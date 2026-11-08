"""PD와 PPO를 복원시간, 오버슈트, 정상오차, 넘어짐 비율로 비교한 표를 초기 자세 두 조건으로 낸다(#266, #276).

실행(저장소 루트에서):
    python ship.py capped 8G -- uv run --frozen --project . python sim/sim_stage1/compare_metrics.py
    ... compare_metrics.py --model 다른_모델.zip      다른 PPO 모델로 같은 표를 낸다(예: #230 뒤 모델)
    ... compare_metrics.py --tilt-deg 10 20 30 40    기울기를 x°로 고정한 조건만 x마다 낸다(#312)

평가 조건은 pd_gate.py와 같다: 평가 seed 0-199, 도메인 랜덤화 켬, PD(kp=8, kd=2), PPO는 결정적 행동.
에피소드 k는 두 정책 모두 env.reset(seed=k)로 시작하므로 초기 자세와 랜덤화된 기체가 같다.
지표 계산은 새로 만들지 않고 커넥톰 트랙의 sim/connectome/evaluate.py run_episodes()를 쓴다.

초기 자세 조건(CONDITIONS). 두 조건 모두 같은 seed 0-199를 쓰고 seed k의 랜덤화된 기체는 두 조건에서 같다.
  학습 분포   세 축 각각 U(-0.3, 0.3) rad(약 ±17°). 학습 환경 그대로이고 pd_gate.py와 같다.
  TC-3        마스터 설계 §11 TC-3의 ±10° 초기 오프셋. reset(options={"initial_tilt_deg": 10.0})으로
              기울기 hypot(phi, theta)를 10°로 고정한다. 방향은 seed마다 균등하게 뽑고 요는 0이다.
              학습 분포는 바꾸지 않는다. 이 옵션은 평가에서만 쓴다(hopper_aviary.py 머리 설명).

--tilt-deg x를 주면 위 두 조건 대신 기울기 x° 고정 조건(TC-3과 같은 옵션)을 x마다 낸다(#312).
학습 분포 밖 초기 자세에서 두 정책이 어떻게 움직이는지 본다. 표마다 롤·피치·요 중 한 축 이상이
학습 초기 범위(각 축 ±INITIAL_ATTITUDE_RAD = 0.3 rad, 약 ±17.2°) 밖인 에피소드 수를 같이 낸다.
x가 17.2° 이하이면 0이고, 17.2° · √2 = 24.3°보다 크면 모든 에피소드다. 그 사이(예: 20°)는 방향에 따라 다르다.

지표 정의와 근거 (자세한 계산은 evaluate.py episode_metrics()):
  기울기       hypot(phi, theta). 목표값은 0(수평)이고 초기 기울기에서 0으로 돌아오는 응답을 본다.
  복원시간     기울기가 2° 아래로 내려가서 에피소드 끝까지 유지된 첫 시점(s). 끝까지 못 내려온
               에피소드는 에피소드 길이(5 s)로 평균에 넣고 "미복원" 개수로 따로 센다.
               교재와 MATLAB stepinfo의 정착시간은 "응답 변화량 |yfinal - yinit|의 2 %" 같은 상대 띠를
               쓴다. 여기서는 절대 띠 2°를 쓴다. 초기 기울기가 10°이면 2°는 변화량의 20 %다.
               TC-3 실측과 같은 기준을 쓰려고 상대 띠 복원시간은 같이 내지 않는다.
               근거는 docs/design/00-hopper-master-design.md §11.1(#274).
  오버슈트     0 넘음. 수평(0°)을 지나 반대쪽으로 기운 최대 각도 / 초기 기울기(evaluate.py의 overshoot_cross).
               MATLAB stepinfo의 정의(ynorm = (y - yinit)/(yfinal - yinit), 오버슈트 = max(0, max(ynorm - 1)))에
               초기 기울기 방향으로 투영한 기울기와 yfinal = 0을 넣은 값이다. 복원하지 않고 멈춘 에피소드도
               0이므로 미복원 수, 정상오차와 함께 읽는다.
               예전 표의 "초기값 초과"((최대 기울기 - 초기 기울기) / 초기 기울기)는 표에서 뺐다.
               근거는 docs/design/00-hopper-master-design.md §11.2(#273).
  정상오차     마지막 20 % 구간(1 s)의 평균 기울기(°). 교재 정의는 e(t)의 t -> 무한대 극한이다.
               에피소드가 5 s로 끝나므로 마지막 구간 평균으로 대신한다.
  넘어짐       롤이나 피치가 60°를 넘어 에피소드가 끝난 비율(hopper_aviary.py의 terminated).

넘어진 에피소드도 복원시간, 오버슈트, 정상오차 평균에 들어간다(evaluate.py와 같다).

TC-3 조건에서는 초기 기울기가 모든 에피소드에서 10°다. 그래서 복원 기준 2°는 늘 변화량의 20 %이고,
오버슈트를 나누는 초기 기울기도 에피소드마다 같다. 학습 분포 조건에서는 초기 기울기가 에피소드마다 다르다.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "connectome"))

from evaluate import SETTLE_DEG, run_episodes  # noqa: E402
from hopper_aviary import INITIAL_ATTITUDE_RAD, HopperAttitudeEnv  # noqa: E402
from pd_gate import EVAL_SEEDS, pd  # noqa: E402

DEFAULT_MODEL = HERE / "hopper_attitude_ppo.zip"
TC3_TILT_DEG = 10.0   # 마스터 설계 §11 TC-3의 초기 오프셋(°)

# 초기 자세 조건 이름 -> env.reset(options=...). None은 학습 분포다.
CONDITIONS = {
    "학습 분포(세 축 각각 U(-0.3, 0.3) rad, 약 ±17°. pd_gate.py와 같다)": None,
    f"TC-3(기울기 {TC3_TILT_DEG:g}° 고정, 방향은 seed마다 균등, 요 0)": {"initial_tilt_deg": TC3_TILT_DEG},
}


def tilt_conditions(tilts_deg):
    """--tilt-deg 값마다 기울기 고정 조건을 만든다(#312). TC-3과 같은 reset 옵션이다."""
    return {f"기울기 {x:g}° 고정, 방향은 seed마다 균등, 요 0": {"initial_tilt_deg": x} for x in tilts_deg}


def outside_training_init(reset_options):
    """평가 seed마다 reset 직후 롤·피치·요 중 한 축 이상이 학습 초기 범위 밖인 에피소드 수(#312).

    잘못된 옵션이면 env.reset()이 ValueError를 낸다. main()은 평가 전에 모든 조건에서 이 함수를 불러
    오래 걸리는 평가를 시작하기 전에 멈춘다.
    """
    env = HopperAttitudeEnv()
    count = 0
    for seed in EVAL_SEEDS:
        obs, _ = env.reset(seed=seed, options=reset_options)
        count += bool(np.any(np.abs(obs[:3]) > INITIAL_ATTITUDE_RAD))
    return count


class Predictor:
    """관측 -> 행동 함수를 run_episodes()가 부르는 predict(obs, deterministic) 형식으로 감싼다."""

    def __init__(self, act):
        self.act = act

    def predict(self, obs, deterministic=True):
        return self.act(obs), None


def evaluate(act, reset_options=None):
    env = HopperAttitudeEnv()
    if not env.dr.get("enabled", False):
        raise ValueError("params.yaml의 domain_rand.enabled가 false다. 이 표는 랜덤화를 켠 상태에서만 낸다.")
    seeds = list(EVAL_SEEDS)
    if seeds != list(range(seeds[0], seeds[0] + len(seeds))):
        raise ValueError("EVAL_SEEDS가 연속한 범위가 아니다. run_episodes()는 seed_base + k만 쓴다.")
    return run_episodes(Predictor(act), env, episodes=len(seeds), seed_base=seeds[0],
                        reset_options=reset_options)


def row(name, m):
    return (f"| {name} | {m['crash_rate'] * 100:.1f} % | {m['settle_s']:.2f} | "
            f"{m['settle_censored']}/{m['episodes']} | {m['overshoot_cross'] * 100:.1f} % | "
            f"{m['steady_err_deg']:.2f}° | {m['mean_reward']:.2f} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=str(DEFAULT_MODEL), help="비교할 SB3 PPO 모델(.zip)")
    ap.add_argument("--tilt-deg", type=float, nargs="+", metavar="X",
                    help="학습 분포와 TC-3 대신 기울기 X°로 고정한 조건만 낸다(여러 개 가능, 0 < X < 60)")
    args = ap.parse_args()
    conditions = tilt_conditions(args.tilt_deg) if args.tilt_deg else CONDITIONS
    outside = {condition: outside_training_init(options) for condition, options in conditions.items()}

    from policy_io import load_policy   # 모델 옆 <이름>.json·<이름>.vecnormalize.pkl도 읽는다(#230)

    policies = {
        "PD (kp=8, kd=2)": pd,
        f"PPO ({Path(args.model).name})": load_policy(args.model),
    }

    print(f"평가 seed {EVAL_SEEDS.start}-{EVAL_SEEDS.stop - 1}, 도메인 랜덤화 켬, 복원 기준 {SETTLE_DEG}°")
    for condition, options in conditions.items():
        print(f"\n초기 자세: {condition}")
        print(f"한 축 이상이 학습 초기 범위(각 축 ±{INITIAL_ATTITUDE_RAD} rad) 밖: "
              f"{outside[condition]}/{len(EVAL_SEEDS)}\n")
        print("| 정책 | 넘어짐 | 복원시간 평균(s) | 미복원 | 오버슈트 | 정상오차 | 평균 리턴 |")
        print("|---|---:|---:|---:|---:|---:|---:|")
        for name, act in policies.items():
            print(row(name, evaluate(act, reset_options=options)))
    print("\n* 미복원: 끝까지 복원 기준 아래로 못 내려온 에피소드 수. 복원시간 평균에는 에피소드 길이(5 s)로 들어간다.")
    print("* 오버슈트: 수평(0°)을 지나 반대쪽으로 기운 최대 각도 / 초기 기울기(MATLAB stepinfo 정의, 최종값 0. "
          "마스터 설계 §11.2). 복원하지 않고 멈춘 에피소드도 0 %다.")
    print("* 정상오차: 마지막 20 % 구간의 평균 기울기. 넘어진 에피소드도 평균에 들어간다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
