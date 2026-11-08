"""Train or replay one Stage 2 landing policy from the repository root."""
import argparse
import csv
import json
from pathlib import Path

from .control import LandingPD
from .env import LandingEnv
from .model import euler

COLUMNS = ("t_ms source mode phi theta psi qw qx qy qz wx wy wz "
           "servo1 servo2 servo3 servo4 throttle batt_v rpm reward "
           "px py pz vx vy vz motor vane1_rad vane2_rad vane3_rad vane4_rad").split()


def row(time_s, mode, obs, action=None, reward=None):
    commands = list(action[:4]) if action is not None else [None] * 4
    throttle = (action[4] + 1) / 2 if action is not None else None
    return [round(1000 * time_s), "SIM", mode, *euler(obs[6:10]), *obs[6:13],
            *commands, throttle, None, None, reward, *obs[:6], obs[17], *obs[13:17]]


def episode(env, policy, seed, mode):
    obs, _ = env.reset(seed=seed)
    total = 0.
    rows = []
    while True:
        action = policy(obs)
        time_s = env.data.time
        next_obs, reward, terminated, truncated, info = env.step(action)
        rows.append(row(time_s, mode, obs, action, reward))
        obs = next_obs
        total += reward
        if terminated or truncated:
            break
    rows.append(row(info["time_s"], mode, obs))
    return rows, {**info, "seed": seed, "steps": len(rows) - 1, "return": total}


def positive(value):
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("Expected a positive count.")
    return n


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("train")
    train.add_argument("--steps", type=positive, default=100_000)
    train.add_argument("--model", type=Path, required=True)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--policy", choices=["pd", "ppo"], default="pd")
    evaluate.add_argument("--model", type=Path)
    evaluate.add_argument("--episodes", type=positive, default=1)
    evaluate.add_argument("--out", type=Path, help="Write one web CSV per seed.")
    for command in (train, evaluate):
        command.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if args.command == "evaluate" and args.policy == "ppo" and args.model is None:
        parser.error("--policy ppo requires --model")

    env = LandingEnv()
    try:
        if args.command == "train":
            from stable_baselines3 import PPO
            model = PPO("MlpPolicy", env, n_steps=256, batch_size=64, device="cpu",
                        seed=args.seed, verbose=1)
            model.learn(total_timesteps=args.steps)
            args.model.parent.mkdir(parents=True, exist_ok=True)
            model.save(args.model)
            return

        if args.policy == "pd":
            policy = LandingPD(env.airframe)
            mode = "PID"
        else:
            from stable_baselines3 import PPO
            model = PPO.load(args.model, env=env, device="cpu")
            def policy(obs):
                return model.predict(obs, deterministic=True)[0]
            mode = "RL"
        for seed in range(args.seed, args.seed + args.episodes):
            rows, result = episode(env, policy, seed, mode)
            print(json.dumps(result))
            if args.out:
                args.out.mkdir(parents=True, exist_ok=True)
                path = args.out / f"stage2-{args.policy}-s{seed}.csv"
                with path.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(COLUMNS)
                    writer.writerows(rows)
    finally:
        env.close()


if __name__ == "__main__":
    main()
