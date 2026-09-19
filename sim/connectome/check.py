"""커넥톰 트랙 자체 점검 — CI가 매 PR마다 돌리는 것.

    python check.py

여기서 잡으려는 사고:
    1. 그래프를 못 만들거나 정합성이 깨진 채로 저장된다
    2. 셔플이 차수를 보존하지 못한다 (= 대조군 자격 상실)
    3. 정책망 출력이 발산하거나 0으로 죽는다 (실제로 한 번 겪었다 — 1e-7 사건)
    4. SB3에 꽂았을 때 구조가 의도와 다르다 (pi 쪽에 MLP가 끼어드는 등)
    5. 기울기가 커넥톰 가중치까지 안 흐른다

FlyWire 실측 경로는 여기서 안 돈다 — 수백 MB를 받아야 해서 CI에 올릴 수 없다. 대신
합성 CX 그래프로 같은 코드 경로를 전부 지나간다. 그래프를 바꿔 끼우는 것 말고는
FlyWire 경로도 똑같은 코드를 쓴다.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "sim" / "sim_stage1"))

from authority import authority  # noqa: E402
from build_subgraph import build_synthetic  # noqa: E402
from evaluate import run_episodes  # noqa: E402
from graph import ConnectomeGraph  # noqa: E402
from hopper_aviary import HopperAttitudeEnv  # noqa: E402
from policy import ConnectomeExtractor, make_policy_kwargs  # noqa: E402
from shuffle import degree_preserving_shuffle  # noqa: E402

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "OK  " if condition else "실패"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        FAILURES.append(label)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="cosmos-connectome-"))
    env = HopperAttitudeEnv()

    print("\n1) 그래프 생성과 저장/적재")
    g = build_synthetic()
    path = g.save(tmp / "synthetic.npz")
    g2 = ConnectomeGraph.load(path)
    check("저장 후 다시 읽어도 같다", g2.n_nodes == g.n_nodes and g2.n_edges == g.n_edges,
          g.summary())
    check("스펙트럼 반경이 1 미만", g.spectral_radius() < 1.0,
          f"rho={g.spectral_radius():.3f}")
    check("링 어트랙터 구성요소가 다 있다",
          all((g.node_type == t).any() for t in ("EPG", "Delta7", "PEN_L", "PEN_R", "DN")))

    print("\n2) 셔플 대조군")
    s = degree_preserving_shuffle(g, seed=0)
    s.normalize_weights()
    in_ok = (np.bincount(s.edge_index[1], minlength=g.n_nodes)
             == np.bincount(g.edge_index[1], minlength=g.n_nodes)).all()
    out_ok = (np.bincount(s.edge_index[0], minlength=g.n_nodes)
              == np.bincount(g.edge_index[0], minlength=g.n_nodes)).all()
    check("입력차수 보존", bool(in_ok))
    check("출력차수 보존", bool(out_ok))
    check("흥분/억제 비율 보존", int((s.edge_sign > 0).sum()) == int((g.edge_sign > 0).sum()))
    check("실제로 재배선됐다", s.meta["shuffle_rewired_frac"] > 0.5,
          f"{s.meta['shuffle_rewired_frac']:.0%}")
    s_path = s.save(tmp / "shuffled.npz")

    print("\n3) 정책망 수치 건전성")
    torch.manual_seed(0)
    ex = ConnectomeExtractor(env.observation_space, graph_path=str(path))
    obs = torch.as_tensor(np.stack([env.observation_space.sample() for _ in range(64)]))
    with torch.no_grad():
        out = ex(obs)
    rms = float(out.pow(2).mean().sqrt())
    check("출력이 전부 유한", bool(torch.isfinite(out).all()))
    check("출력 크기가 학습 가능한 범위", 0.1 < rms < 10.0, f"RMS={rms:.3f}")
    ex.n_settle = 300
    with torch.no_grad():
        far = ex(obs)
    check("정착 300스텝에도 발산 안 함", bool(torch.isfinite(far).all()),
          f"max={float(far.abs().max()):.2f}")
    ex.n_settle = 20

    loss = ex(obs).sum()
    loss.backward()
    nz = int((ex.w_raw.grad != 0).sum())
    check("커넥톰 가중치까지 기울기가 흐른다", nz > 0 and bool(torch.isfinite(ex.w_raw.grad).all()),
          f"0이 아닌 기울기 {nz}/{ex.w_raw.numel()}")

    print("\n4) SB3 연결")
    from stable_baselines3 import PPO
    model = PPO("MlpPolicy", env, n_steps=64, batch_size=64, seed=0, verbose=0,
                policy_kwargs=make_policy_kwargs(str(path)))
    pi_hidden = len(list(model.policy.mlp_extractor.policy_net.children()))
    check("정책 쪽에 은닉층이 없다 (pi=[])", pi_hidden == 0,
          "커넥톰 출력이 바로 액션으로 간다")
    check("액션 헤드가 하강뉴런 수를 입력으로 받는다",
          model.policy.action_net.in_features == len(g.motor_idx),
          f"DN {len(g.motor_idx)}개 -> 액션 5개")
    model.learn(total_timesteps=256)
    a, _ = model.policy.predict(env.reset(seed=0)[0], deterministic=True)
    check("학습 후 액션이 유한", bool(np.isfinite(a).all()), f"{np.round(a, 3)}")

    print("\n5) 셔플 그래프도 같은 경로를 통과")
    m2 = PPO("MlpPolicy", env, n_steps=64, batch_size=64, seed=0, verbose=0,
             policy_kwargs=make_policy_kwargs(str(s_path)))
    m2.learn(total_timesteps=256)
    check("셔플 정책도 학습 루프를 통과", True)

    print("\n6) PD baseline 과 평가 지표")
    from baseline_pd import PDController
    m = run_episodes(PDController(), HopperAttitudeEnv(), episodes=5)
    check("평가 지표가 전부 유한",
          all(np.isfinite(v) for v in m.values() if isinstance(v, (int, float))),
          f"보상 {m['mean_reward']:.1f} · 복원 {m['settle_s']:.2f}s · 추락 {m['crash_rate']:.0%}")

    print("\n7) 제어권한 진단 (과제가 풀 수 있는 것인가)")
    auth = authority()
    check("진단이 계산된다", np.isfinite(auth["ratio"]),
          f"5초 가동각 {auth['reachable_deg']:.1f}도 / 초기교란 {auth['needed_deg']:.0f}도 "
          f"= 여유 {auth['ratio']:.2f}배")
    if auth["ratio"] < 2.0:
        print("       ^ 권한 부족 상태다. 실험 A로 params.yaml 의 Kf 를 채우기 전까지")
        print("         비교군 간 우열은 읽으면 안 된다 (authority.py 참고).")

    print()
    if FAILURES:
        print(f"실패 {len(FAILURES)}건: {', '.join(FAILURES)}")
        return 1
    print("커넥톰 트랙 점검 전부 통과.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
