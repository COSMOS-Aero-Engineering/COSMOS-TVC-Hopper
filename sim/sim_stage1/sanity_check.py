"""
학습 돌리기 전에 먼저 실행해서 환경 자체가 안 깨졌는지 빠르게 확인하는 스크립트.
(무작위 액션으로 20스텝만 돌려봄 — 몇 초면 끝남)

실행: python sanity_check.py
"""
from hopper_aviary import HopperAttitudeEnv

env = HopperAttitudeEnv()
obs, info = env.reset()
print("초기 상태 (phi, theta, psi, wx, wy, wz):", obs)

for i in range(20):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    print(f"step {i}: reward={reward:.4f} terminated={terminated} truncated={truncated}")
    if terminated or truncated:
        obs, info = env.reset()
        print("  -> reset")

print("환경 정상 동작 확인 완료.")
