"""
고도 검사(#185). 스로틀 변화율 제한(params.yaml throttle_slew_rate)으로 고도·호버 제어가 되는지 잰다.

HopperAttitudeEnv는 위치를 구속한 자세 환경이라 고도(z) 동역학이 없다. 이 스크립트는 환경을 고치지 않는다.
환경의 한 스텝마다 세로 운동방정식을 옆에서 같이 적분한다:
    m·z'' = Ft·cos(phi)·cos(theta) − m·g          (병진 동역학 식 3.29-3.31의 z 성분, 공기 저항 없음)
    Ft    = Kf·(u·omega_t_per_throttle)²            (환경과 같은 식. u는 환경이 실제로 쓴 스로틀)
u는 변화율 제한 뒤 스로틀(info["throttle"])이다. 회전자 항을 켜면 지연된 회전수의 유효 스로틀 Ω/omega_max다(#122).
자세는 환경이 그대로 계산한다. 롤·피치는 pd_gate.py의 PD(kp=8, kd=2)가 잡는다. 기울면 세로 추력이 줄어든다.

고도 제어기: ArduPilot Copter의 세로 위치 제어기 꼴(위치 P → 속도 PI)이다.
    v_cmd = KP_POS·(z_ref − z) + v_ref
    a_cmd = KP_VEL·(v_cmd − vz) + I,   I += KI_VEL·(v_cmd − vz)·dt
    u_cmd = sqrt(m·(g + a_cmd) / (cos(phi)·cos(theta)) / (Kf_명목·omega_t_per_throttle²))   (추력 식의 역)
  KP_POS 1.0, KP_VEL 5.0은 ArduPilot Copter 기본값(PSC_D_POS_P, PSC_D_VEL_P)이다. 적분은 Kf 랜덤화(±20 %)로
  생긴 호버 스로틀 오차를 없앤다. 스로틀이 0·1에 걸리거나 변화율 제한에 걸린 스텝에는 적분하지 않는다(조건부 적분).
  제어기는 명목 Kf와 질량만 안다. 에피소드마다 뽑힌 실제 Kf는 모른다.

시나리오 (평가 seed 0-199, 도메인 랜덤화 켬, 초기 자세 교란은 환경 그대로 최대 0.3 rad):
  H 호버 유지: z = 1 m에서 명목 호버 스로틀로 시작한다. 목표 1 m 유지. 실제 호버 스로틀은 Kf에 따라 다르다.
    재는 값: |z − 1| 최댓값, 마지막 |z − 1|.
  L 착지 하강: H와 같게 시작하고 t = 1 s부터 0.5 m/s로 내린다(ArduPilot LAND_SPD_MS 기본값). 바닥 z = 0에 닿으면 끝낸다.
    재는 값: 하강 중 |z − z_ref| 최댓값, 접지 속도. 목표 접지 속도는 0.5 m/s다.
  각 시나리오를 변화율 제한 없음, 2.0, 1.0, 0.5, 0.25, 0.125/s로 같은 seed에서 돌린다. 기준은 "제한 없음" 줄이다.
  "필요 변화율"은 제한 없이 돌렸을 때 제어기가 낸 스로틀 명령의 |du/dt| 99번째 백분위수(초기 0.1 s 제외)다.

실행: python altitude_check.py               표만 출력한다. 합격 판정과 exit 1은 없다(참고용 검사).
      python altitude_check.py --rotor       회전자 항(#86)을 켜고 잰다(spin_dir +1)
"""
import argparse
import sys

import numpy as np

from hopper_aviary import G, HopperAttitudeEnv, hover_throttle
from pd_gate import EVAL_SEEDS, pd

