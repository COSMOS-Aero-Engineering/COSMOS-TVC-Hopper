"""4개 비교군을 같은 조건에서 돌리고 표로 뽑는다 — 이 브랜치의 최종 산출물.

    python run_comparison.py --timesteps 60000 --seeds 3
    python run_comparison.py --timesteps 200000 --seeds 5 --out results/run1.json

비교군
------
    A. PD          학습 없음. 게인은 격자탐색으로 최적을 고른다 (baseline_pd.py)
    B. MLP         SB3 기본 MLP(64,64) + PPO — "아무 구조나 쓴 신경망"
    C. connectome  커넥톰 제약 RNN + PPO — 배선이 고정된 신경망
    D. shuffled    C와 크기·차수분포·흥분억제비가 같고 연결 상대만 무작위 (shuffle.py)

D가 이 실험의 핵심이다. C > D 여야 "배선 구조가 기여했다"고 말할 수 있고, C ~ D 면
"그냥 희소 RNN이 잘 된 것"이다. 둘 다 정직한 결과이고, D가 없으면 어느 쪽도 말할 수 없다.

지금 돌려도 되는가
------------------
된다. 다만 sim/sim_stage1/params.yaml 의 물리 상수가 아직 전부 PLACEHOLDER라서 **여기서
나오는 절대 수치는 의미가 없다.** 지금 확인할 수 있는 건 "파이프라인이 돌아가는가"와
"네 비교군이 같은 자로 재어지는가"까지다. 실험 A(EDF 추력곡선)로 params.yaml을 채운 뒤
같은 명령을 다시 돌리는 게 본 실험이다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "sim" / "sim_stage1"))

from authority import warn_if_underpowered  # noqa: E402
from baseline_pd import PDController, tune  # noqa: E402
from evaluate import format_table, run_episodes  # noqa: E402
from hopper_aviary import HopperAttitudeEnv  # noqa: E402
from policy import make_policy_kwargs  # noqa: E402
from stable_baselines3 import PPO  # noqa: E402
from stable_baselines3.common.callbacks import BaseCallback  # noqa: E402


class EvalCurve(BaseCallback):
    """학습 중간중간 평가해서 학습곡선을 남긴다 — 샘플 효율을 비교하려면 이게 있어야 한다.

    FlyGM 논문(arXiv 2602.17997)이 커넥톰 구조의 이점으로 내세운 게 최종 성능이 아니라
    '샘플 효율'이다. 최종 점수만 찍으면 그 주장을 확인할 수도 반박할 수도 없다.
    """

    EPISODES = 10  # 학습 중에 여러 번 부르므로 최종 평가(30)보다 적게 쓴다

    def __init__(self, every: int, episodes: int | None = None):
        super().__init__()
        self.every = every
        self.episodes = self.EPISODES if episodes is None else episodes
        self.curve: list[tuple[int, float]] = []
        self._next = every

    def _on_step(self) -> bool:
        if self.num_timesteps >= self._next:
            self._next += self.every
            m = run_episodes(self.model.policy, HopperAttitudeEnv(), episodes=self.episodes)
            self.curve.append((int(self.num_timesteps), m["mean_reward"]))
        return True


def train_arm(name: str, policy_kwargs, timesteps: int, seed: int, eval_every: int):
    env = HopperAttitudeEnv()
    model = PPO("MlpPolicy", env, seed=seed, verbose=0, policy_kwargs=policy_kwargs)
    if seed == 0 and hasattr(model.policy.features_extractor, "describe"):
        print(f"      {model.policy.features_extractor.describe()}")
    cb = EvalCurve(every=eval_every)
    t0 = time.time()
    model.learn(total_timesteps=timesteps, callback=cb)
    metrics = run_episodes(model.policy, HopperAttitudeEnv(), episodes=30)
    metrics["train_seconds"] = round(time.time() - t0, 1)
    metrics["curve"] = cb.curve
    return model, metrics


def average(runs: list[dict]) -> dict:
    """시드별 결과를 평균낸다. 곡선은 시드 0의 것만 대표로 남긴다(길이가 같다)."""
    keys = [k for k, v in runs[0].items() if isinstance(v, (int, float))]
    out = {k: float(np.mean([r[k] for r in runs])) for k in keys}
    out["seeds"] = len(runs)
    out["mean_reward_std"] = float(np.std([r["mean_reward"] for r in runs]))
    out["curve"] = runs[0]["curve"]
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="PD / MLP / 커넥톰 / 셔플 4군 비교")
    p.add_argument("--timesteps", type=int, default=60_000)
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--graph", default="graphs/synthetic.npz")
    p.add_argument("--shuffled", default="graphs/synthetic_shuffled.npz")
    p.add_argument("--n-settle", type=int, default=20)
    p.add_argument("--eval-every", type=int, default=0, help="0이면 학습량의 1/10")
    p.add_argument("--skip-pd", action="store_true")
    p.add_argument("--out", default=None, help="결과 JSON 경로")
    a = p.parse_args()

    eval_every = a.eval_every or max(a.timesteps // 10, 1)
    # 몇 시간짜리 학습을 돌리기 전에 '이 과제가 풀 수 있는 것인가'부터 알려준다.
    underpowered = warn_if_underpowered()
    results: dict[str, dict] = {}

    if not a.skip_pd:
        print("[A] PD baseline — 게인 격자탐색")
        _, gains, m = tune(HopperAttitudeEnv, run_episodes, episodes=20)
        m = run_episodes(PDController(**gains), HopperAttitudeEnv(), episodes=30)
        m.update({"seeds": 1, "mean_reward_std": 0.0, "curve": [], "gains": gains})
        results["A. PD (튜닝)"] = m

    arms = [
        ("B. MLP(64,64)", None),
        ("C. 커넥톰", make_policy_kwargs(a.graph, n_settle=a.n_settle)),
        ("D. 셔플 대조군", make_policy_kwargs(a.shuffled, n_settle=a.n_settle)),
    ]
    for name, pk in arms:
        print(f"\n[{name}] {a.seeds}개 시드 x {a.timesteps:,} 스텝")
        runs = []
        for seed in range(a.seeds):
            torch.manual_seed(seed)
            _, m = train_arm(name, pk, a.timesteps, seed, eval_every)
            print(f"      시드 {seed}: 보상 {m['mean_reward']:>8.1f} · "
                  f"복원 {m['settle_s']:.2f}s · 추락 {m['crash_rate']:.0%} "
                  f"({m['train_seconds']}초)")
            runs.append(m)
        results[name] = average(runs)

    print("\n" + "=" * 82)
    print(format_table(results))
    print("=" * 82)
    # 곡선은 학습 중에 찍느라 10 에피소드만 쓴다. 위 표는 30 에피소드다 —
    # 에피소드 집합이 달라서 두 숫자를 직접 비교하면 안 된다(곡선은 같은 비교군 안에서
    # 시간에 따른 변화를 보는 용도). 헷갈리기 쉬워서 개수를 같이 찍는다.
    print(f"\n[학습곡선 — 시드 0, {EvalCurve.EPISODES} 에피소드 기준 "
          f"(위 표는 30 에피소드라 값이 직접 비교되지 않는다)]")
    for name, m in results.items():
        if m["curve"]:
            pts = " ".join(f"{s // 1000}k:{r:.0f}" for s, r in m["curve"])
            print(f"  {name:<18} {pts}")

    print("\n※ params.yaml 이 아직 PLACEHOLDER다 — 위 절대 수치는 파이프라인 확인용이고,")
    print("  실험 A로 물리 상수를 채운 뒤 같은 명령을 다시 돌린 결과가 본 실험이다.")
    if underpowered:
        print("  특히 제어권한이 부족한 상태라 네 비교군의 우열은 아직 읽으면 안 된다.")

    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n저장: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
