"""
PRJ-01 TVC 호퍼 — Stage 1 (자세 안정화) PPO 학습 스크립트

실행: (sim/ 폴더 안에서) python train.py
필요 패키지: gymnasium, stable-baselines3, pyyaml (CartPole/Pendulum 연습 때 이미 설치했으면
             pyyaml만 추가로 설치: pip install pyyaml)

학습 seed(TRAIN_SEED)는 pd_gate.py의 평가 seed(0~199)와 겹치지 않게 둔다. 학습 후 PD와 같은
조건으로 비교하려면: python pd_gate.py --model hopper_attitude_ppo.zip
"""
from hopper_aviary import HopperAttitudeEnv
from stable_baselines3 import PPO

TRAIN_SEED = 10_000

env = HopperAttitudeEnv()
env.reset(seed=TRAIN_SEED)
model = PPO("MlpPolicy", env, verbose=1, seed=TRAIN_SEED)
model.learn(total_timesteps=200_000)
model.save("hopper_attitude_ppo")

# 학습된 정책으로 몇 에피소드 굴려서 보상 확인
obs, _ = env.reset()
total_reward = 0.0
episode = 0
for _ in range(3000):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    total_reward += reward
    if terminated or truncated:
        episode += 1
        print(f"[에피소드 {episode}] 보상: {total_reward:.1f}  ({'추락(각도 초과)' if terminated else '정상 종료'})")
        total_reward = 0.0
        obs, _ = env.reset()

print("학습 완료 — hopper_attitude_ppo.zip 저장됨")
