"""PD와 PPO를 복원시간, 오버슈트, 정상오차, 넘어짐 비율로 비교한 표를 낸다(#266).

실행(저장소 루트에서):
    python ship.py capped 8G -- uv run --frozen --project . python sim/sim_stage1/compare_metrics.py
    ... compare_metrics.py --model 다른_모델.zip      다른 PPO 모델로 같은 표를 낸다(예: #230 뒤 모델)

평가 조건은 pd_gate.py와 같다: 평가 seed 0-199, 도메인 랜덤화 켬, PD(kp=8, kd=2), PPO는 결정적 행동.
에피소드 k는 두 정책 모두 env.reset(seed=k)로 시작하므로 초기 자세와 랜덤화된 기체가 같다.
지표 계산은 새로 만들지 않고 커넥톰 트랙의 sim/connectome/evaluate.py run_episodes()를 쓴다.

지표 정의와 근거 (자세한 계산은 evaluate.py episode_metrics()):
  기울기       hypot(phi, theta). 목표값은 0(수평)이고 초기 기울기에서 0으로 돌아오는 응답을 본다.
  복원시간     기울기가 2° 아래로 내려가서 에피소드 끝까지 유지된 첫 시점(s). 끝까지 못 내려온
               에피소드는 에피소드 길이(5 s)로 평균에 넣고 "미복원" 개수로 따로 센다.
               교재와 MATLAB stepinfo의 정착시간은 "응답 변화량 |yfinal - yinit|의 2 %" 같은 상대 띠를
               쓴다. 여기서는 절대 띠 2°를 쓴다. 초기 기울기가 10°이면 2°는 변화량의 20 %다.
  오버슈트     두 값을 같이 낸다.
               - 0 넘음: stepinfo의 정의(ynorm = (y - yinit)/(yfinal - yinit), 오버슈트 = max(0, max(ynorm - 1)))에
                 초기 기울기 방향으로 투영한 기울기를 넣은 값. 0을 지나 반대쪽으로 넘어간 최대 크기 / 초기 기울기.
                 발표 표의 "오버슈트"는 이 값이 교재 정의와 같다.
               - 초기값 초과: evaluate.py가 원래 내던 값. (최대 기울기 - 초기 기울기) / 초기 기울기.
                 처음보다 더 기울어진 정도이고 교재의 오버슈트와 다르다.
  정상오차     마지막 20 % 구간(1 s)의 평균 기울기(°). 교재 정의는 e(t)의 t -> 무한대 극한이다.
               에피소드가 5 s로 끝나므로 마지막 구간 평균으로 대신한다.
  넘어짐       롤이나 피치가 60°를 넘어 에피소드가 끝난 비율(hopper_aviary.py의 terminated).

넘어진 에피소드도 복원시간, 오버슈트, 정상오차 평균에 들어간다(evaluate.py와 같다).

TC-3과 다른 점: TC-3은 ±10° 초기 오프셋이다. 이 표는 학습 환경의 초기 자세(세 축 각각 U(-0.3, 0.3) rad,
약 ±17°)를 그대로 쓴다. pd_gate.py와 같은 seed와 같은 초기 조건으로 재기 위해서다.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "connectome"))

from evaluate import SETTLE_DEG, run_episodes  # noqa: E402
from hopper_aviary import HopperAttitudeEnv  # noqa: E402
from pd_gate import EVAL_SEEDS, model_policy, pd  # noqa: E402

DEFAULT_MODEL = HERE / "hopper_attitude_ppo.zip"


class Predictor:
    """관측 -> 행동 함수를 run_episodes()가 부르는 predict(obs, deterministic) 형식으로 감싼다."""

    def __init__(self, act):
        self.act = act

    def predict(self, obs, deterministic=True):
        return self.act(obs), None


def evaluate(act):
    env = HopperAttitudeEnv()
    if not env.dr.get("enabled", False):
        raise ValueError("params.yaml의 domain_rand.enabled가 false다. 이 표는 랜덤화를 켠 상태에서만 낸다.")
    seeds = list(EVAL_SEEDS)
    if seeds != list(range(seeds[0], seeds[0] + len(seeds))):
        raise ValueError("EVAL_SEEDS가 연속한 범위가 아니다. run_episodes()는 seed_base + k만 쓴다.")
    return run_episodes(Predictor(act), env, episodes=len(seeds), seed_base=seeds[0])


def row(name, m):
    return (f"| {name} | {m['crash_rate'] * 100:.1f} % | {m['settle_s']:.2f} | "
            f"{m['settle_censored']}/{m['episodes']} | {m['overshoot_cross'] * 100:.1f} % | "
            f"{m['overshoot'] * 100:.1f} % | {m['steady_err_deg']:.2f}° | {m['mean_reward']:.2f} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=str(DEFAULT_MODEL), help="비교할 SB3 PPO 모델(.zip)")
    args = ap.parse_args()

    from stable_baselines3 import PPO
    model = PPO.load(args.model, device="cpu")

    results = {
        "PD (kp=8, kd=2)": evaluate(pd),
        f"PPO ({Path(args.model).name})": evaluate(model_policy(model)),
    }

    print(f"평가 seed {EVAL_SEEDS.start}-{EVAL_SEEDS.stop - 1}, 도메인 랜덤화 켬, 복원 기준 {SETTLE_DEG}°\n")
    print("| 정책 | 넘어짐 | 복원시간 평균(s) | 미복원 | 오버슈트(0 넘음) | 초기값 초과 | 정상오차 | 평균 리턴 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, m in results.items():
        print(row(name, m))
    print("\n* 미복원: 끝까지 복원 기준 아래로 못 내려온 에피소드 수. 복원시간 평균에는 에피소드 길이(5 s)로 들어간다.")
    print("* 오버슈트(0 넘음): 0을 지나 반대쪽으로 넘어간 최대 크기 / 초기 기울기(MATLAB stepinfo 정의).")
    print("* 초기값 초과: (최대 기울기 - 초기 기울기) / 초기 기울기(evaluate.py의 overshoot).")
    print("* 정상오차: 마지막 20 % 구간의 평균 기울기. 넘어진 에피소드도 평균에 들어간다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
