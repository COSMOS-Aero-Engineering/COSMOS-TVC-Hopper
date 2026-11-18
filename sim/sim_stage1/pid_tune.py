"""compare_metrics.py의 PID 게인(PID_GAINS)을 고른 격자 탐색(#349).

실행(저장소 루트에서, 격자 294점, 프로세스 하나에 약 35분):
    python ship.py capped 8G -- uv run --frozen --project . python sim/sim_stage1/pid_tune.py --jobs 3

고르는 방법:
  튜닝 seed  TUNE_SEEDS(1000-1199). 평가 seed(pd_gate.EVAL_SEEDS, 0-199)와 학습 seed(ppo_ablation.TRAIN_SEED
             10000부터)와 겹치지 않는다. 평가 seed로 게인을 고르면 평가 seed에 맞춘 값이 되기 때문이다.
  조건       학습 분포(세 축 각각 U(-0.3, 0.3) rad), 도메인 랜덤화 켬. PPO가 학습한 조건과 같다.
  기준       평균 리턴(환경 보상의 에피소드 합)이 가장 큰 격자점. PPO가 최대화하는 값과 같은 목적이다.
             복원시간, 오버슈트, 정상오차는 고를 때 쓰지 않는다. 평가 지표로만 쓴다.
  격자       KP x KD x KI. ki = 0인 점은 튜닝한 PD다.

출력의 마지막 줄은 고른 점이 compare_metrics.PID_GAINS와 같은지 알린다. 다르면 exit 1이다.
"""
import argparse
import itertools
import sys
from multiprocessing import Pool

from compare_metrics import PID_GAINS, evaluate, make_pid

TUNE_SEEDS = range(1000, 1200)
KP = [16.0, 20.0, 24.0, 28.0, 32.0, 40.0, 48.0]
KD = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 16.0]
KI = [0.0, 2.5, 5.0, 7.5, 10.0, 20.0]


def score(gains):
    return gains, evaluate(make_pid(gains), seeds=TUNE_SEEDS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", type=int, default=1, help="동시에 돌릴 프로세스 수")
    args = ap.parse_args()
    grid = [{"kp": kp, "kd": kd, "ki": ki} for kp, kd, ki in itertools.product(KP, KD, KI)]
    with Pool(args.jobs) as pool:
        results = pool.map(score, grid)
    results.sort(key=lambda r: -r[1]["mean_reward"])

    print(f"튜닝 seed {TUNE_SEEDS.start}-{TUNE_SEEDS.stop - 1}, 학습 분포, 도메인 랜덤화 켬, 격자 {len(grid)}점\n")
    print("| 순위 | kp | kd | ki | 평균 리턴 | 넘어짐 | 복원시간 평균(s) | 미복원 | 오버슈트 | 정상오차 |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    best_pd = next(i for i, (g, _) in enumerate(results) if g["ki"] == 0)
    for i, (g, m) in enumerate(results):
        if i < 10 or i == best_pd:
            print(f"| {i + 1} | {g['kp']:g} | {g['kd']:g} | {g['ki']:g} | {m['mean_reward']:.3f} | "
                  f"{m['crash_rate'] * 100:.1f} % | {m['settle_s']:.2f} | {m['settle_censored']}/{m['episodes']} | "
                  f"{m['overshoot_cross'] * 100:.1f} % | {m['steady_err_deg']:.2f}° |")
    best = results[0][0]
    same = best == PID_GAINS
    print(f"\n고른 점: kp={best['kp']:g}, kd={best['kd']:g}, ki={best['ki']:g}. "
          f"compare_metrics.PID_GAINS와 {'같다' if same else '다르다'}.")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
