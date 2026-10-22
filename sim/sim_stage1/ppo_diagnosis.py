"""Diagnose whether PPO's vane or throttle outputs cause issue #90."""
import argparse

import gymnasium as gym
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor

from hopper_aviary import HopperAttitudeEnv
from pd_gate import EVAL_SEEDS, evaluate, pd, row

TRAIN_SEED = 10_000


class FixedThrottleEnv(gym.ActionWrapper):
    """Train four vane actions while the environment receives full throttle."""

    def __init__(self):
        super().__init__(HopperAttitudeEnv())
        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(4,), dtype=np.float32)

    def action(self, action):
        return np.append(np.asarray(action, dtype=np.float32), np.float32(1.0))


def model_action(model, obs, deterministic=True):
    return np.asarray(model.predict(obs, deterministic=deterministic)[0], dtype=np.float32)


def ppo_policy(model, deterministic=True):
    return lambda obs: model_action(model, obs, deterministic)


def ppo_vanes_fixed_throttle(model, throttle_norm=1.0):
    def policy(obs):
        action = model_action(model, obs)
        action[4] = throttle_norm
        return action
    return policy


def pd_vanes_ppo_throttle(model):
    def policy(obs):
        action = pd(obs)
        action[4] = model_action(model, obs)[4]
        return action
    return policy


def fixed_throttle_model_policy(model):
    def policy(obs):
        vanes = model_action(model, obs)
        return np.append(vanes, np.float32(1.0))
    return policy


def throttle_stats(policy, seeds=EVAL_SEEDS):
    env = HopperAttitudeEnv()
    values = []
    for seed in seeds:
        obs, _ = env.reset(seed=seed)
        done = False
        while not done:
            obs, _, terminated, truncated, info = env.step(policy(obs))
            values.append(info["throttle"])
            done = terminated or truncated
    values = np.asarray(values)
    return {
        "mean": float(values.mean()),
        "max": float(values.max()),
        "zero_fraction": float(np.mean(values == 0.0)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="hopper_attitude_ppo.zip")
    parser.add_argument("--train-fixed-throttle", metavar="MODEL")
    parser.add_argument("--timesteps", type=int, default=200_000)
    parser.add_argument("--eval-seeds", type=int, default=len(EVAL_SEEDS))
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    seeds = range(args.eval_seeds)

    model = PPO.load(args.model, device="cpu")
    policies = {
        "PD": pd,
        "PPO": ppo_policy(model),
        "PPO stochastic": ppo_policy(model, deterministic=False),
        "PPO vanes + throttle 1": ppo_vanes_fixed_throttle(model),
        "PD vanes + PPO throttle": pd_vanes_ppo_throttle(model),
    }

    if not args.skip_existing:
        print(f"evaluation seeds 0-{args.eval_seeds - 1}")
        print("| policy | mean return | mean length | crash | median final tilt |")
        print("|---|---|---|---|---|")
        for name, policy in policies.items():
            print(row(name, evaluate(policy, seeds=seeds)))

        print("\n| policy | mean throttle | max throttle | zero steps |")
        print("|---|---|---|---|")
        for name in ("PPO", "PD vanes + PPO throttle"):
            stats = throttle_stats(policies[name], seeds=seeds)
            print(f"| {name} | {stats['mean']:.4f} | {stats['max']:.4f} | "
                  f"{stats['zero_fraction'] * 100:.1f} % |")

        expected_attitude_cost = 2 * (0.3 ** 2 / 3) + 0.1 * (0.3 ** 2 / 3)
        expected_shutdown_return = -500 * (expected_attitude_cost + 0.001)
        print(f"\nexpected frozen-state return: {expected_shutdown_return:.2f}")

    if args.train_fixed_throttle:
        env = Monitor(FixedThrottleEnv())
        fixed_model = PPO("MlpPolicy", env, verbose=0, seed=TRAIN_SEED)
        fixed_model.learn(total_timesteps=args.timesteps)
        fixed_model.save(args.train_fixed_throttle)
        rewards = np.asarray(env.get_episode_rewards())
        window = min(20, len(rewards))
        print(f"fixed-throttle episodes: {len(rewards)}")
        print(f"fixed-throttle first {window} mean return: {rewards[:window].mean():.2f}")
        print(f"fixed-throttle last {window} mean return: {rewards[-window:].mean():.2f}")
        print(row("PPO fixed-throttle train",
                  evaluate(fixed_throttle_model_policy(fixed_model), seeds=seeds)))


if __name__ == "__main__":
    main()