KP_POS = 1.0              # 1/s,  ArduPilot Copter PSC_D_POS_P 기본값
KP_VEL = 5.0              # 1/s,  ArduPilot Copter PSC_D_VEL_P 기본값
KI_VEL = 2.0              # 1/s², 가정. Kf 오차를 1-2 s 안에 없애는 크기
Z0 = 1.0                  # m, 시작 고도와 호버 목표
LAND_START_S = 1.0        # s, 하강 시작 시각
LAND_SPEED = 0.5          # m/s, ArduPilot Copter LAND_SPD_MS 기본값(config.h LAND_SPD_MS_DEFAULT)
RATES = (None, 2.0, 1.0, 0.5, 0.25, 0.125)   # 1/s, None = 제한 없음
SKIP_S = 0.1              # s, 필요 변화율에서 빼는 초기 구간(첫 스텝은 환경이 제한하지 않는다)


def thrust(env, u):
    """환경과 같은 추력 식. u는 실제로 쓴 유효 스로틀(0-1)."""
    return env.Kf * (u * env.omega_t_per_throttle) ** 2


def effective_throttle(env, info):
    if env.rotor_enabled:
        return env.rotor_omega / env.rotor_omega_max
    return info["throttle"]


def run(env, seed, scenario):
    """한 seed를 돌리고 지표 사전을 돌려준다."""
    obs, _ = env.reset(seed=seed)
    k_nom = env.nominal_Kf * env.omega_t_per_throttle ** 2   # 제어기가 아는 추력 계수(명목)
    u_hover_nom = hover_throttle(env.mass, env.nominal_Kf, env.omega_t_per_throttle)
    z, vz, integ = Z0, 0.0, 0.0
    u_prev_cmd, u_applied = u_hover_nom, None
    max_err, cmd_rates, touchdown = 0.0, [], None
    for k in range(env.max_steps):
        t = k * env.dt
        if scenario == "L" and t >= LAND_START_S:
            z_ref, v_ref = max(Z0 - LAND_SPEED * (t - LAND_START_S), 0.0), -LAND_SPEED
        else:
            z_ref, v_ref = Z0, 0.0
        tilt_cos = max(np.cos(obs[0]) * np.cos(obs[1]), 0.5)
        v_cmd = KP_POS * (z_ref - z) + v_ref
        a_cmd = KP_VEL * (v_cmd - vz) + integ
        f_cmd = env.mass * (G + a_cmd) / tilt_cos
        u_cmd = float(np.sqrt(np.clip(f_cmd / k_nom, 0.0, 1.0)))
        if k > 0 and t >= SKIP_S:
            cmd_rates.append(abs(u_cmd - u_prev_cmd) / env.dt)
        u_prev_cmd = u_cmd

        action = pd(obs[:6])
        action[4] = 2.0 * u_cmd - 1.0
        obs, _, term, _, info = env.step(action)
        u_applied = info["throttle"]
        # 조건부 적분: 스로틀이 끝에 걸리거나 변화율 제한에 걸리면 적분하지 않는다(적분 누적 방지)
        if 0.0 < u_cmd < 1.0 and abs(u_applied - u_cmd) < 1e-9:
            integ += KI_VEL * (v_cmd - vz) * env.dt

        az = thrust(env, effective_throttle(env, info)) * np.cos(obs[0]) * np.cos(obs[1]) / env.mass - G
        vz += az * env.dt
        z += vz * env.dt
        max_err = max(max_err, abs(z - z_ref))
        if z <= 0.0:
            touchdown = -vz
            break
        if term:
            break
    return {
        "max_err": max_err,
        "final_err": abs(z - Z0),
        "touchdown": touchdown,
        "crash": bool(term),
        "need_rate": float(np.percentile(cmd_rates, 99)) if cmd_rates else 0.0,
    }


