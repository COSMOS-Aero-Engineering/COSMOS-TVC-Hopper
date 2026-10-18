"""제어권한(control authority) 진단 — "이 과제가 애초에 풀 수 있는 것인가"를 먼저 묻는다.

    python authority.py

왜 이게 필요한가 (2026-09-18 발견)
----------------------------------
커넥톰 비교군을 붙이고 PD baseline을 돌려봤더니 5초 에피소드 내내 한 번도 수평으로
복원하지 못했다. 게인 탓인 줄 알고 격자탐색을 하려다, 그 전에 물리 상수로 **최대로
낼 수 있는 토크**를 직접 계산해봤다:

    당시 params.yaml 값 (Kf=3e-8) 기준
      스로틀 100%: 추력 0.27 N · 최대 베인토크 4.0e-5 Nm · 각가속도 0.008 rad/s^2
      -> 5초를 전부 써도 자세를 5.8도밖에 못 바꾼다
    그런데 reset()의 초기 교란은 +-17도다.

즉 **어떤 제어기를 넣어도 Stage 1 과제를 풀 수 없다.** PD도, MLP도, 커넥톰도 똑같이
실패하고, 그러면 네 비교군의 점수가 다 같이 바닥에 깔려서 비교 자체에 정보가 없다.
"물리 상수가 PLACEHOLDER라 절대 수치가 무의미하다"보다 한 단계 더 나쁜 상황이다 —
숫자가 부정확한 게 아니라 과제가 성립하지 않는다.

원인은 Kf로 보인다. params.yaml은 Ft = Kf * omega^2 이고 omega는 throttle*3000 인데,
64mm급 EDF의 실제 정적추력은 8~12 N 수준이다. 그러려면 Kf가 1e-6 근처여야 하는데
당시 값은 3e-8 로 약 37배 작았다. (params.yaml 스스로 "임시 스케일, 절대값 의미 없음"이라
적어둔 그대로다 — 틀린 값이 아니라 아직 안 채운 값이다.)

그 뒤 (2026-10-18 기준)
-----------------------
위 숫자는 2026-09-18 당시 기록이다. 그 뒤 상수가 두 번 바뀌었다.
  - 2026-09-19 PR #10: Kf를 1.1e-6으로 잠정 보정했다(100% 스로틀 추력 9.9 N).
  - PR #35(#21): 베인 양력 계수 CL(논문 식 3.16)과 vane_arm_l을 다시 계산했다.
2026-10-18 params.yaml로는 여유 배수가 약 533배라 경고가 나오지 않는다. 지금 값은
`python authority.py`로 본다. 경고 문구는 위의 옛 숫자가 아니라 그때 읽은 params.yaml의
Kf를 출력한다(#129).

이 파일은 값을 고치지 않는다. params.yaml은 실험 A(EDF 추력곡선)의 산출물이고 실측으로
채울 자리다. 여기서는 **학습을 돌리기 전에 그 사실을 알려주는 것**까지만 한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

PARAMS = Path(__file__).resolve().parents[1] / "sim_stage1" / "params.yaml"
sys.path.insert(0, str(PARAMS.parent))
from hopper_aviary import vane_lift_gain  # noqa: E402  (gymnasium만 딸려 온다, torch는 안 온다)

# reset()의 초기 교란 범위(rad)와 에피소드 길이(s) — hopper_aviary.py 와 맞춰둔 값.
# 저기를 고치면 여기도 고쳐야 한다. 자동으로 읽지 않는 이유는 env를 만들면 SB3/torch까지
# 딸려 들어와서, 이 진단만 빨리 돌려보고 싶을 때 무거워지기 때문이다.
INIT_TILT_RAD = 0.3
EPISODE_S = 5.0

# 64mm급 EDF 정적추력의 대략 범위(N). params.yaml의 Kf 주석(2026-09-19)과 같은 근거다.
# 경고가 "이 추력이면 Kf가 얼마여야 하나"를 지금 omega_t_per_throttle로 다시 계산할 때 쓴다.
EDF_STATIC_THRUST_N = (8.0, 12.0)


def authority(params_path: Path = PARAMS, throttle: float = 1.0) -> dict:
    p = yaml.safe_load(params_path.read_text(encoding="utf-8"))
    alpha_max = np.deg2rad(p["alpha_max_deg"])
    thrust = p["Kf"] * (throttle * p["omega_t_per_throttle"]) ** 2
    vane_force = vane_lift_gain(p) * thrust * alpha_max
    torque = 2.0 * vane_force * p["vane_arm_l"]      # 한 축당 베인 2장
    ang_acc = torque / p["Jxx"]
    reachable = 0.5 * ang_acc * EPISODE_S ** 2        # 계속 최대토크를 걸었을 때
    return {
        "Kf": float(p["Kf"]),
        "omega_t_per_throttle": float(p["omega_t_per_throttle"]),
        "throttle": throttle,
        "thrust_N": thrust,
        "torque_Nm": torque,
        "ang_acc": ang_acc,
        "reachable_deg": float(np.rad2deg(reachable)),
        "needed_deg": float(np.rad2deg(INIT_TILT_RAD)),
        "ratio": float(reachable / INIT_TILT_RAD),
    }


def warn_if_underpowered(params_path: Path = PARAMS, stream=sys.stdout) -> bool:
    """권한이 부족하면 경고를 찍고 True를 돌려준다. 학습 스크립트가 시작 전에 부른다."""
    a = authority(params_path)
    if a["ratio"] >= 2.0:
        return False
    # Kf 숫자를 글자로 박아 두지 않는다. params.yaml을 고치면 경고가 옛 값을 "현재"라고
    # 알리게 된다(#129). 범위도 지금 omega_t_per_throttle로 다시 계산한다.
    # print에 em dash처럼 cp949에 없는 문자를 쓰지 않는다. 한국어 Windows에서 출력을 파일로
    # 돌리면 UnicodeEncodeError로 멈춘다(#147, tasks.py _survive_console_encoding 참고).
    thrust_lo, thrust_hi = EDF_STATIC_THRUST_N
    kf_lo = thrust_lo / a["omega_t_per_throttle"] ** 2
    kf_hi = thrust_hi / a["omega_t_per_throttle"] ** 2
    print(
        "\n" + "!" * 78 + "\n"
        "제어권한 부족: 지금 물리 상수로는 이 과제를 어떤 제어기도 풀 수 없다.\n"
        f"  스로틀 100%에서 최대 추력 {a['thrust_N']:.3f} N, 베인토크 {a['torque_Nm']:.2e} Nm\n"
        f"  -> {EPISODE_S:.0f}초를 전부 써도 자세를 {a['reachable_deg']:.1f}도밖에 못 바꾼다\n"
        f"  그런데 초기 교란은 최대 {a['needed_deg']:.0f}도다 "
        f"(여유 배수 {a['ratio']:.2f}, 2.0 이상이어야 한다)\n\n"
        "  네 비교군이 다 같이 실패하므로 결과에 정보가 없다.\n"
        f"  읽은 파일: {params_path}\n"
        f"  읽은 값: Kf {a['Kf']:.2e}, omega_t_per_throttle {a['omega_t_per_throttle']:g}\n"
        f"  64mm급 EDF 정적추력 {thrust_lo:g}-{thrust_hi:g} N이면 Kf는 "
        f"{kf_lo:.2e}에서 {kf_hi:.2e} 사이다.\n"
        "  Kf가 이 범위 밖이면 실험 A(EDF 추력곡선)로 Kf를 실측값으로 채운 뒤 다시 돌릴 것.\n"
        "  Kf가 이 범위 안이면 원인은 Kf가 아니다. 베인 상수(CLalpha, vane_geometry,\n"
        "  A_duct, alpha_max_deg), vane_arm_l, Jxx를 확인할 것.\n"
        + "!" * 78,
        file=stream,
    )
    return True


def main() -> int:
    print(f"params: {PARAMS}\n")
    header = f"{'스로틀':>8}{'추력(N)':>12}{'토크(Nm)':>14}{'각가속(rad/s2)':>18}{'5초내 가동각(deg)':>20}"
    print(header)
    print("-" * len(header))
    for th in (0.25, 0.5, 0.75, 1.0):
        a = authority(throttle=th)
        print(f"{th:>8.0%}{a['thrust_N']:>12.4f}{a['torque_Nm']:>14.2e}"
              f"{a['ang_acc']:>18.4f}{a['reachable_deg']:>20.2f}")
    print(f"\n초기 교란 최대 {np.rad2deg(INIT_TILT_RAD):.0f}도 · 에피소드 {EPISODE_S:.0f}초")
    warn_if_underpowered()
    return 0


if __name__ == "__main__":
    sys.exit(main())
