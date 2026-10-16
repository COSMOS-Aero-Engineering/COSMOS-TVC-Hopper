"""
이슈 #21 재현과 PRD #27 합격 판정 스크립트.

#21 본문의 재현 코드를 파일로 옮기고, params.yaml을 고치기 전에 후보 값을 미리 시험할 수 있게
명령줄 옵션을 붙였다. params.yaml은 읽기만 하고 바꾸지 않는다.

출력 세 가지:
  1) 재현표: 도메인 랜덤화(DR) 끔 / CG 오프셋만 0 / 켬 x 정책(zero, crash, pd)
  2) 제어력 점검: 베인 최대 토크를 추력 대비 등가 오프셋(mm)으로 바꾼 값 vs DR의 CG 오프셋,
     축당 베인 측력 합 vs 운동량 상한 Ft*sin(alpha_max)
  3) PRD #27 판정: DR 켬 + PD에서 넘어짐 5% 이하, 최종 기울기 중앙값 5도 이하, 상한 이내

실행 예 (레포 루트에서):
  python sim/sim_stage1/check_issue21.py                       # 지금 params.yaml 그대로
  python sim/sim_stage1/check_issue21.py --episodes 50         # 빠르게
  python sim/sim_stage1/check_issue21.py --clalpha-per-deg --arm-l 0.104
      # 후보 시험: CLalpha를 '도(deg)당' 값으로 보고 rad당으로 환산, 롤·피치 팔 104 mm
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hopper_aviary import HopperAttitudeEnv  # noqa: E402

PASS_CRASH_PCT = 5.0
PASS_TILT_DEG = 5.0


def zero_policy(o):
    return np.array([0, 0, 0, 0, 1.0], dtype=np.float32)


def crash_policy(o):
    return np.array([1, 0, 1, 0, 1.0], dtype=np.float32)


def pd_policy(o, kp=8.0, kd=2.0):
    phi, theta, psi, wx, wy, wz = o
    ux = np.clip(-kp * phi - kd * wx, -1, 1)   # tau_x = (F1+F3)*l
    uy = np.clip(kp * theta + kd * wy, -1, 1)  # tau_y = -(F2+F4)*l
    return np.array([ux, uy, ux, uy, 1.0], dtype=np.float32)


POLICIES = (("zero", zero_policy), ("crash", crash_policy), ("pd", pd_policy))


def make_env(args, mode):
    env = HopperAttitudeEnv()
    if args.clalpha is not None:
        env.CLalpha = args.clalpha
    if args.clalpha_per_deg:
        env.CLalpha = env.CLalpha * 180.0 / np.pi
    if args.arm_l is not None:
        env.nominal_l = args.arm_l
    if args.cg_offset_mm is not None:
        env.dr = dict(env.dr, cg_offset_mm=args.cg_offset_mm)
    if mode == "off":
        env.dr = {"enabled": False}
    elif mode == "no_cg":
        env.dr = dict(env.dr, cg_offset_mm=0.0)
    return env


def run(env, policy, n):
    rets, lens, crashes, tilts = [], [], [], []
    for s in range(n):
        o, _ = env.reset(seed=s)
        ret, t, done, term = 0.0, 0, False, False
        while not done:
            o, r, term, trunc, _ = env.step(policy(o))
            ret += r
            t += 1
            done = term or trunc
        rets.append(ret)
        lens.append(t)
        crashes.append(term)
        tilts.append(np.degrees(np.hypot(o[0], o[1])))
    return np.array(rets), np.array(lens), np.array(crashes), np.array(tilts)


def authority(env):
    """추력 Ft로 나눈 값이라 Kf와 무관하다(#21 '원인 계산')."""
    l, cl, a = env.nominal_l, env.CLalpha, env.alpha_max
    side_frac = 2 * cl * a                      # 축당 베인 2개 측력 합 / Ft
    equiv_mm = side_frac * l * 1000.0           # 베인 최대 토크 / Ft  (mm)
    bound_frac = np.sin(a)                      # 운동량 상한 / Ft
    cg_mm = env.dr.get("cg_offset_mm", 0.0) if env.dr.get("enabled", False) else 0.0
    return side_frac, equiv_mm, bound_frac, cg_mm


def main():
    ap = argparse.ArgumentParser(description="#21 재현 + #27 합격 판정")
    ap.add_argument("--episodes", type=int, default=200, help="정책·모드별 에피소드 수 (seed 0..N-1)")
    ap.add_argument("--clalpha", type=float, help="CLalpha 대신 쓸 값 (rad당)")
    ap.add_argument("--clalpha-per-deg", action="store_true",
                    help="CLalpha를 도(deg)당 값으로 보고 rad당으로 환산(x 57.3)")
    ap.add_argument("--arm-l", type=float, help="롤·피치 토크 팔 vane_arm_l 대신 쓸 값 (m)")
    ap.add_argument("--cg-offset-mm", type=float, help="DR의 cg_offset_mm 대신 쓸 값")
    args = ap.parse_args()

    base = make_env(args, "on")
    print(f"사용 값: CLalpha={base.CLalpha:.6g} /rad, vane_arm_l={base.nominal_l * 1000:.1f} mm, "
          f"alpha_max={np.degrees(base.alpha_max):.1f} deg, DR cg_offset_mm={base.dr.get('cg_offset_mm', 0.0)}")
    print()
    print(f"| DR | 정책 | 평균 리턴 | 평균 길이(step) | 넘어짐 | 최종 기울기 중앙값 |")
    print(f"|---|---|---|---|---|---|")
    verdict_row = None
    for mode in ("off", "no_cg", "on"):
        for name, pol in POLICIES:
            R, L, C, E = run(make_env(args, mode), pol, args.episodes)
            print(f"| {mode} | {name} | {R.mean():.2f} | {L.mean():.1f} | {C.mean() * 100:.1f} % | "
                  f"{np.median(E):.1f} deg |")
            if mode == "on" and name == "pd":
                verdict_row = (C.mean() * 100, float(np.median(E)))

    side_frac, equiv_mm, bound_frac, cg_mm = authority(base)
    print()
    print("제어력 점검 (추력 Ft 대비)")
    print(f"  축당 베인 측력 합 = {side_frac:.4f} Ft   운동량 상한 sin(alpha_max) = {bound_frac:.4f} Ft")
    print(f"  베인 최대 토크의 등가 오프셋 = {equiv_mm:.3f} mm   DR CG 오프셋 최대 = {cg_mm:.3f} mm")

    crash_pct, tilt = verdict_row
    ok_pd = crash_pct <= PASS_CRASH_PCT and tilt <= PASS_TILT_DEG
    ok_bound = side_frac <= bound_frac
    print()
    print(f"PRD #27 판정: DR 켬 + PD 넘어짐 {crash_pct:.1f} % (기준 <= {PASS_CRASH_PCT} %), "
          f"기울기 중앙값 {tilt:.1f} deg (기준 <= {PASS_TILT_DEG} deg), "
          f"상한 {'이내' if ok_bound else '초과(과대 추정)'}")
    print("  -> 합격" if (ok_pd and ok_bound) else "  -> 불합격: 원인과 다음 조치를 PR·이슈에 적는다")


if __name__ == "__main__":
    main()
