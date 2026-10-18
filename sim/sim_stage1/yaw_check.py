"""
요 축 검사(#65). pd_gate.py는 롤·피치만 본다. 그 PD는 a1=a3, a2=a4라 요 토크가 늘 0이다.
그래서 요 팔 r(vane_geometry)이나 요 토크 식이 틀려도 pd_gate.py는 통과한다. 이 파일이 요 경로를 따로 본다.

실행: python yaw_check.py      하나라도 실패하면 exit 1

1. 토크 손계산 (도메인 랜덤화 끔, 명목값)
   ω = 0에서 베인 명령을 한 스텝 주고 환경이 만든 각속도 변화 Δω를 손계산과 비교한다.
   손계산은 hopper_aviary.py의 토크 식을 쓰지 않는다. 베인 위치와 힘 방향에서 τ = Σ pᵢ × Fᵢ로 구한다.
   상수는 전부 params.yaml에서 읽는다. 그래서 params.yaml 값이 바뀌어도(#98의 vane_geometry 등) 그대로 맞는다.
   요 팔 r, A_fin, A_duct도 vane_geometry에서 따로 손계산한다(hand_geometry).
   - 부호: 요 명령 [1,-1,-1,1]이 +ωz를 만든다.
   - 크기: Δωz가 손계산과 상대오차 1e-4 안에서 같다.
   - 누설: 요 명령의 Δωx, Δωy가 0이다. 롤·피치 명령의 Δωz도 0이다.
   회전자 항(#86)을 켠 표도 함께 비교한다. 첫 스텝의 회전자는 이미 명령 회전수로 돈다(반작용 0).
   ω = 0이라 자이로 토크도 0에서 시작하지만, 환경은 자이로 항을 사다리꼴 규칙으로 적분하므로 Δω에 축 사이
   결합이 생긴다. 손계산은 (J − dt/2·[h]×)·Δω = dt·τ를 3×3 행렬로 따로 푼다. [h]×는 h × (·)의 행렬이다.
   이때 누설은 손계산이 0인 축만 본다. 롤 명령의 Δωy 같은 자이로 결합은 손계산에 들어 있다.
2. 회전자 항·스로틀 변화율 손계산 (#86, #120, 도메인 랜덤화 끔)
   가-다는 회전자 항을 켜고 spin_dir +1과 -1을 각각 본다. 가-다는 회전자 식만 보려고 스로틀 변화율 제한을 끈다.
   가. 반작용: 베인 0, 스로틀 1.0 → 0.75 계단. 베인 토크가 없으면 z축 각운동량 Jzz·ωz + s·I_r·Ω가
       매 스텝 그대로다. 회전수가 다 따라간 뒤 Δωz = −s·I_r·omega_max·(0.75 − 1.0)/Jzz다.
       이 값은 1차 지연 모델과 상관없다. Δωx·Δωy는 0이다.
   나. 자이로: 베인 0, 스로틀 1.0, ω0 = (0.5, 0, 0) rad/s, Jyy = Jxx로 둔 대칭 기체.
       해석해에서 (ωx, ωy)는 크기를 지키며 각속도 s·I_r·omega_max/Jxx로 +Z축 둘레를 돈다.
       |ω|는 상대오차 1e-4 안에서 그대로여야 한다. 0.3초 뒤 (ωx, ωy)는 해석해와
       사다리꼴 규칙의 위상 오차 한도(스텝당 (rate·dt)³/12 rad) 안에서 같아야 한다. ωz는 0이다.
   다. 추력 지연(#122): 회전자 항을 켜면 추력도 지연된 회전수에서 나온다. 스로틀 1.0 → 0.75 계단 뒤
       THRUST_PROBE_STEPS번째 스텝에 롤 명령을 주고 그 스텝의 Δω를 손계산과 상대오차 1e-4 안에서 비교한다.
       손계산은 1차 지연의 해석해 u_k = 0.75 + 0.25·e^(−k·dt/tau)(u = Ω/omega_max)로 추력 Kf·(u_k·omega_t_per_throttle)²를 쓴다.
       추력이 지연 없이 스로틀을 따르면(#122 전 모델) Δω가 (0.75/u_k)²배라서 이 검사가 실패한다.
   라. 스로틀 변화율 제한(#120): 명령 1.0 → 0.75 → 1.0 계단에서 환경이 실제로 쓴 스로틀(info["throttle"])이
       첫 스텝은 그대로, 그 뒤는 스텝마다 throttle_slew_rate·dt씩 바뀌는지 본다(허용 오차 SLEW_TOL).
   마. 베인 서보 동특성(#161): 서보 모델을 켜고(params.yaml servo 상수) 베인 1에 계단 명령을 준다.
       (1) 1차 지연: 0 → +alpha_max 계단 뒤 k 스텝째 베인각이 해석해 alpha_max·(1 − e^(−k·dt/tau))와 같다.
           그 스텝의 Δωx도 그 베인각으로 손계산한 토크와 같다(힘이 스텝 끝 베인각을 따른다).
       (2) 데드밴드: 베인이 멈추면 명령보다 데드밴드 미만만큼 모자란다. 멈춘 베인각에서 데드밴드의 절반만큼 떨어진 명령에는
           베인각이 그대로다. 데드밴드의 2배만큼 떨어진 명령에는 움직인다.
       (3) 속도 제한: tau를 0으로 두고 −alpha_max → +alpha_max 계단을 주면 스텝마다 rate_max·dt씩 움직인다.
   1번과 2번 가-라는 서보 모델을 끈다(명령각이 바로 베인각). 3번 요 PD는 params.yaml servo.enabled를 따른다.
   1·2번은 랜덤화를 끄므로 회전자 상수도 params.yaml rotor의 명목값이다(#121).
3. 요 PD (도메인 랜덤화 켬, 평가 seed 0-199)
   pd_gate.py의 롤·피치 PD에 요 PD(같은 게인 kp=8, kd=2)를 섞는다. 같은 seed로 두 스로틀 시나리오를 잰다.
   회전자 상수(inertia·omega_max·tau)도 seed마다 domain_rand.rotor_*_range에서 뽑은 값이다(#121).
     A: 스로틀 1.0 고정(#65와 같다). 반작용 토크는 0이고 자이로 항만 작용한다.
     B: t = 1 s에 스로틀 명령 1.0 → 0.75 계단. 0.75는 호버 스로틀 추정값이다.
        01 문서 §8.1의 AUW 735 g, 정적 추력 1300 gf에서 √(735/1300) = 0.75(추력 ∝ 스로틀²).
        환경이 params.yaml의 throttle_slew_rate로 명령을 자르므로 실제 스로틀은 경사로 바뀐다(#120).
   각 시나리오를 회전자 항 끔, 켬(spin_dir +1), 켬(spin_dir -1)으로 돌린다.
   - 합격: 모든 seed에서 마지막 |ψ| ≤ 1°. 롤·피치 판정(pd_gate.py와 같은 기준)도 합격이다.
     초기 |ψ|는 최대 0.3 rad(17.2°)다.
   - 판정하는 줄은 params.yaml의 rotor.enabled를 따른다. 꺼져 있으면(기본) A·회전자 항 끔 한 줄이다(#65와 같다).
     켜져 있으면 A와 B의 회전자 항 켬 줄 전부다. 산 EDF의 회전 방향을 아직 몰라서 spin_dir ±1을 둘 다 본다.
     나머지 줄은 참고로 출력하고 판정하지 않는다.
   - 참고(판정 안 함): 롤만 0.2 rad 기울인 초기조건(랜덤화 끔)에서 피치로 넘어간 최대 |θ|.
     마스터 설계 TC-2.5(자이로 결합 관찰: 롤 입력 → 피치 응답)와 같은 꼴이다.
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

# 회전자 항 검사(#86)
THROTTLE_HOVER = 0.75   # 호버 스로틀 추정 √(735 g / 1300 gf), 01 문서 §8.1. 시나리오 B와 반작용 손계산에 쓴다
STEP_TIME_S = 1.0       # 시나리오 B에서 스로틀을 바꾸는 시각
GYRO_W0 = 0.5           # rad/s, 자이로 손계산의 첫 롤 각속도
GYRO_STEPS = 30         # 0.3 s
NORM_TOL = 1e-4         # 자이로 손계산에서 |ω| 보존 허용 상대오차
ROLL_STEP_RAD = 0.2     # 참고 지표(TC-2.5 꼴)의 첫 롤각
THRUST_PROBE_STEPS = 5  # 추력 지연 손계산(#122): 계단 뒤 이 스텝째에 롤 명령을 준다. 명목 tau 0.05 s = 5 스텝
SLEW_TOL = 1e-5         # 변화율 손계산(#120) 허용 오차. 행동이 float32라 스텝마다 6e-8쯤 반올림이 쌓인다.
                        # 0.25/s에서 한 스텝 변화량 0.0025의 0.4 %라서 변화율이 틀리면 잡힌다

# 베인 명령 [a1, a2, a3, a4, throttle(-1~1)]
COMMANDS = {
    "롤 [1,0,1,0]": [1, 0, 1, 0, 1],
    "피치 [0,1,0,1]": [0, 1, 0, 1, 1],
    "요 [1,-1,-1,1]": [1, -1, -1, 1, 1],
    "섞음": [0.3, -0.7, 0.5, 0.2, 0.2],
}


def hand_geometry(p):
    """params.yaml의 vane_geometry에서 잠긴 면적 A_fin(m^2), 요 팔 r(m), 배기 단면적 A_duct(m^2)를 손계산한다(#98, #117).

    hopper_aviary.vane_geometry()를 쓰지 않는다. r은 정의대로 구한다: 유속이 균일하면 압력중심은
    잠긴 면적의 도심이다. r = ∫ r·c dr / ∫ c dr (구간 r0-r1, 시위 c 일정) = c·(r1² − r0²)/2 / A_fin.
    A_duct는 제트 단면 = 반지름 r1인 원 전체의 넓이 π·r1²다(#117 결정 (a). 꼬리 원뿔 단면은 빼지 않는다).
    """
    g = p["vane_geometry"]
    r0, r1, c = (g[k] / 1000.0 for k in ("inner_r_mm", "outer_r_mm", "chord_mm"))
    A_fin = (r1 - r0) * c
    return A_fin, c * (r1**2 - r0**2) / 2.0 / A_fin, np.pi * r1**2


def hand_torque(p, action, thrust_throttle=None):
    """베인 4장의 힘으로 몸체 토크 τ(N·m, 3벡터)를 손계산한다.

    추력은 thrust_throttle(0-1)로 계산한다. 없으면 action의 스로틀을 쓴다(지연 없음).

    위치 pᵢ: 좌표계(AGENTS.md §프로젝트 한눈에)대로 베인 1-4는 +X, +Y, −X, −Y에 있다.
      z축에서 반경 r, 무게중심에서 아래로 l → pᵢ = (r cos θᵢ, r sin θᵢ, −l), θᵢ = 0°, 90°, 180°, 270°.
    힘 Fᵢ = CL · Ft · αᵢ (논문 식 3.16). 방향은 논문 식 3.19의 롤·피치 행에서 정해진다:
      τx = (F1+F3)·l이면 베인 1·3의 힘은 +Y, τy = −(F2+F4)·l이면 베인 2·4의 힘은 +X다.
    요 행 τz = (F1−F2−F3+F4)·r은 쓰지 않는다. 위 위치와 방향의 외적에서 따로 나와야 한다.
    """
    A_fin, r, A_duct = hand_geometry(p)
    CL = p["CLalpha"] * A_fin / (2.0 * A_duct)
    alpha = np.asarray(action[:4], dtype=float) * np.deg2rad(p["alpha_max_deg"])
    throttle = (action[4] + 1.0) / 2.0 if thrust_throttle is None else thrust_throttle
    Ft = p["Kf"] * (throttle * p["omega_t_per_throttle"]) ** 2
    l = p["vane_arm_l"]
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
    A_fin, r, A_duct = hand_geometry(p)
    print(f"   vane_arm_l = {p['vane_arm_l']} m, vane_geometry 손계산: r = {r:.6g} m, A_fin = {A_fin:.6g} m², "
          f"A_duct = {A_duct:.6g} m²\n")
    failures = []
    for name, value in (("vane_arm_l", p["vane_arm_l"]), ("r", r), ("A_fin", A_fin), ("A_duct", A_duct)):
        if not value > 0:
            failures.append(f"{name} = {value}: 거리·면적이라서 0보다 커야 한다")

    J = np.array([p["Jxx"], p["Jyy"], p["Jzz"]])
    for rotor in (False, True):   # 회전자 항(#86) 끔, 켬
        label = f"회전자 항 {'켬' if rotor else '끔'}"
        env = HopperAttitudeEnv()
        env.dr = {"enabled": False}   # 명목값 한 점. 무게중심 오프셋도 0이다
        env.rotor_enabled = rotor
        env.servo_enabled = False     # 손계산은 명령각이 바로 베인각이라고 본다. 서보 모델은 2번 마.에서 본다(#161)
        print(f"   {label}\n")
        print("   | 명령 | 환경 Δω (rad/s) | 손계산 Δω (rad/s) |")
        print("   |---|---|---|")
        for name, action in COMMANDS.items():
            got = env_delta_omega(env, action)
            want = hand_delta_omega(p, action, J, env.dt, rotor)
            print(f"   | {name} | {np.array2string(got, precision=5)} | {np.array2string(want, precision=5)} |")
            for axis, g, w in zip("xyz", got, want):
                where = f"{label}, {name}: Δω{axis}"
                if not np.isfinite(g):
                    failures.append(f"{where} = {g} (유한한 값이 아니다)")
                elif abs(w) < LEAK_TOL:
                    if abs(g) > LEAK_TOL:
                        failures.append(f"{where} = {g:.3g}, 손계산은 0 (누설)")
                elif np.sign(g) != np.sign(w):
                    failures.append(f"{where} = {g:.5g}, 손계산 {w:.5g} (부호가 다름)")
                elif abs(g - w) > REL_TOL * abs(w):
                    failures.append(f"{where} = {g:.5g}, 손계산 {w:.5g} (크기가 다름)")

        yaw = env_delta_omega(env, COMMANDS["요 [1,-1,-1,1]"])
        if not yaw[2] > 0:
            failures.append(f"{label}: 요 명령 [1,-1,-1,1]의 Δωz = {yaw[2]:.5g}. +ωz여야 한다")
        print()
    return failures


def cross_matrix(v):
    """[v]×: 벡터 v와의 외적을 행렬로 쓴 것. [v]× · u = v × u."""
    return np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])


def throttle_action(throttle, vanes=(0.0, 0.0, 0.0, 0.0)):
    """스로틀(0-1)을 행동 벡터의 -1~1 값으로 바꾼다."""
    return np.array([*vanes, 2.0 * throttle - 1.0], dtype=np.float32)


def hand_delta_omega(p, action, J, dt, rotor):
    """ω = 0, 자세 0에서 한 스텝 뒤 Δω(rad/s, 3벡터)를 손계산한다.

    회전자 항이 꺼져 있으면 Δω = dt·τ/J다. 켜져 있으면 회전자 각운동량 h = s·I_r·Ω·e_z,
    Ω = omega_max·throttle(첫 스텝이라 회전자가 이미 이 회전수로 돈다)로 두고
    사다리꼴 식 J·Δω = dt·(τ + [h]×·(ω0 + ω1)/2), ω0 = 0을 푼다. 자이로 토크 −ω × h = [h]×·ω다.
    """
    tau = hand_torque(p, action)
    if not rotor:
        return tau / J * dt
    r = p["rotor"]
    throttle = (action[4] + 1.0) / 2.0
    h = np.array([0.0, 0.0, r["spin_dir"] * r["inertia"] * r["omega_max"] * throttle])
    return np.linalg.solve(np.diag(J) - 0.5 * dt * cross_matrix(h), dt * tau)


def rotor_env(spin):
    env = HopperAttitudeEnv()
    env.dr = {"enabled": False}
    env.rotor_enabled = True
    env.rotor_spin_dir = spin
    env.throttle_slew_rate = None   # 가-다는 회전자 식만 본다. 변화율 제한은 라.에서 따로 본다
    env.servo_enabled = False       # 다.의 롤 명령이 바로 베인각이 되게 한다. 서보 모델은 마.에서 따로 본다(#161)
    env.reset(seed=0)
    return env


def check_rotor_reaction(p, spin):
    """가. 반작용: 스로틀 계단에서 z축 각운동량 보존과 회전수가 다 따라간 뒤의 Δωz."""
    r = p["rotor"]
    env = rotor_env(spin)
    env.state = np.zeros(6, dtype=np.float32)
    obs, *_ = env.step(throttle_action(1.0))   # 첫 스텝: 회전자가 이미 omega_max로 돌고 있었다고 둔다
    momentum0 = p["Jzz"] * float(obs[5]) + spin * r["inertia"] * env.rotor_omega
    # 시상수의 20배(최소 1 s) 동안 계단 뒤 스로틀을 유지한다. 남는 지연은 e^-20 ≈ 2e-9배라 무시한다
    steps = int(np.ceil(max(1.0, 20.0 * r["tau"]) / env.dt))
    drift = 0.0
    for _ in range(steps):
        obs, *_ = env.step(throttle_action(THROTTLE_HOVER))
        momentum = p["Jzz"] * float(obs[5]) + spin * r["inertia"] * env.rotor_omega
        drift = max(drift, abs(momentum - momentum0))
    got = float(obs[5])
    want = -spin * r["inertia"] * r["omega_max"] * (THROTTLE_HOVER - 1.0) / p["Jzz"]
    where = f"반작용 spin_dir {spin:+d}"
    print(f"   가. {where}: {steps * env.dt:.1f} s 뒤 ωz = {got:.5f} rad/s, 손계산 {want:.5f} rad/s, "
          f"z축 각운동량 변화 최대 {drift:.2e} N·m·s")
    failures = []
    if drift > REL_TOL * r["inertia"] * r["omega_max"]:
        failures.append(f"{where}: z축 각운동량 Jzz·ωz + s·I_r·Ω가 {drift:.3g} N·m·s 변했다 (보존되지 않음)")
    if np.sign(got) != np.sign(want) or abs(got - want) > REL_TOL * abs(want):
        failures.append(f"{where}: ωz = {got:.5g}, 손계산 {want:.5g} (부호나 크기가 다름)")
    if max(abs(obs[3]), abs(obs[4])) > LEAK_TOL:
        failures.append(f"{where}: ωx = {obs[3]:.3g}, ωy = {obs[4]:.3g}, 손계산은 0 (누설)")
    return failures


def check_rotor_gyro(p, spin):
    """나. 자이로: 대칭 기체의 자유 세차를 해석해와 비교한다."""
    r = p["rotor"]
    env = rotor_env(spin)
    env.Jyy = env.Jxx   # 대칭 기체. 그래야 (ωx, ωy)의 해석해가 원 운동이고 ωz가 0으로 남는다
    env.state = np.array([0.0, 0.0, 0.0, GYRO_W0, 0.0, 0.0], dtype=np.float32)
    for _ in range(GYRO_STEPS):
        obs, *_ = env.step(throttle_action(1.0))
    rate = spin * r["inertia"] * r["omega_max"] / p["Jxx"]   # rad/s, +Z축 둘레 세차 각속도
    t = GYRO_STEPS * env.dt
    want = GYRO_W0 * np.array([np.cos(rate * t), np.sin(rate * t)])
    got = obs[3:5].astype(float)
    norm_err = abs(np.hypot(*got) - GYRO_W0) / GYRO_W0
    phase_tol = GYRO_STEPS * abs(rate * env.dt) ** 3 / 12.0   # 사다리꼴 규칙의 위상 오차(rad)
    vec_tol = GYRO_W0 * (2.0 * phase_tol + NORM_TOL)
    where = f"자이로 spin_dir {spin:+d}"
    print(f"   나. {where}: {t:.1f} s 뒤 (ωx, ωy) = {np.array2string(got, precision=5)}, "
          f"해석해 {np.array2string(want, precision=5)} rad/s (세차 {rate:+.3f} rad/s), |ω| 상대오차 {norm_err:.1e}")
    failures = []
    if not norm_err <= NORM_TOL:
        failures.append(f"{where}: |ω| 상대오차 {norm_err:.3g} > {NORM_TOL:g} (회전 에너지가 보존되지 않음)")
    if not np.linalg.norm(got - want) <= vec_tol:
        failures.append(f"{where}: (ωx, ωy) = {got}, 해석해 {want} (차이 {np.linalg.norm(got - want):.3g} > {vec_tol:.3g})")
    if abs(obs[5]) > LEAK_TOL:
        failures.append(f"{where}: ωz = {obs[5]:.3g}, 해석해는 0 (누설)")
    return failures


def check_thrust_lag(p, spin):
    """다. 추력 지연(#122): 계단 뒤 THRUST_PROBE_STEPS번째 스텝에 롤 명령을 주고 Δω로 추력을 잰다.

    그 스텝 전에는 베인이 0이고 무게중심 오프셋도 0이라 ωx = ωy = 0이다. ω가 h와 나란해서 자이로 항은
    hand_delta_omega와 같은 꼴 (J − dt/2·[h]×)·Δω = dt·τ이다. h는 그 스텝의 평균 회전수로 계산한다.
    z축에는 반작용 −s·I_r·(Ω_k − Ω_(k−1))/Jzz가 더해진다. 롤 명령은 τz를 만들지 않는다.
    """
    r = p["rotor"]
    env = rotor_env(spin)
    env.state = np.zeros(6, dtype=np.float32)
    env.step(throttle_action(1.0))   # 첫 스텝: 회전자가 이미 omega_max로 돌고 있었다고 둔다(u = 1)
    for _ in range(THRUST_PROBE_STEPS - 1):
        env.step(throttle_action(THROTTLE_HOVER))
    before = env.state.astype(float)
    action = throttle_action(THROTTLE_HOVER, vanes=COMMANDS["롤 [1,0,1,0]"][:4])
    obs, *_ = env.step(action)
    got = obs[3:6].astype(float) - before[3:6]

    decay = np.exp(-env.dt / r["tau"]) if r["tau"] > 0 else 0.0
    u0, u1 = (THROTTLE_HOVER + (1.0 - THROTTLE_HOVER) * decay**k for k in (THRUST_PROBE_STEPS - 1, THRUST_PROBE_STEPS))
    J = np.array([p["Jxx"], p["Jyy"], p["Jzz"]])
    h = np.array([0.0, 0.0, spin * r["inertia"] * r["omega_max"] * 0.5 * (u0 + u1)])
    want = np.linalg.solve(np.diag(J) - 0.5 * env.dt * cross_matrix(h), env.dt * hand_torque(p, action, u1))
    want[2] -= spin * r["inertia"] * r["omega_max"] * (u1 - u0) / p["Jzz"]
    no_lag = hand_torque(p, action)[0] / p["Jxx"] * env.dt   # 지연 없는 추력이면 나올 Δωx(참고)

    where = f"추력 지연 spin_dir {spin:+d}"
    print(f"   다. {where}: 계단 뒤 {THRUST_PROBE_STEPS}번째 스텝 u = Ω/omega_max = {u1:.4f}, "
          f"Δω = {np.array2string(got, precision=5)}, 손계산 {np.array2string(want, precision=5)} rad/s "
          f"(지연 없는 추력이면 Δωx 약 {no_lag:.5f})")
    failures = []
    for axis, g, w in zip("xyz", got, want):
        if not np.isfinite(g) or np.sign(g) != np.sign(w) or abs(g - w) > REL_TOL * abs(w):
            failures.append(f"{where}: Δω{axis} = {g:.6g}, 손계산 {w:.6g} (추력이 지연된 회전수를 따르지 않음)")
    return failures


def check_slew(p):
    """라. 스로틀 변화율 제한(#120): 명령 계단 1.0 → 0.75 → 1.0에서 실제 스로틀이 경사로 바뀌는지 본다."""
    rate = p["throttle_slew_rate"]
    if rate is None:
        print("   라. 스로틀 변화율 제한: params.yaml throttle_slew_rate = null (제한 없음, 검사 건너뜀)")
        return []
    env = HopperAttitudeEnv()
    env.dr = {"enabled": False}
    env.servo_enabled = False   # 베인 0 명령이라 결과는 같다. 서보 모델은 마.에서 본다
    env.reset(seed=0)
    d = rate * env.dt
    n = int(np.ceil((1.0 - THROTTLE_HOVER) / d)) + 5   # 경사가 끝나고 5스텝 더
    commands = [1.0] + [THROTTLE_HOVER] * n + [1.0] * n
    want, got = [], []
    for k, cmd in enumerate(commands):
        _, _, _, _, info = env.step(throttle_action(cmd))
        got.append(info["throttle"])
        # 손계산: 첫 스텝은 명령 그대로. 그 뒤는 명령 쪽으로 d씩 가고 명령에서 멈춘다
        prev = want[-1] if want else cmd
        want.append(cmd if k == 0 else min(max(cmd, prev - d), prev + d))
    ramp_s = (1.0 - THROTTLE_HOVER) / rate
    err = float(np.max(np.abs(np.array(got) - np.array(want))))
    print(f"   라. 스로틀 변화율 제한 {rate:g}/s: 명령 1.0 → {THROTTLE_HOVER:g} → 1.0, 경사 {ramp_s:.2f} s씩, "
          f"실제 스로틀과 손계산의 차이 최대 {err:.1e}")
    failures = []
    if not err <= SLEW_TOL:
        failures.append(f"라. 스로틀 변화율 제한: 실제 스로틀이 손계산과 {err:.3g} 다르다 (허용 {SLEW_TOL:g})")
    if abs(got[0] - 1.0) > SLEW_TOL:
        failures.append(f"라. 스로틀 변화율 제한: 첫 스텝 스로틀 {got[0]:.6g}, 명령 1.0 그대로여야 한다")
    return failures


def servo_env(p):
    """서보 모델을 켠 명목 환경(랜덤화·회전자 항·스로틀 변화율 제한 끔). 상수는 params.yaml servo 블록이다."""
    env = HopperAttitudeEnv()
    env.dr = {"enabled": False}
    env.rotor_enabled = False
    env.throttle_slew_rate = None
    env.servo_enabled = True
    env.reset(seed=0)
    env.state = np.zeros(6, dtype=np.float32)
    return env


def vane_action(a1):
    """베인 1만 a1(-1~1), 나머지 0, 스로틀 1.0인 행동."""
    return np.array([a1, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)


def check_servo(p):
    """마. 베인 서보 동특성(#161): 1차 지연 해석해, 데드밴드, 속도 제한을 본다."""
    sv = p.get("servo")
    if sv is None:
        print("   마. 베인 서보 동특성: params.yaml에 servo 블록이 없다 (검사 건너뜀)")
        return []
    failures = []
    alpha_max = np.deg2rad(p["alpha_max_deg"])
    tau, rate, band = sv["tau"], np.deg2rad(sv["rate_max_dps"]), np.deg2rad(sv["deadband_deg"])

    # (1) 1차 지연: 0 → +alpha_max 계단. 속도 제한이 걸리지 않을 때만 해석해와 같다
    env = servo_env(p)
    lag_ok = tau > 0 and alpha_max / tau <= rate
    if lag_ok:
        worst, before = 0.0, env.state.astype(float)
        for k in range(1, THRUST_PROBE_STEPS + 1):
            obs, *_ = env.step(vane_action(1.0))
            want = alpha_max * (1.0 - np.exp(-k * env.dt / tau))
            worst = max(worst, abs(env.vane_alpha[0] - want) / want)
            got_dw = float(obs[3]) - before[3]
            before = obs.astype(float)
        # 마지막 스텝의 Δωx: 그 스텝 끝 베인각으로 손계산한 토크. 회전자 항이 꺼져 있고 ωy = ωz = 0이라 교차항은 0이다
        frac = float(env.vane_alpha[0] / alpha_max)
        want_dw = hand_torque(p, vane_action(frac))[0] / p["Jxx"] * env.dt
        dw_err = abs(got_dw - want_dw) / abs(want_dw)
        print(f"   마. (1) 1차 지연 tau {tau:g} s: 계단 뒤 1-{THRUST_PROBE_STEPS} 스텝 베인각과 해석해의 상대오차 최대 {worst:.1e}, "
              f"{THRUST_PROBE_STEPS}번째 스텝 베인각 {np.degrees(env.vane_alpha[0]):.3f}°, Δωx {got_dw:.5f} (손계산 {want_dw:.5f}) rad/s")
        if not worst <= REL_TOL:
            failures.append(f"마. 서보 1차 지연: 베인각이 해석해와 상대오차 {worst:.3g}만큼 다르다")
        if not dw_err <= REL_TOL:
            failures.append(f"마. 서보 1차 지연: Δωx {got_dw:.6g}, 손계산 {want_dw:.6g} (힘이 스텝 끝 베인각을 따르지 않음)")
    else:
        print(f"   마. (1) 1차 지연: tau {tau:g} s에서 속도 제한이 먼저 걸리거나 지연이 없어 해석해 비교를 건너뜀")

    # (2) 데드밴드: 0.5 명령으로 멈출 때까지 보낸 뒤 데드밴드의 절반, 2배만큼 명령을 바꾼다
    env = servo_env(p)
    for _ in range(int(np.ceil(max(1.0, 20.0 * tau) / env.dt))):
        env.step(vane_action(0.5))
    # 1차 지연은 오차가 데드밴드 안에 들어오는 스텝에 멈춘다. 그래서 멈춘 베인각은 명령보다 최대 데드밴드만큼 모자란다
    rest = float(env.vane_alpha[0])
    short = 0.5 * alpha_max - rest
    env.step(vane_action((rest + 0.5 * band) / alpha_max))   # 현재 베인각에서 데드밴드의 절반
    small = float(env.vane_alpha[0]) - rest
    env.step(vane_action((rest + 2.0 * band) / alpha_max))   # 현재 베인각에서 데드밴드의 2배
    large = float(env.vane_alpha[0]) - rest
    print(f"   마. (2) 데드밴드 {np.degrees(band):g}°: 명령 {np.degrees(0.5 * alpha_max):g}°에서 멈춘 베인각은 {np.degrees(short):.3f}° 모자란다. "
          f"베인각 +{np.degrees(0.5 * band):.3f}° 명령 → 베인 {np.degrees(small):+.2e}°, +{np.degrees(2.0 * band):.3f}° 명령 → 베인 {np.degrees(large):+.2e}°")
    if not 0.0 <= short < band + 1e-12:
        failures.append(f"마. 서보 데드밴드: 멈춘 베인각이 명령보다 {np.degrees(short):.3g}° 모자란다 (0 이상 데드밴드 미만이어야 한다)")
    if band > 0 and small != 0.0:
        failures.append(f"마. 서보 데드밴드: 데드밴드 안의 명령 변화에 베인이 {np.degrees(small):.3g}° 움직였다")
    if not large > 0:
        failures.append(f"마. 서보 데드밴드: 데드밴드 밖의 명령 변화에 베인이 움직이지 않았다 ({np.degrees(large):.3g}°)")

    # (3) 속도 제한: tau = 0이면 1차 지연이 없어 계단이 속도 제한만으로 경사가 된다
    env = servo_env(p)
    env.servo_tau = 0.0
    env.step(vane_action(-1.0))   # 첫 스텝: 중립(0)에서 −alpha_max 쪽으로 간다
    for _ in range(int(np.ceil(alpha_max / (rate * env.dt))) + 1):
        env.step(vane_action(-1.0))
    start = float(env.vane_alpha[0])
    n = int(np.ceil(2.0 * alpha_max / (rate * env.dt))) + 2
    got, want = [], []
    for k in range(1, n + 1):
        env.step(vane_action(1.0))
        got.append(float(env.vane_alpha[0]))
        want.append(min(start + k * rate * env.dt, alpha_max))
    err = float(np.max(np.abs(np.array(got) - np.array(want))))
    print(f"   마. (3) 속도 제한 {np.degrees(rate):g}°/s(tau 0): -{np.degrees(alpha_max):g}° → +{np.degrees(alpha_max):g}° 계단, "
          f"{n} 스텝 동안 손계산과 차이 최대 {err:.1e} rad")
    if not err <= 1e-9:
        failures.append(f"마. 서보 속도 제한: 베인각이 손계산 경사와 {err:.3g} rad 다르다")
    return failures


def check_rotor(p):
    r = p["rotor"]
    print("2. 회전자 항·스로틀 변화율·서보 손계산 (랜덤화 끔. 가-다는 회전자 항 켬, 변화율 제한 끔. 마.만 서보 모델 켬)")
    print(f"   inertia = {r['inertia']:g} kg·m², omega_max = {r['omega_max']:g} rad/s, tau = {r['tau']:g} s "
          f"(params.yaml rotor 명목값, 추정값)\n")
    failures = []
    for spin in (1, -1):
        failures += check_rotor_reaction(p, spin)
    for spin in (1, -1):
        failures += check_rotor_gyro(p, spin)
    for spin in (1, -1):
        failures += check_thrust_lag(p, spin)
    failures += check_slew(p)
    failures += check_servo(p)
    print()
    return failures


def pd_with_yaw(obs, kp=8.0, kd=2.0):
    """pd_gate.pd()에 요 PD를 섞는다. 요 명령 [1,-1,-1,1] 방향이 +τz다."""
    a = pd(obs)
    uz = np.clip(-kp * obs[2] - kd * obs[5], -1, 1)
    a[:4] = np.clip(a[:4] + uz * np.array([1, -1, -1, 1]), -1, 1)
    return a


def run_yaw_pd(rotor=False, spin=1, step_throttle=None):
    """평가 seed 전부로 요 PD를 돌린다. step_throttle이 있으면 STEP_TIME_S에 스로틀을 그 값으로 바꾼다."""
    env = HopperAttitudeEnv()
    if not env.dr.get("enabled", False):
        raise ValueError("params.yaml의 domain_rand.enabled가 false다. 요 PD 기준은 랜덤화를 켠 상태에서만 잰다.")
    env.rotor_enabled = rotor
    env.rotor_spin_dir = spin
    step_k = round(STEP_TIME_S / env.dt)
    initial, final, peak, crashes, tilts = [], [], [], [], []
    for s in EVAL_SEEDS:
        obs, _ = env.reset(seed=s)
        initial.append(abs(obs[2]))
        k, top, done = 0, abs(obs[2]), False
        while not done:
            a = pd_with_yaw(obs)
            if step_throttle is not None and k >= step_k:
                a[4] = 2.0 * step_throttle - 1.0
            obs, _, term, trunc, _ = env.step(a)
            k += 1
            top = max(top, abs(obs[2]))
            done = term or trunc
        final.append(abs(obs[2]))
        peak.append(top)
        crashes.append(term)
        tilts.append(np.degrees(np.hypot(obs[0], obs[1])))
    final_deg = np.degrees(final)
    return {
        "initial_max_deg": float(np.degrees(np.max(initial))),
        "final_max_deg": float(np.max(final_deg)),
        "final_median_deg": float(np.median(final_deg)),
        "peak_max_deg": float(np.degrees(np.max(peak))),
        "n_final_over": int(np.sum(final_deg > MAX_FINAL_YAW_DEG)),
        "crash": float(np.mean(crashes)),
        "median_tilt_deg": float(np.median(tilts)),
    }


def roll_step_pitch_peak(rotor, spin=1):
    """참고 지표: 롤만 ROLL_STEP_RAD 기울인 초기조건(랜덤화 끔)에서 요 PD를 돌릴 때 피치 최대 |θ|(°)."""
    env = HopperAttitudeEnv()
    env.dr = {"enabled": False}
    env.rotor_enabled = rotor
    env.rotor_spin_dir = spin
    env.reset(seed=0)
    env.state = np.array([ROLL_STEP_RAD, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    obs, peak, done = env.state.copy(), 0.0, False
    while not done:
        obs, _, term, trunc, _ = env.step(pd_with_yaw(obs))
        peak = max(peak, abs(float(obs[1])))
        done = term or trunc
    return float(np.degrees(peak))


def check_yaw_pd(rotor_switch, slew_rate):
    print(f"3. 요 PD (랜덤화 켬, 회전자 상수 포함, 평가 seed {EVAL_SEEDS.start}-{EVAL_SEEDS.stop - 1}, kp=8, kd=2)")
    print(f"   A: 스로틀 1.0 고정. B: t = {STEP_TIME_S:g} s에 스로틀 명령 1.0 → {THROTTLE_HOVER:g} 계단(호버 추정)")
    print("   스로틀 변화율 제한(params.yaml throttle_slew_rate): "
          + (f"{slew_rate:g}/s → B의 실제 스로틀은 {(1.0 - THROTTLE_HOVER) / slew_rate:.2f} s에 걸쳐 바뀐다"
             if slew_rate is not None else "없음 → B의 실제 스로틀도 계단이다"))
    print(f"   params.yaml rotor.enabled = {str(rotor_switch).lower()} → "
          + ("A·B의 회전자 항 켬 줄을 판정한다\n" if rotor_switch else "A·회전자 항 끔 줄만 판정한다\n"))
    print("   각은 전부 |ψ|(°)다. 넘어진 seed의 마지막 값은 넘어진 순간의 값이다.\n")
    print("   | 시나리오 | 회전자 항 | 마지막 최댓값 | 마지막 중앙값 | 도중 최댓값 | 마지막 > 1° seed | "
          "넘어짐 | 최종 기울기 중앙값 | 판정 |")
    print("   |---|---|---|---|---|---|---|---|---|")
    failures = []
    initial_max = None
    for scenario, step_throttle in (("A", None), ("B", THROTTLE_HOVER)):
        for rotor, spin in ((False, 1), (True, 1), (True, -1)):
            m = run_yaw_pd(rotor, spin, step_throttle)
            initial_max = m["initial_max_deg"]
            ok = m["final_max_deg"] <= MAX_FINAL_YAW_DEG and gate_passes(m)
            judged = (rotor == rotor_switch) and (rotor or scenario == "A")
            label = f"켬 spin_dir {spin:+d}" if rotor else "끔"
            verdict = ("합격" if ok else "불합격") if judged else ("참고: 기준 만족" if ok else "참고: 기준 못 미침")
            print(f"   | {scenario} | {label} | {m['final_max_deg']:.3g} | {m['final_median_deg']:.2g} | "
                  f"{m['peak_max_deg']:.3g} | {m['n_final_over']} | {m['crash'] * 100:.1f} % | "
                  f"{m['median_tilt_deg']:.1f}° | {verdict} |", flush=True)
            if judged and not ok:
                where = f"시나리오 {scenario}, 회전자 항 {label}"
                if not m["final_max_deg"] <= MAX_FINAL_YAW_DEG:
                    failures.append(f"{where}: 마지막 |ψ| 최댓값 {m['final_max_deg']:.3f}° > {MAX_FINAL_YAW_DEG}°: "
                                    f"요 PD가 요 오차를 못 줄였다")
                if not gate_passes(m):
                    failures.append(f"{where}: 요를 섞은 뒤 롤·피치 판정 불합격 (기준: 넘어짐 ≤ {MAX_CRASH * 100:.0f} %, "
                                    f"중앙값 ≤ {MAX_MEDIAN_TILT_DEG:.0f}°)")
    print(f"\n   초기 |ψ| 최댓값 {initial_max:.2f}°")
    # print에 em dash처럼 cp949에 없는 문자를 쓰지 않는다. 한국어 Windows에서 출력을 파일로 돌리면
    # UnicodeEncodeError로 멈춘다(tasks.py _survive_console_encoding 참고)
    print(f"   참고(TC-2.5 꼴, 랜덤화 끔): 롤만 {ROLL_STEP_RAD} rad 기울였을 때 피치 최대 |θ|: "
          f"회전자 항 끔 {roll_step_pitch_peak(False):.3f}°, 켬 spin_dir +1 {roll_step_pitch_peak(True, 1):.3f}°, "
          f"-1 {roll_step_pitch_peak(True, -1):.3f}°")
    return failures


def main():
    with open(PARAMS, "r", encoding="utf-8") as f:
        p = yaml.safe_load(f)
    rotor_switch = bool(p.get("rotor", {}).get("enabled", False))
    failures = check_torque(p) + check_rotor(p) + check_yaw_pd(rotor_switch, p["throttle_slew_rate"])
    if failures:
        print("\n요 축 판정: 불합격")
        for msg in failures:
            print(f"   - {msg}")
        return 1
    print(f"\n요 축 판정: 합격 (토크 손계산 상대오차 ≤ {REL_TOL:g}, 누설 ≤ {LEAK_TOL:g} rad/s, "
          f"회전자 항·스로틀 변화율·서보 손계산 통과, 마지막 |ψ| ≤ {MAX_FINAL_YAW_DEG}°)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
