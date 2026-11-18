"""Stage 2 PPO landing rate by training budget, on evaluation seeds kept apart from training (#296).

train     PPO on LandingEnv with N parallel envs; saves checkpoints at the given budgets.
evaluate  Counts episode outcomes for PD and for each checkpoint on the same evaluation seeds.

Training seeds: make_vec_env(seed=S) seeds env i with S+i on the first reset; later resets
continue those generators. Evaluation uses reset(seed=s) for s in EVAL_SEEDS, which never
appears as a training seed for the default S=41 and N<=16.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import gymnasium as gym
import numpy as np

from .control import LandingPD
from .env import LandingEnv

EVAL_SEEDS = range(1000, 1100)
OUTCOMES = ("landed", "hard_contact", "body_contact", "tipped", "out_of_bounds", "time_limit")
CONDITIONS = ("raw", "vecnorm")
# Training-only reward variants. LandingEnv itself is unchanged; evaluation counts outcomes only.
REWARDS = ("env", "timeout10")


class TimeoutAsFailure(gym.Wrapper):
    """timeout10: the time limit costs -10 like a failure instead of -5 (LandingEnv.step)."""

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        if truncated and info.get("outcome") == "time_limit":
            reward -= 5.
        return obs, reward, terminated, truncated, info


def make_env(reward):
    return TimeoutAsFailure(LandingEnv()) if reward == "timeout10" else LandingEnv()


def train(args):
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize

    torch.set_num_threads(args.threads)
    if args.seed <= max(EVAL_SEEDS) and args.seed + args.envs - 1 >= min(EVAL_SEEDS):
        raise SystemExit("Training seeds overlap the evaluation seeds.")
    budgets = sorted(set(args.budgets))
    venv = make_vec_env(make_env, n_envs=args.envs, seed=args.seed, vec_env_cls=SubprocVecEnv,
                        env_kwargs={"reward": args.reward})
    if args.condition == "vecnorm":
        venv = VecNormalize(venv, norm_obs=True, norm_reward=True, gamma=0.99)
    args.out.mkdir(parents=True, exist_ok=True)
    model = PPO("MlpPolicy", venv, n_steps=args.n_steps, batch_size=args.batch, device="cpu",
                seed=args.seed, verbose=0)

    class Checkpoints(BaseCallback):
        def __init__(self):
            super().__init__()
            self.pending = list(budgets)

        def _on_step(self):
            while self.pending and self.num_timesteps >= self.pending[0]:
                budget = self.pending.pop(0)
                tag = args.condition if args.reward == "env" else f"{args.condition}-{args.reward}"
                stem = args.out / f"ppo-{tag}-s{args.seed}-{budget}"
                self.model.save(stem.with_suffix(".zip"))
                if args.condition == "vecnorm":
                    self.model.get_env().save(str(stem) + ".vecnormalize.pkl")
                print(json.dumps({"saved": str(stem) + ".zip", "timesteps": self.num_timesteps}), flush=True)
            return True

    model.learn(total_timesteps=budgets[-1], callback=Checkpoints())
    venv.close()


def load_ppo(path):
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

    model = PPO.load(path, device="cpu")
    stats = Path(str(path)[:-len(".zip")] + ".vecnormalize.pkl")
    normalize = None
    if stats.exists():
        vn = VecNormalize.load(str(stats), DummyVecEnv([LandingEnv]))
        vn.training = False
        vn.norm_reward = False
        normalize = vn.normalize_obs

    def policy(obs):
        o = obs if normalize is None else normalize(obs[None])[0]
        return model.predict(o, deterministic=True)[0]
    return policy


def evaluate_policy(policy, seeds):
    env = LandingEnv()
    counts, impacts, times = Counter(), [], []
    try:
        for seed in seeds:
            obs, _ = env.reset(seed=seed)
            while True:
                obs, _, terminated, truncated, info = env.step(policy(obs))
                if terminated or truncated:
                    break
            counts[info["outcome"]] += 1
            if info["outcome"] == "landed":
                impacts.append(info["impact_m_s"])
                times.append(info["time_s"])
    finally:
        env.close()
    row = {name: counts.get(name, 0) for name in OUTCOMES}
    row["episodes"] = len(seeds)
    row["landed_impact_max_m_s"] = float(max(impacts)) if impacts else None
    row["landed_time_mean_s"] = float(np.mean(times)) if times else None
    return row


def evaluate(args):
    seeds = list(EVAL_SEEDS)[:args.episodes]
    rows = []
    if not args.skip_pd:
        env = LandingEnv()
        rows.append({"policy": "pd", **evaluate_policy(LandingPD(env.airframe), seeds)})
        env.close()
    for path in args.models:
        rows.append({"policy": str(path), **evaluate_policy(load_ppo(path), seeds)})
    for row in rows:
        print(json.dumps(row), flush=True)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"eval_seeds": [seeds[0], seeds[-1]], "rows": rows}, indent=1),
                             encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    t = commands.add_parser("train")
    t.add_argument("--condition", choices=CONDITIONS, default="raw")
    t.add_argument("--reward", choices=REWARDS, default="env")
    t.add_argument("--seed", type=int, default=41)
    t.add_argument("--envs", type=int, default=8)
    t.add_argument("--threads", type=int, default=2)
    t.add_argument("--n-steps", type=int, default=512)
    t.add_argument("--batch", type=int, default=256)
    t.add_argument("--budgets", type=int, nargs="+", default=[250_000, 500_000, 1_000_000])
    t.add_argument("--out", type=Path, required=True)
    e = commands.add_parser("evaluate")
    e.add_argument("models", type=Path, nargs="*")
    e.add_argument("--episodes", type=int, default=len(EVAL_SEEDS))
    e.add_argument("--skip-pd", action="store_true")
    e.add_argument("--json", type=Path)
    args = parser.parse_args()
    if args.command == "train":
        train(args)
    else:
        if not 1 <= args.episodes <= len(EVAL_SEEDS):
            parser.error(f"--episodes must be in [1,{len(EVAL_SEEDS)}]")
        evaluate(args)


if __name__ == "__main__":
    main()
