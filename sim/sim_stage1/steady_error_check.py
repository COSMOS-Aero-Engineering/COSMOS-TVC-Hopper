"""#230 모델의 정상오차 0.64°가 어디에서 나오는지 seed별로 본다(#357). 결과와 판정은 ppo-ablation.md
"정상오차 0.64°의 출처" 절.

실행(저장소 루트에서, 7조건 x seed 200개. 서버에서 약 6분):
    python ship.py capped 8G -- uv run --frozen --project . python sim/sim_stage1/steady_error_check.py
    ... steady_error_check.py --seeds 20      빠르게 볼 때

정상오차는 sim/connectome/evaluate.py episode_metrics()와 같다: 마지막 20 % 구간의 평균 기울기 hypot(phi, theta).
평가 seed 0-(N-1), 도메인 랜덤화 켬, 정책은 결정적 행동이다(compare_metrics.py와 같다).

환경 코드와 params.yaml은 바꾸지 않는다. 비교 조건은 reset() 뒤 이 스크립트가 env 속성을 바꿔서 만든다.
  무게중심 0   reset() 뒤 env.cg_offset_x = env.cg_offset_y = 0. 나머지 랜덤화 값은 그대로다
  랜덤화 끔    env.dr = {"enabled": False}. 모든 상수가 명목값이고 무게중심 오프셋이 0이다
초기 자세(학습 분포, 기울기 10°·40° 고정)는 compare_metrics.py와 같은 reset 옵션이다.

출력의 "롤 기울기/cg_y", "피치 기울기/cg_x" 열: 마지막 구간 평균 롤(°)을 cg_offset_y(mm)에, 평균 피치(°)를 cg_offset_x(mm)에
직선으로 맞춘 기울기다. cg_offset은 팔 l의 명목값 비율(0.104 / l)로 고쳐서 쓴다. 정지 상태의 토크 균형은
베인 토크 (a1 + a3)·CL·Ft·alpha_max·l = -cg_offset_y·Ft이므로 필요한 베인 명령이 cg_offset / l에 비례한다.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from hopper_aviary import HopperAttitudeEnv  # noqa: E402
from pd_gate import pd  # noqa: E402

MODEL = HERE / "hopper_attitude_ppo_230.zip"
TAIL = 0.8   # evaluate.py episode_metrics()와 같은 마지막 20 % 구간


def run(act, n_seeds, options=None, cg_zero=False, dr_off=False):
    """seed마다 마지막 20 % 구간의 값을 모은다. 돌려주는 값: {이름: seed별 배열}."""
    env = HopperAttitudeEnv()
    if dr_off:
        env.dr = {"enabled": False}
    keys = ("steady", "phi", "theta", "tilt_std", "a_max", "sat", "cost_att", "cost_act",
            "cg_x", "cg_y", "l", "crashed")
    out = {k: [] for k in keys}
    for seed in range(n_seeds):
        obs, _ = env.reset(seed=seed, options=options)
        if cg_zero:
            env.cg_offset_x = env.cg_offset_y = 0.0
        xs, acts = [obs], []
        while True:
            a = np.clip(np.asarray(act(obs), dtype=float), -1.0, 1.0)
            obs, _, terminated, truncated, _ = env.step(a)
            xs.append(obs)
            acts.append(a)
            if terminated or truncated:
                break
        x, a = np.asarray(xs, dtype=float), np.asarray(acts, dtype=float)
        t0 = max(1, int(len(x) * TAIL))
        tail, a_tail = x[t0:], a[t0 - 1:]   # x[k]는 행동 a[k-1] 뒤의 관측이다
        tilt = np.hypot(tail[:, 0], tail[:, 1])
        out["steady"].append(np.rad2deg(tilt.mean()))
        out["phi"].append(np.rad2deg(tail[:, 0].mean()))
        out["theta"].append(np.rad2deg(tail[:, 1].mean()))
        out["tilt_std"].append(np.rad2deg(tilt.std()))
        out["a_max"].append(np.abs(a_tail[:, :4]).max())
        out["sat"].append(np.mean(np.abs(a_tail[:, :4]) >= 0.999))
        # 보상 항(hopper_aviary.py step()과 같은 식)의 스텝 평균
        out["cost_att"].append(np.mean(tail[:, 0] ** 2 + tail[:, 1] ** 2 + 0.1 * tail[:, 2] ** 2))
        out["cost_act"].append(np.mean(0.001 * np.sum(a_tail ** 2, axis=1)))
        out["cg_x"].append(env.cg_offset_x * 1e3)
        out["cg_y"].append(env.cg_offset_y * 1e3)
        out["l"].append(env.l)
        out["crashed"].append(terminated)
    return {k: np.asarray(v, dtype=float) for k, v in out.items()}


def corr(a, b):
    """상관계수 문자열. 한쪽이 상수(무게중심 0)이면 '-'."""
    return f"{np.corrcoef(a, b)[0, 1]:.3f}" if np.std(a) > 0 and np.std(b) > 0 else "-"


def slope(cg_mm, l, angle_deg):
    """angle_deg = k · cg_mm·(l0 / l) + c 의 k(°/mm)와 상관계수 r 문자열. 무게중심이 모두 0이면 '-'."""
    x = cg_mm * (0.104 / l)
    if not np.std(x) > 0:
        return "-"
    return f"{np.polyfit(x, angle_deg, 1)[0]:.3f} °/mm (r {np.corrcoef(x, angle_deg)[0, 1]:.4f})"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=200, help="평가 seed 수(0부터)")
    args = ap.parse_args()

    from policy_io import load_policy
    ppo = load_policy(MODEL)
    runs = {
        "PPO 학습 분포": run(ppo, args.seeds),
        "PPO 기울기 10°": run(ppo, args.seeds, {"initial_tilt_deg": 10.0}),
        "PPO 기울기 40°": run(ppo, args.seeds, {"initial_tilt_deg": 40.0}),
        "PPO 무게중심 0": run(ppo, args.seeds, cg_zero=True),
        "PPO 랜덤화 끔": run(ppo, args.seeds, dr_off=True),
        "PD 학습 분포": run(pd, args.seeds),
        "PD 무게중심 0": run(pd, args.seeds, cg_zero=True),
    }

    print(f"평가 seed 0-{args.seeds - 1}, 정상오차 = 마지막 20 % 구간 평균 기울기, 모델 {MODEL.name}\n")
    print("| 조건 | 넘어짐 | 정상오차 평균 | 최소-최대 | 롤 크기 평균 | 피치 크기 평균 | 상관(cg 크기/l) "
          "| 롤 기울기/cg_y | 피치 기울기/cg_x | 구간 표준편차 최대 | 베인 명령 크기 최대 | 포화 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, r in runs.items():
        eq = np.hypot(r["cg_x"], r["cg_y"]) / r["l"]
        print(f"| {name} | {int(r['crashed'].sum())}/{len(r['steady'])} | {r['steady'].mean():.3f}° | "
              f"{r['steady'].min():.3f}-{r['steady'].max():.3f}° | {np.abs(r['phi']).mean():.3f}° | "
              f"{np.abs(r['theta']).mean():.3f}° | {corr(r['steady'], eq)} | "
              f"{slope(r['cg_y'], r['l'], r['phi'])} | {slope(r['cg_x'], r['l'], r['theta'])} | "
              f"{r['tilt_std'].max():.4f}° | {r['a_max'].max():.3f} | {r['sat'].mean() * 100:.1f} % |")

    base = runs["PPO 학습 분포"]["steady"]
    for name in ("PPO 기울기 10°", "PPO 기울기 40°"):
        print(f"\nseed별 정상오차 차이 최대(PPO 학습 분포 vs {name}): {np.abs(runs[name]['steady'] - base).max():.4f}°")
    r = runs["PPO 학습 분포"]
    print(f"\nPPO 학습 분포 마지막 구간 보상 항(스텝 평균): 자세 {r['cost_att'].mean():.2e}, "
          f"행동 {r['cost_act'].mean():.2e}")
    r = runs["PD 학습 분포"]
    print(f"PD 학습 분포 마지막 구간 보상 항(스텝 평균): 자세 {r['cost_att'].mean():.2e}, "
          f"행동 {r['cost_act'].mean():.2e}")

    zero = np.zeros(7, dtype=np.float32)
    zero[6] = 1.0   # 수평, 정지, 스로틀 1.0
    print(f"\nPPO 행동(관측이 수평·정지일 때) a1-a4: {', '.join(f'{v:.3f}' for v in ppo(zero)[:4])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