def summarize(env, scenario, rate):
    env.throttle_slew_rate = rate
    rows = [run(env, s, scenario) for s in EVAL_SEEDS]
    m = {
        "max_err_max": max(r["max_err"] for r in rows),
        "max_err_med": float(np.median([r["max_err"] for r in rows])),
        "final_err_max": max(r["final_err"] for r in rows),
        "crash": float(np.mean([r["crash"] for r in rows])),
        "need_rate_p99": float(np.percentile([r["need_rate"] for r in rows], 99)),
        "need_rate_med": float(np.median([r["need_rate"] for r in rows])),
    }
    td = [r["touchdown"] for r in rows if r["touchdown"] is not None]
    m["n_touchdown"] = len(td)
    m["touchdown_max"] = max(td) if td else float("nan")
    m["touchdown_med"] = float(np.median(td)) if td else float("nan")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rotor", action="store_true", help="회전자 항(#86)을 켜고 잰다(spin_dir +1)")
    args = ap.parse_args()

    env = HopperAttitudeEnv()
    if not env.dr.get("enabled", False):
        raise ValueError("params.yaml의 domain_rand.enabled가 false다. 이 검사는 랜덤화를 켠 상태에서만 잰다.")
    env.rotor_enabled = args.rotor or env.rotor_enabled
    k_nom = env.nominal_Kf * env.omega_t_per_throttle ** 2
    u_h = hover_throttle(env.mass, env.nominal_Kf, env.omega_t_per_throttle)
    kf_lo, kf_hi = 1 - env.dr.get("Kf_range", 0.0), 1 + env.dr.get("Kf_range", 0.0)
    print(f"고도 검사 (#185): 질량 {env.mass} kg, 최대 추력 {k_nom:.2f} N(명목), 회전자 항 "
          f"{'켬' if env.rotor_enabled else '끔'}, params.yaml throttle_slew_rate = {env.throttle_slew_rate}")
    print(f"   호버 스로틀: 명목 {u_h:.3f}, Kf {kf_hi:.2f}배 {u_h / np.sqrt(kf_hi):.3f}, Kf {kf_lo:.2f}배 {u_h / np.sqrt(kf_lo):.3f}")
    print(f"   호버에서 dFt/du = {2 * k_nom * u_h:.2f} N. 변화율 0.25/s이면 추력 변화 최대 {2 * k_nom * u_h * 0.25:.2f} N/s "
          f"= 세로 저크 {2 * k_nom * u_h * 0.25 / env.mass:.2f} m/s³")
    print(f"   제어기: 위치 P {KP_POS}, 속도 P {KP_VEL}, 속도 I {KI_VEL}. 평가 seed {EVAL_SEEDS.start}-{EVAL_SEEDS.stop - 1}\n")

    for scenario, title in (("H", "H 호버 유지 (목표 1 m, 5 s)"),
                            ("L", f"L 착지 하강 (t = {LAND_START_S:g} s부터 {LAND_SPEED} m/s, 목표 접지 속도 {LAND_SPEED} m/s)")):
        print(title)
        if scenario == "H":
            print("| 변화율 제한 | 고도 오차 최댓값 | 고도 오차 중앙값 | 마지막 오차 최댓값 | 넘어짐 | 필요 변화율 중앙값 | 필요 변화율 99 % |")
            print("|---|---|---|---|---|---|---|")
        else:
            print("| 변화율 제한 | 추종 오차 최댓값 | 추종 오차 중앙값 | 접지 seed | 접지 속도 최댓값 | 접지 속도 중앙값 | 넘어짐 |")
            print("|---|---|---|---|---|---|---|")
        for rate in RATES:
            m = summarize(env, scenario, rate)
            label = "없음" if rate is None else f"{rate:g}/s"
            if scenario == "H":
                print(f"| {label} | {m['max_err_max'] * 100:.1f} cm | {m['max_err_med'] * 100:.1f} cm | "
                      f"{m['final_err_max'] * 100:.2f} cm | {m['crash'] * 100:.1f} % | "
                      f"{m['need_rate_med']:.3f}/s | {m['need_rate_p99']:.3f}/s |", flush=True)
            else:
                print(f"| {label} | {m['max_err_max'] * 100:.1f} cm | {m['max_err_med'] * 100:.1f} cm | "
                      f"{m['n_touchdown']} | {m['touchdown_max']:.3f} m/s | {m['touchdown_med']:.3f} m/s | "
                      f"{m['crash'] * 100:.1f} % |", flush=True)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
