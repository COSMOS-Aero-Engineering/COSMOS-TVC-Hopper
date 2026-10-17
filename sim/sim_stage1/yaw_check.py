"""
요 축 검사(#65). pd_gate.py는 롤·피치만 본다. 그 PD는 a1=a3, a2=a4라 요 토크가 늘 0이다.
그래서 vane_arm_r이나 요 토크 식이 틀려도 pd_gate.py는 통과한다. 이 파일이 요 경로를 따로 본다.

실행: python yaw_check.py      둘 중 하나라도 실패하면 exit 1

1. 토크 손계산 (도메인 랜덤화 끔, 명목값)
   ω = 0에서 베인 명령을 한 스텝 주고 환경이 만든 각속도 변화 Δω를 손계산과 비교한다.
   손계산은 hopper_aviary.py의 토크 식을 쓰지 않는다. 베인 위치와 힘 방향에서 τ = Σ pᵢ × Fᵢ로 구한다.
   상수는 전부 params.yaml에서 읽는다. 그래서 params.yaml 값이 바뀌어도(PR #63의 vane_arm_r 등) 그대로 맞는다.
   - 부호: 요 명령 [1,-1,-1,1]이 +ωz를 만든다.
   - 크기: Δωz가 손계산과 상대오차 1e-4 안에서 같다.
   - 누설: 요 명령의 Δωx, Δωy가 0이다. 롤·피치 명령의 Δωz도 0이다.
2. 요 PD (도메인 랜덤화 켬, 평가 seed 0-199)
   pd_gate.py의 롤·피치 PD에 요 PD(같은 게인 kp=8, kd=2)를 섞는다.
   - 합격: 모든 seed에서 마지막 |ψ| ≤ 1°. 초기 |ψ|는 최대 0.3 rad(17.2°)다.
   - 롤·피치 판정(pd_gate.py와 같은 기준)이 요를 섞은 뒤에도 합격이다.

회전자 반작용 토크와 회전자 자이로 항은 환경에 없고 이 검사도 넣지 않는다(#65 제외 범위).
"""
import os
import sys

import numpy as np
import yaml

from hopper_aviary import HopperAttitudeEnv
from pd_gate import EVAL_SEEDS, MAX_CRASH, MAX_MEDIAN_TILT_DEG, gate_passes, pd

PARAMS = os.path.join(os.path.dirname(__file__), "params.yaml")

REL_TOL = 1e-4      # 상태가 float32라 1e-7 근처까지 맞는다. 여유를 둔다
LEAK_TOL = 1e-6     # rad/s, 한 스텝 각속도 누설 허용치
MAX_FINAL_YAW_DEG = 1.0

# 베인 명령 [a1, a2, a3, a4, throttle(-1~1)]
COMMANDS = {
    "롤 [1,0,1,0]": [1, 0, 1, 0, 1],
    "피치 [0,1,0,1]": [0, 1, 0, 1, 1],
    "요 [1,-1,-1,1]": [1, -1, -1, 1, 1],
    "섞음": [0.3, -0.7, 0.5, 0.2, 0.2],
}


def hand_torque(p, action):
    """베인 4장의 힘으로 몸체 토크 τ(N·m, 3벡터)를 손계산한다.

    위치 pᵢ: 좌표계(AGENTS.md §프로젝트 한눈에)대로 베인 1-4는 +X, +Y, −X, −Y에 있다.
      z축에서 반경 r, 무게중심에서 아래로 l → pᵢ = (r cos θᵢ, r sin θᵢ, −l), θᵢ = 0°, 90°, 180°, 270°.
    힘 Fᵢ = CL · Ft · αᵢ (논문 식 3.16). 방향은 논문 식 3.19의 롤·피치 행에서 정해진다:
      τx = (F1+F3)·l이면 베인 1·3의 힘은 +Y, τy = −(F2+F4)·l이면 베인 2·4의 힘은 +X다.
    요 행 τz = (F1−F2−F3+F4)·r은 쓰지 않는다. 위 위치와 방향의 외적에서 따로 나와야 한다.
    """
    CL = p["CLalpha"] * p["A_fin"] / (2.0 * p["A_duct"])
    alpha = np.asarray(action[:4], dtype=float) * np.deg2rad(p["alpha_max_deg"])
    throttle = (action[4] + 1.0) / 2.0
    Ft = p["Kf"] * (throttle * p["omega_t_per_throttle"]) ** 2
    l, r = p["vane_arm_l"], p["vane_arm_r"]
    tau = np.zeros(3)
    for i, theta in enumerate(np.deg2rad([0, 90, 180, 270])):
        pos = np.array([r * np.cos(theta), r * np.sin(theta), -l])
        direction = np.array([0.0, 1.0, 0.0]) if i in (0, 2) else np.array([1.0, 0.0, 0.0])
        tau += np.cross(pos, CL * Ft * alpha[i] * direction)
    return tau


def env_delta_omega(env, action):
    """ω = 0, 자세 0에서 한 스텝 뒤 각속도 변화(rad/s, 3벡터)."""
    env.reset(seed=0)
    env.state = np.zeros(6, dtype=np.float32)
    obs, *_ = env.step(np.asarray(action, dtype=np.float32))
    return obs[3:6].astype(float)


