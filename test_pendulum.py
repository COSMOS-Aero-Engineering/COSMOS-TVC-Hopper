import gymnasium as gym
from stable_baselines3 import PPO

env = gym.make("Pendulum-v1")
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=50000)

obs, _ = env.reset()
total_reward = 0
for _ in range(300):
    action, _ = model.predict(obs)
    obs, reward, terminated, truncated, info = env.step(action)
    total_reward += reward
    if terminated or truncated:
        print(f"에피소드 보상: {total_reward:.1f}")
        total_reward = 0
        obs, _ = env.reset()

print("학습 완료!")