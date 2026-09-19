"""차수보존 셔플 — 이 프로젝트에서 가장 중요한 대조군.

    python shuffle.py --in graphs/synthetic.npz --out graphs/synthetic_shuffled.npz

왜 필요한가
-----------
커넥톰 정책이 MLP보다 잘 나왔다고 해서 "초파리 배선이 좋아서"라고 말할 수는 없다.
희소한 순환 신경망이면 아무 배선이나 잘 되는 것일 수도 있기 때문이다. 이 둘을 가르려면
**크기·희소도·차수분포·흥분억제 비율이 전부 같고 연결 상대만 무작위인 그래프**와
비교해야 한다. 그게 이 파일이 만드는 것이다.

    실측 커넥톰 > 셔플  ->  "실제 배선 구조가 기여했다"고 말할 수 있다
    실측 커넥톰 ~ 셔플  ->  "그냥 희소 RNN이 잘 된 것" — 이것도 정직한 결과다

이 대조군이 없으면 실험이 아니라 시연이다. 발표에서 제일 먼저 깨지는 지점이기도 하다.

어떻게 보존하나 — 이중 엣지 교환(double-edge swap)
--------------------------------------------------
엣지 (u1->v1), (u2->v2) 두 개를 골라 목적지만 바꾼다: (u1->v2), (u2->v1).

    시냅스전 뉴런이 안 바뀐다  -> 출력차수 보존, 그리고 부호도 자동 보존
                                  (신경전달물질은 사실상 뉴런마다 정해져 있으므로
                                   부호를 엣지에 붙여 옮기면 생물학적으로도 일관된다)
    목적지만 맞바꾼다          -> 입력차수 보존
    가중치는 엣지에 붙어 따라감 -> 가중치 분포 보존

자기연결과 중복 엣지가 생기는 교환은 버린다 — 그러면 실제 성사 비율이 100%가 아니므로
몇 번 성사됐는지를 찍어준다. 성사율이 너무 낮으면(=그래프가 이미 거의 완전연결이면)
셔플이 원본과 별로 안 달라지는 것이므로 그때는 이 대조군 자체가 약해진다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import ConnectomeGraph  # noqa: E402


def degree_preserving_shuffle(g: ConnectomeGraph, seed: int = 0,
                              swaps_per_edge: int = 20) -> ConnectomeGraph:
    rng = np.random.default_rng(seed)
    pre = g.edge_index[0].copy()
    post = g.edge_index[1].copy()
    e = pre.shape[0]

    in_deg_before = np.bincount(post, minlength=g.n_nodes)
    out_deg_before = np.bincount(pre, minlength=g.n_nodes)

    existing = set(zip(pre.tolist(), post.tolist()))
    attempts = e * swaps_per_edge
    accepted = 0

    for _ in range(attempts):
        i, j = rng.integers(0, e, size=2)
        if i == j:
            continue
        u1, v1 = int(pre[i]), int(post[i])
        u2, v2 = int(pre[j]), int(post[j])
        if u1 == v2 or u2 == v1:
            continue  # 자기연결이 생긴다
        if (u1, v2) in existing or (u2, v1) in existing:
            continue  # 중복 엣지가 생긴다
        existing.discard((u1, v1))
        existing.discard((u2, v2))
        existing.add((u1, v2))
        existing.add((u2, v1))
        post[i], post[j] = v2, v1
        accepted += 1

    # 보존 확인 — 여기서 틀리면 대조군 자격이 없으므로 조용히 넘어가면 안 된다.
    assert (np.bincount(pre, minlength=g.n_nodes) == out_deg_before).all(), "출력차수가 안 맞는다"
    assert (np.bincount(post, minlength=g.n_nodes) == in_deg_before).all(), "입력차수가 안 맞는다"

    rewired = int((post != g.edge_index[1]).sum())
    meta = dict(g.meta)
    meta.update({
        "source": f"{g.meta.get('source', '?')}-shuffled",
        "shuffle_seed": seed,
        "shuffle_accepted": accepted,
        "shuffle_attempts": attempts,
        "shuffle_rewired_frac": round(rewired / max(e, 1), 3),
    })

    return ConnectomeGraph(
        node_ids=g.node_ids.copy(),
        node_type=g.node_type.copy(),
        edge_index=np.stack([pre, post]),
        edge_w=g.edge_w.copy(),
        edge_sign=g.edge_sign.copy(),
        sensory_idx=g.sensory_idx.copy(),
        motor_idx=g.motor_idx.copy(),
        meta=meta,
    )


def main() -> int:
    p = argparse.ArgumentParser(description="차수보존 셔플 대조군 생성")
    p.add_argument("--in", dest="src", required=True)
    p.add_argument("--out", dest="dst", required=True)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()

    g = ConnectomeGraph.load(a.src)
    s = degree_preserving_shuffle(g, seed=a.seed)
    # 셔플하면 입력 가중치 행합이 달라지므로 스케일을 다시 맞춘다.
    # 안 맞추면 "커넥톰이 좋다"가 아니라 "스케일이 달랐다"를 측정하게 된다.
    s.normalize_weights()
    s.save(a.dst)
    print(f"원본 : {g.summary()}")
    print(f"셔플 : {s.summary()}")
    print(f"재배선된 엣지 비율: {s.meta['shuffle_rewired_frac']:.1%} "
          f"(교환 성사 {s.meta['shuffle_accepted']}/{s.meta['shuffle_attempts']})")
    print(f"저장: {a.dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