def check_torque(p):
    print("1. 토크 손계산 (랜덤화 끔, 명목값)")
    print(f"   vane_arm_l = {p['vane_arm_l']} m, vane_arm_r = {p['vane_arm_r']} m\n")
    failures = []
    for name in ("vane_arm_l", "vane_arm_r"):
        if not p[name] > 0:
            failures.append(f"{name} = {p[name]}: 거리라서 0보다 커야 한다")

    env = HopperAttitudeEnv()
    env.dr = {"enabled": False}   # 명목값 한 점. 무게중심 오프셋도 0이다
    J = np.array([p["Jxx"], p["Jyy"], p["Jzz"]])
    print("   | 명령 | 환경 Δω (rad/s) | 손계산 Δω (rad/s) |")
    print("   |---|---|---|")
    for name, action in COMMANDS.items():
        got = env_delta_omega(env, action)
        want = hand_torque(p, action) / J * env.dt
        print(f"   | {name} | {np.array2string(got, precision=5)} | {np.array2string(want, precision=5)} |")
        for axis, g, w in zip("xyz", got, want):
            if not np.isfinite(g):
                failures.append(f"{name}: Δω{axis} = {g} (유한한 값이 아니다)")
            elif abs(w) < LEAK_TOL:
                if abs(g) > LEAK_TOL:
                    failures.append(f"{name}: Δω{axis} = {g:.3g}, 손계산은 0 (누설)")
            elif np.sign(g) != np.sign(w):
                failures.append(f"{name}: Δω{axis} = {g:.5g}, 손계산 {w:.5g} (부호가 다름)")
            elif abs(g - w) > REL_TOL * abs(w):
                failures.append(f"{name}: Δω{axis} = {g:.5g}, 손계산 {w:.5g} (크기가 다름)")

    yaw = env_delta_omega(env, COMMANDS["요 [1,-1,-1,1]"])
    if not yaw[2] > 0:
        failures.append(f"요 명령 [1,-1,-1,1]의 Δωz = {yaw[2]:.5g}. +ωz여야 한다")
    return failures


def pd_with_yaw(obs, kp=8.0, kd=2.0):
    """pd_gate.pd()에 요 PD를 섞는다. 요 명령 [1,-1,-1,1] 방향이 +τz다."""
    a = pd(obs)
    uz = np.clip(-kp * obs[2] - kd * obs[5], -1, 1)
    a[:4] = np.clip(a[:4] + uz * np.array([1, -1, -1, 1]), -1, 1)
    return a


def run_yaw_pd():
    env = HopperAttitudeEnv()
    if not env.dr.get("enabled", False):
        raise ValueError("params.yaml의 domain_rand.enabled가 false다. 요 PD 기준은 랜덤화를 켠 상태에서만 잰다.")
    initial, final, crashes, tilts = [], [], [], []
    for s in EVAL_SEEDS:
        obs, _ = env.reset(seed=s)
        initial.append(abs(obs[2]))
        done = False
        while not done:
            obs, _, term, trunc, _ = env.step(pd_with_yaw(obs))
            done = term or trunc
        final.append(abs(obs[2]))
        crashes.append(term)
        tilts.append(np.degrees(np.hypot(obs[0], obs[1])))
    return {
        "initial_max_deg": float(np.degrees(np.max(initial))),
        "final_max_deg": float(np.degrees(np.max(final))),
        "final_median_deg": float(np.degrees(np.median(final))),
        "crash": float(np.mean(crashes)),
        "median_tilt_deg": float(np.median(tilts)),
    }


def check_yaw_pd():
    print(f"\n2. 요 PD (랜덤화 켬, 평가 seed {EVAL_SEEDS.start}-{EVAL_SEEDS.stop - 1}, kp=8, kd=2)\n")
    m = run_yaw_pd()
    print(f"   초기 |ψ| 최댓값 {m['initial_max_deg']:.2f}°, 마지막 |ψ| 최댓값 {m['final_max_deg']:.2g}°, "
          f"중앙값 {m['final_median_deg']:.2g}°")
    print(f"   롤·피치: 넘어짐 {m['crash'] * 100:.1f} %, 최종 기울기 중앙값 {m['median_tilt_deg']:.1f}°")
    failures = []
    if not m["final_max_deg"] <= MAX_FINAL_YAW_DEG:
        failures.append(f"마지막 |ψ| 최댓값 {m['final_max_deg']:.3f}° > {MAX_FINAL_YAW_DEG}°: 요 PD가 요 오차를 못 줄였다")
    if not gate_passes(m):
        failures.append(f"요를 섞은 뒤 롤·피치 판정 불합격 (기준: 넘어짐 ≤ {MAX_CRASH * 100:.0f} %, "
                        f"중앙값 ≤ {MAX_MEDIAN_TILT_DEG:.0f}°)")
    return failures


def main():
    with open(PARAMS, "r", encoding="utf-8") as f:
        p = yaml.safe_load(f)
    failures = check_torque(p) + check_yaw_pd()
    if failures:
        print("\n요 축 판정: 불합격")
        for msg in failures:
            print(f"   - {msg}")
        return 1
    print(f"\n요 축 판정: 합격 (토크 손계산 상대오차 ≤ {REL_TOL:g}, 누설 ≤ {LEAK_TOL:g} rad/s, "
          f"마지막 |ψ| ≤ {MAX_FINAL_YAW_DEG}°)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
