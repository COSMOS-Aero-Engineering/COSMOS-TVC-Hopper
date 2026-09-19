"""커넥톰 서브그래프의 자료구조 — 저장·적재·검증·스케일 정규화.

이 파일이 하는 일은 하나다: "뉴런 N개와 그 사이 연결 E개"를 정책망이 바로 쓸 수 있는
형태로 들고 있는 것. 어디서 왔는지(FlyWire 실측이냐 합성 모티프냐)는 build_subgraph.py가
알고, 그걸로 뭘 하는지(PPO 정책)는 policy.py가 안다. 여기는 그 사이의 좁은 경계다.

왜 npz 한 덩어리인가: 노드 목록·엣지·부호·초기가중치·입출력 위치가 따로 놀면 반드시
어긋난다(엣지 인덱스는 노드 순서에 의존하는데, 노드를 다시 정렬하는 순간 전부 깨진다).
한 파일에 같이 넣고, load() 할 때마다 validate()로 정합성을 다시 확인한다.

담는 내용:
    node_ids    (N,)    int64   원본 식별자. FlyWire면 root_id, 합성이면 일련번호.
    node_type   (N,)    <U24    세포타입 문자열 (EPG, PEN_L, Delta7, DN, ...). 분석·디버깅용.
    edge_index  (2, E)  int64   [0]=시냅스전(pre) 지역인덱스, [1]=시냅스후(post) 지역인덱스
    edge_w      (E,)    float32 가중치 크기의 '초기값'. 항상 양수 — 부호는 아래가 따로 든다.
    edge_sign   (E,)    float32 +1 흥분 / -1 억제. 학습 중에도 안 바뀐다(신경전달물질 고정).
    sensory_idx (S,)    int64   관측을 주입할 뉴런 위치
    motor_idx   (M,)    int64   액션을 읽어낼 뉴런 위치 (하강뉴런 DN)
    meta        (json)          출처·생성 파라미터 기록
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class ConnectomeGraph:
    node_ids: np.ndarray
    node_type: np.ndarray
    edge_index: np.ndarray
    edge_w: np.ndarray
    edge_sign: np.ndarray
    sensory_idx: np.ndarray
    motor_idx: np.ndarray
    meta: dict

    # ── 기본 정보 ────────────────────────────────────────────────────────────
    @property
    def n_nodes(self) -> int:
        return int(self.node_ids.shape[0])

    @property
    def n_edges(self) -> int:
        return int(self.edge_index.shape[1])

    def summary(self) -> str:
        exc = int((self.edge_sign > 0).sum())
        return (
            f"뉴런 {self.n_nodes}개 · 연결 {self.n_edges}개 "
            f"(흥분 {exc} / 억제 {self.n_edges - exc}) · "
            f"감각 {len(self.sensory_idx)} · 운동 {len(self.motor_idx)} · "
            f"출처 {self.meta.get('source', '?')}"
        )

    # ── 검증 ────────────────────────────────────────────────────────────────
    def validate(self) -> None:
        """조용히 틀린 그래프가 학습까지 흘러가는 걸 막는다.

        여기서 잡는 사고는 전부 실제로 나기 쉬운 것들이다: 노드를 걸러낸 뒤 엣지
        인덱스를 다시 매기지 않아 범위를 벗어나거나, 부호 컬럼이 비어서 0이 섞이거나,
        모터 뉴런이 하나도 안 잡혀서 features_dim이 0이 되거나.
        """
        n = self.n_nodes
        if n == 0:
            raise ValueError("노드가 0개다.")
        if self.node_type.shape[0] != n:
            raise ValueError(f"node_type 길이({self.node_type.shape[0]})가 노드 수({n})와 다르다.")
        if self.edge_index.ndim != 2 or self.edge_index.shape[0] != 2:
            raise ValueError(f"edge_index 모양이 (2, E)가 아니다: {self.edge_index.shape}")
        if self.edge_w.shape[0] != self.n_edges or self.edge_sign.shape[0] != self.n_edges:
            raise ValueError("edge_w/edge_sign 길이가 엣지 수와 다르다.")
        if self.n_edges and (self.edge_index.min() < 0 or self.edge_index.max() >= n):
            raise ValueError(
                f"엣지가 없는 노드를 가리킨다 (범위 0..{n - 1}, 실제 "
                f"{self.edge_index.min()}..{self.edge_index.max()}). "
                "노드를 거른 뒤 엣지 인덱스를 다시 매기지 않은 경우가 대부분이다."
            )
        if (self.edge_w <= 0).any():
            raise ValueError("edge_w 에 0 이하가 있다 — 크기는 항상 양수여야 한다(부호는 edge_sign).")
        if not np.isin(self.edge_sign, (-1.0, 1.0)).all():
            raise ValueError("edge_sign 은 +1 또는 -1 만 가능하다.")
        for name, idx in (("sensory_idx", self.sensory_idx), ("motor_idx", self.motor_idx)):
            if idx.shape[0] == 0:
                raise ValueError(f"{name} 가 비어 있다.")
            if idx.min() < 0 or idx.max() >= n:
                raise ValueError(f"{name} 가 노드 범위를 벗어난다.")

    # ── 스케일 정규화 ────────────────────────────────────────────────────────
    def spectral_radius(self, iters: int = 300) -> float:
        """|W| 의 최대 고윳값을 거듭제곱법으로 구한다.

        |W| 는 원소가 전부 음이 아니므로 Perron-Frobenius에 의해 최대 고윳값이 실수이고
        유일하게 지배적이다 — 거듭제곱법이 확실히 수렴한다. 부호를 살린 W의 스펙트럼
        반경은 이보다 작거나 같으므로(rho(W) <= rho(|W|)), 이걸로 맞춰두면 안전한 쪽으로
        틀린다. 희소 연산이라 뉴런 수천 개에서도 비용이 무시할 만하다.
        """
        if self.n_edges == 0:
            return 0.0
        pre, post = self.edge_index
        w = np.abs(self.edge_w.astype(np.float64))
        v = np.full(self.n_nodes, 1.0 / np.sqrt(self.n_nodes))
        rho = 0.0
        for _ in range(iters):
            u = np.zeros(self.n_nodes)
            np.add.at(u, post, w * v[pre])
            rho = float(np.linalg.norm(u))
            if rho <= 1e-300:
                return 0.0
            v = u / rho
        return rho

    def normalize_weights(self, target_radius: float = 0.9) -> None:
        """가중치 전체에 상수배를 걸어 순환 dynamics가 폭발하지 않게 만든다.

        시냅스 개수(syn_count)를 그대로 가중치로 쓰면 반드시 발산한다. FlyWire의
        syn_count는 1에서 1000+ 까지 퍼져 있고, 어떤 뉴런은 들어오는 연결이 수백 개다.
        그대로 두면 정착 루프에서 발화율이 지수적으로 튀고 학습은 NaN으로 끝난다.

        처음엔 '최대 입력 가중치 행합'(||W||_inf)을 1로 맞췄다. 안 터지는 건 확실하지만
        실제로 재보니 너무 보수적이었다 — 합성 CX 그래프에서 행합은 16인데 스펙트럼
        반경은 0.34였다. 즉 모든 가중치를 1/16로 줄여놓고 쓰고 있었고, 그 결과
        감각->EPG->PFL->DN 3홉을 지나는 동안 신호가 16^3 = 4000배 죽어서 출력이 1e-7
        수준으로 깔렸다. 기울기는 흘렀지만 학습이 될 수 있는 크기가 아니었다.

        그래서 판정을 스펙트럼 반경으로 바꿨다. 이건 순환 신경망에서 표준적으로 쓰는
        기준이고(에코 스테이트 네트워크의 rho < 1), 위 spectral_radius()가 |W| 기준이라
        여전히 안전한 쪽으로 틀린다. 남은 신호 크기 문제는 policy.py 의 출력 보정이
        따로 맡는다 — 정규화는 '안 터지게'만 책임지고, '크기를 알맞게'는 거기서 한다.
        """
        if self.n_edges == 0:
            return
        rho = self.spectral_radius()
        if rho <= 0:
            return
        row_sum = np.zeros(self.n_nodes, dtype=np.float64)
        np.add.at(row_sum, self.edge_index[1], np.abs(self.edge_w.astype(np.float64)))
        self.edge_w = (self.edge_w.astype(np.float64) * (target_radius / rho)).astype(np.float32)
        self.meta["spectral_radius_before"] = round(rho, 6)
        self.meta["spectral_radius_target"] = target_radius
        self.meta["row_sum_before"] = round(float(row_sum.max()), 6)

    # ── 입출력 ──────────────────────────────────────────────────────────────
    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.validate()
        np.savez_compressed(
            path,
            node_ids=self.node_ids.astype(np.int64),
            node_type=self.node_type.astype("<U24"),
            edge_index=self.edge_index.astype(np.int64),
            edge_w=self.edge_w.astype(np.float32),
            edge_sign=self.edge_sign.astype(np.float32),
            sensory_idx=self.sensory_idx.astype(np.int64),
            motor_idx=self.motor_idx.astype(np.int64),
            meta=np.array(json.dumps(self.meta, ensure_ascii=False)),
        )
        return path

    @classmethod
    def load(cls, path: str | Path) -> "ConnectomeGraph":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"그래프 파일이 없다: {path}\n"
                "     먼저 만들어야 한다:  python build_subgraph.py --source synthetic"
            )
        with np.load(path, allow_pickle=False) as z:
            g = cls(
                node_ids=z["node_ids"],
                node_type=z["node_type"],
                edge_index=z["edge_index"],
                edge_w=z["edge_w"],
                edge_sign=z["edge_sign"],
                sensory_idx=z["sensory_idx"],
                motor_idx=z["motor_idx"],
                meta=json.loads(str(z["meta"])),
            )
        g.validate()
        return g
