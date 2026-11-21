"""Stage 2 PPO landing rate by training budget, on evaluation seeds kept apart from training (#296).

train     PPO on LandingEnv with N parallel envs; saves checkpoints at the given budgets.
evaluate  Counts episode outcomes for PD and for each checkpoint on the same evaluation seeds.

Training seeds: make_vec_env(seed=S) seeds env i with S+i on the first reset; later resets
continue those generators. Evaluation uses reset(seed=s) for s in EVAL_SEEDS. train refuses
any S..S+N-1 that overlaps EVAL_SEEDS.

Each checkpoint <stem>.zip has <stem>.json (condition, reward, methods, vecnormalize, timesteps)
and, for vecnorm, <stem>.vecnormalize.pkl. A checkpoint is saved at the first callback step at or
past each budget, so its weights come from the last PPO update before that step.

--method (#413) adds learning aids on top of LandingEnv, which stays unchanged. shaped, curriculum
and timeterm only change the training signal, so evaluation runs on the plain LandingEnv.
residual (PD output plus a learned correction) and timeobs (elapsed fraction in the observation)
change what the policy sees or outputs, so evaluate wraps the evaluation env the same way.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np

from .control import LandingPD
from .env import LandingEnv

EVAL_SEEDS = range(1000, 1100)
OUTCOMES = ("landed", "hard_contact", "body_contact", "tipped", "out_of_bounds", "time_limit")
CONDITIONS = ("raw", "vecnorm")
# Training-only reward variants. LandingEnv itself is unchanged; evaluation counts outcomes only.
REWARDS = ("env", "timeout10")
# Learning aids (#413). The first three need the policy interface at evaluation too.
METHODS = ("shaped", "curriculum", "residual", "timeobs", "timeterm")
INTERFACE_METHODS = ("residual", "timeobs")
GAMMA = 0.99
# shaped: potential = -SHAPE_SCALE * distance to the landed state in (height, offset, speed) space.
SHAPE_SCALE = 5.
SHAPE_LENGTHS = (0.5, 0.5, 0.3)  # m, m, m/s: one unit of distance
# curriculum: start-height range (above rest height) at the first step and when the ramp ends.
CURRICULUM_START = (0.03, 0.10)
CURRICULUM_END = (0.45, 0.65)
RESIDUAL_SCALE = 0.3


class TimeoutAsFailure(gym.Wrapper):
    """timeout10: the time-limit penalty is -10, the same number as a failure, instead of -5.

    It is not the same signal for PPO. SB3 treats truncation as non-terminal and bootstraps
    gamma * V(terminal_obs) (TimeLimit.truncated), while a failure is terminal. The observation
    has no elapsed time, so the value function cannot see the step-400 penalty coming.
    """

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        if truncated and info.get("outcome") == "time_limit":
            reward -= 5.
        return obs, reward, terminated, truncated, info


class PotentialShaping(gym.Wrapper):
    """shaped: adds F = gamma * phi(s') - phi(s) with phi = -K * distance to the landed state.

    The distance combines height above rest, horizontal offset and speed, so a faster descent is
    not rewarded without a matching drop in speed. phi is zero in a terminal state (Ng et al.
    1999), so the shaping adds the same total to any path that ends and leaves the optimal policy
    unchanged. It makes the approach visible step by step. A truncated step keeps phi(s'), since
    SB3 bootstraps V(s') there.
    """

    def potential(self, obs):
        height = obs[2] - self.env.unwrapped.airframe.rest_height
        parts = np.array([max(0., height), np.linalg.norm(obs[:2]), np.linalg.norm(obs[3:6])])
        return -SHAPE_SCALE * float(np.linalg.norm(parts / SHAPE_LENGTHS))

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self.phi = self.potential(obs)
        return obs, info

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        phi = 0. if terminated else self.potential(obs)
        reward += GAMMA * phi - self.phi
        self.phi = phi
        return obs, reward, terminated, truncated, info


class HeightCurriculum(gym.Wrapper):
    """curriculum: the first resets start low above the pad, the range grows to the real one.

    Each env counts its own steps and assumes n_envs equal workers, so progress is the share of
    the ramp (in total env steps) used so far. The last range is LandingEnv's own (0.45-0.65 m).
    Only the start height changes. Hover thrust and zero velocity stay as in LandingEnv.reset.
    """

    def __init__(self, env, n_envs=1, ramp_steps=400_000):
        super().__init__(env)
        self.n_envs, self.ramp_steps, self.seen = n_envs, ramp_steps, 0

    def reset(self, **kwargs):
        env = self.env.unwrapped
        _, info = self.env.reset(**kwargs)
        progress = min(1., self.seen * self.n_envs / self.ramp_steps)
        low = CURRICULUM_START[0] + progress * (CURRICULUM_END[0] - CURRICULUM_START[0])
        high = CURRICULUM_START[1] + progress * (CURRICULUM_END[1] - CURRICULUM_START[1])
        env.data.qpos[2] = env.airframe.rest_height + env.np_random.uniform(low, high)
        mujoco.mj_forward(env.model, env.data)
        return env.observation(), info

    def step(self, action):
        self.seen += 1
        return self.env.step(action)


class PdResidual(gym.Wrapper):
    """residual: the executed action is LandingPD(obs) + RESIDUAL_SCALE * policy action.

    PD's touchdown throttle cut (exactly -1 below 3 mm) passes through unchanged, because the
    landing test needs the EDF speed ratio at or below 0.10 and a positive residual would hold it
    above that.
    """

    def __init__(self, env):
        super().__init__(env)
        self.pd = LandingPD(env.unwrapped.airframe)

    def reset(self, **kwargs):
        self.last, info = self.env.reset(**kwargs)
        return self.last, info

    def step(self, action):
        base = self.pd(self.last)
        if base[4] > -1.:
            base = np.clip(base + RESIDUAL_SCALE * np.clip(action, -1., 1.), -1., 1.)
        self.last, reward, terminated, truncated, info = self.env.step(base)
        return self.last, reward, terminated, truncated, info


class TimeoutTerminates(gym.Wrapper):
    """timeterm: a time-limit stop is reported as terminated, so SB3 does not bootstrap V(s')."""

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        if truncated:
            terminated, truncated = True, False
        return obs, reward, terminated, truncated, info


class ElapsedTime(gym.Wrapper):
    """timeobs: appends steps / max_steps to the observation (19 values)."""

    def __init__(self, env):
        super().__init__(env)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(19,), dtype=np.float32)

    def stamp(self, obs):
        return np.append(obs, self.env.unwrapped.steps / self.env.unwrapped.max_steps).astype(np.float32)

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        return self.stamp(obs), info

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        return self.stamp(obs), reward, terminated, truncated, info


def make_env(reward="env", methods=(), n_envs=1, ramp_steps=400_000):
    """Training env. Wrapper order, inner to outer: curriculum, timeout10, residual, shaped,
    timeterm, timeobs. timeout10 sits inside timeterm so it still sees the truncation."""
    env = LandingEnv()
    if "curriculum" in methods:
        env = HeightCurriculum(env, n_envs, ramp_steps)
    if reward == "timeout10":
        env = TimeoutAsFailure(env)
    if "residual" in methods:
        env = PdResidual(env)
    if "shaped" in methods:
        env = PotentialShaping(env)
    if "timeterm" in methods:
        env = TimeoutTerminates(env)
    if "timeobs" in methods:
        env = ElapsedTime(env)
    return env


def make_eval_env(methods=()):
    """Evaluation env: the plain LandingEnv plus only the wrappers that change the policy interface."""
    env = LandingEnv()
    if "residual" in methods:
        env = PdResidual(env)
    if "timeobs" in methods:
        env = ElapsedTime(env)
    return env


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
    methods = tuple(args.method)
    venv = make_vec_env(make_env, n_envs=args.envs, seed=args.seed, vec_env_cls=SubprocVecEnv,
                        env_kwargs={"reward": args.reward, "methods": methods, "n_envs": args.envs,
                                    "ramp_steps": args.ramp_steps})
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
                tag = "-".join([args.condition, *([] if args.reward == "env" else [args.reward]), *methods])
                stem = args.out / f"ppo-{tag}-s{args.seed}-{budget}"
                self.model.save(stem.with_suffix(".zip"))
                if args.condition == "vecnorm":
                    self.model.get_env().save(str(stem) + ".vecnormalize.pkl")
                Path(str(stem) + ".json").write_text(json.dumps({
                    "condition": args.condition, "reward": args.reward, "methods": list(methods),
                    "seed": args.seed,
                    "envs": args.envs, "vecnormalize": args.condition == "vecnorm",
                    "budget": budget, "timesteps": self.num_timesteps}), encoding="utf-8")
                print(json.dumps({"saved": str(stem) + ".zip", "timesteps": self.num_timesteps}), flush=True)
            return True

    model.learn(total_timesteps=budgets[-1], callback=Checkpoints())
    venv.close()


def load_ppo(path):
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

    path = Path(path)
    stem = path.with_suffix("") if path.suffix == ".zip" else path
    model = PPO.load(stem.with_suffix(".zip"), device="cpu")
    stats = Path(str(stem) + ".vecnormalize.pkl")
    meta_path = Path(str(stem) + ".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    declared = meta.get("vecnormalize")
    methods = tuple(m for m in meta.get("methods", ()) if m in INTERFACE_METHODS)
    if declared and not stats.exists():
        raise FileNotFoundError(f"{meta_path.name} says VecNormalize but {stats.name} is missing")
    if declared is False and stats.exists():
        raise ValueError(f"{meta_path.name} says raw observations but {stats.name} exists")
    normalize = None
    if stats.exists():
        vn = VecNormalize.load(str(stats), DummyVecEnv([lambda: make_eval_env(methods)]))
        vn.training = False
        vn.norm_reward = False
        normalize = vn.normalize_obs

    def policy(obs):
        o = obs if normalize is None else normalize(obs[None])[0]
        return model.predict(o, deterministic=True)[0]
    policy.methods = methods
    return policy


def evaluate_policy(policy, seeds):
    env = make_eval_env(getattr(policy, "methods", ()))
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
        policy = load_ppo(path)
        rows.append({"policy": str(path), "methods": list(policy.methods), **evaluate_policy(policy, seeds)})
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
    t.add_argument("--method", choices=METHODS, nargs="*", default=[])
    t.add_argument("--ramp-steps", type=int, default=400_000)
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
