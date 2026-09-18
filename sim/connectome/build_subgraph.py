"""커넥톰 서브그래프를 만든다 — 합성 모티프(기본) 또는 FlyWire 실측(선택).

    python build_subgraph.py --source synthetic            # 네트워크 불필요, 몇 초
    python build_subgraph.py --fetch                       # FlyWire CSV 내려받기 (수백 MB)
    python build_subgraph.py --source flywire --max-nodes 1200

왜 두 경로인가
--------------
synthetic : 중앙복합체(CX) 링 어트랙터 회로를 문헌의 배선 규칙대로 직접 짜 넣은 그래프.
            FlyWire 데이터를 한 바이트도 안 받아도 되고, 100 뉴런 남짓이라 CI에서 몇 초면
            돈다. "장난감"이 아니라 그 자체로 의미가 있는 비교군이다 — 사람이 아는 회로
            규칙만으로 만든 것이라, 실측 커넥톰이 이것보다 나은지를 바로 물어볼 수 있다.
flywire   : FlyWire v783 공개 릴리스에서 CX + 하강뉴런(DN) 부분을 잘라낸 실제 배선.
            수백 MB를 받아야 하므로 부장 PC에서 수동으로 한 번 돌리는 경로다.

왜 pandas를 안 쓰나
------------------
connections.csv.gz 는 270만 행이라 pandas가 편하긴 하다. 하지만 pandas를 넣으면
sim/pyproject.toml 의존성이 늘고 uv.lock을 다시 말아야 하는데, 그건 모두의 설치와 CI가
매번 받아야 하는 바이트가 늘어난다는 뜻이다. 이 파일의 FlyWire 경로는 CI에서 절대 안
돈다(합성 경로만 돈다). 1회성 전처리 하나 때문에 설치를 무겁게 만들 이유가 없어서 표준
라이브러리 gzip+csv 로 스트리밍한다 — 느리지만(수십 초) 한 번만 돌린다.

FlyWire 데이터 출처 (CC-BY, 로그인 불필요):
    https://storage.googleapis.com/flywire-data/codex/data/fafb/783/
논문: Dorkenwald et al., Nature 2024 / Schlegel et al., Nature 2024
"""
from __future__ import annotations

import argparse
import csv
import gzip
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import ConnectomeGraph  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cosmos-cache" / "flywire"
FLYWIRE_BASE = "https://storage.googleapis.com/flywire-data/codex/data/fafb/783"
FILES = ("connections.csv.gz", "classification.csv.gz")

# 중앙복합체에서 자세·방향 표상에 직접 관여하는 세포타입. 접두사로 맞춘다
# (FlyWire의 cell_type은 ER1_a, PEN_a(PEN1), PFL3 처럼 접미사가 붙는다).
CX_PREFIXES = ("EPG", "PEN", "PEG", "Delta7", "ER", "PFL", "hDelta", "FC")

# 신경전달물질 -> 부호. 초파리는 글루탐산이 GluCl 채널을 통해 대개 '억제성'이다
# (척추동물과 반대라 틀리기 쉬운 지점). 도파민/세로토닌/옥토파민은 조절성이라
# 흥분-억제로 딱 나눌 수 없어서, 기본값은 흥분으로 두되 --drop-modulatory 로 뺄 수 있다.
NT_SIGN = {"ACH": 1.0, "GABA": -1.0, "GLUT": -1.0, "DA": 1.0, "SER": 1.0, "OCT": 1.0}
MODULATORY = {"DA", "SER", "OCT"}


# ---------------------------------------------------------------------------
# 합성 경로 — 중앙복합체 링 어트랙터 모티프
# ---------------------------------------------------------------------------

def build_synthetic(ring: int = 16, n_delta7: int = 8, n_dn: int = 8,
                    n_rate_sensors: int = 4) -> ConnectomeGraph:
    """문헌의 CX 배선 규칙으로 링 어트랙터를 직접 짠다.

    구현하는 규칙 (Seelig & Jayaraman 2015, Kim et al. Science 2017, Green et al. 2017):
        EPG i -> EPG i-1, i+1        국소 흥분  — 활동 덩어리(bump)를 뭉치게
        EPG   -> Delta7 -> EPG       전역 억제  — bump가 '하나만' 서게
        EPG i -> PEN_L i -> EPG i-1  왼쪽 밀기   ] 각속도 입력이 이 두 갈래의 균형을
        EPG i -> PEN_R i -> EPG i+1  오른쪽 밀기 ] 깨서 bump를 회전시킨다 = 자이로 적분
        EPG i -> PFL (i + ring/4)    오프셋 읽기 — 목표방향 대비 오차를 만드는 자리
        PFL   -> DN                  조향 출력

    즉 "각속도를 적분해 각도를 유지하고, 그 오차를 출력으로 내보내는" 구조가 배선만으로
    들어 있다. 우리 Stage 1 과제(자세 안정화)와 기능적으로 같은 자리라서 고른 회로다.
    """
    types: list[str] = []

    def alloc(name: str, count: int) -> np.ndarray:
        start = len(types)
        types.extend([name] * count)
        return np.arange(start, start + count, dtype=np.int64)

    epg = alloc("EPG", ring)
    d7 = alloc("Delta7", n_delta7)
    pen_l = alloc("PEN_L", ring)
    pen_r = alloc("PEN_R", ring)
    pfl = alloc("PFL", ring)
    dn = alloc("DN", n_dn)
    s_ang = alloc("SENS_ANG", ring)
    s_rot_l = alloc("SENS_ROT_L", n_rate_sensors)
    s_rot_r = alloc("SENS_ROT_R", n_rate_sensors)

    pre: list[int] = []
    post: list[int] = []
    sign: list[float] = []
    weight: list[float] = []

    def connect(sources, targets, s: float, w: float = 1.0):
        for a in np.atleast_1d(sources):
            for b in np.atleast_1d(targets):
                if a == b:
                    continue  # 자기연결은 정착 루프에서 순수 이득으로만 작동해 의미가 없다
                pre.append(int(a))
                post.append(int(b))
                sign.append(s)
                weight.append(w)

    for i in range(ring):
        connect(epg[i], epg[(i - 1) % ring], +1.0, 0.6)
        connect(epg[i], epg[(i + 1) % ring], +1.0, 0.6)
        connect(epg[i], pen_l[i], +1.0, 1.0)
        connect(epg[i], pen_r[i], +1.0, 1.0)
        connect(pen_l[i], epg[(i - 1) % ring], +1.0, 1.2)
        connect(pen_r[i], epg[(i + 1) % ring], +1.0, 1.2)
        connect(epg[i], pfl[(i + ring // 4) % ring], +1.0, 1.0)
        connect(s_ang[i], epg[i], +1.0, 1.0)

    connect(epg, d7, +1.0, 0.5)
    connect(d7, epg, -1.0, 0.5)
    connect(pfl, dn, +1.0, 1.0)
    connect(s_rot_l, pen_l, +1.0, 1.0)
    connect(s_rot_r, pen_r, +1.0, 1.0)

    g = ConnectomeGraph(
        node_ids=np.arange(len(types), dtype=np.int64),
        node_type=np.array(types, dtype="<U24"),
        edge_index=np.array([pre, post], dtype=np.int64),
        edge_w=np.array(weight, dtype=np.float32),
        edge_sign=np.array(sign, dtype=np.float32),
        sensory_idx=np.concatenate([s_ang, s_rot_l, s_rot_r]),
        motor_idx=dn,
        meta={"source": "synthetic-cx-ring", "ring": ring, "n_delta7": n_delta7,
              "n_dn": n_dn, "n_rate_sensors": n_rate_sensors},
    )
    g.normalize_weights()
    return g


# ---------------------------------------------------------------------------
# FlyWire 경로
# ---------------------------------------------------------------------------

def fetch_flywire(force: bool = False) -> None:
    """공개 버킷에서 CSV를 받아 .cosmos-cache/flywire 에 둔다(레포에 커밋하지 않는다)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        dest = CACHE / name
        if dest.exists() and not force:
            print(f"[캐시] {name} — 이미 있다 ({dest.stat().st_size / 1e6:.0f} MB)")
            continue
        url = f"{FLYWIRE_BASE}/{name}"
        print(f"[받는 중] {url}")
        tmp = dest.with_suffix(dest.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)  # noqa: S310 — 고정된 공개 https 주소
        tmp.replace(dest)
        print(f"          -> {dest} ({dest.stat().st_size / 1e6:.0f} MB)")


def _pick(header, *candidates: str) -> str:
    """컬럼명 철자가 릴리스마다 흔들리므로 후보 중 실제로 있는 것을 고른다."""
    lower = {h.strip().lower(): h for h in (header or [])}
    for c in candidates:
        if c in lower:
            return lower[c]
    raise KeyError(f"필요한 컬럼을 못 찾았다. 후보={candidates} 실제 헤더={header}")


def build_flywire(max_nodes: int, min_syn: int, drop_modulatory: bool) -> ConnectomeGraph:
    for name in FILES:
        if not (CACHE / name).exists():
            raise FileNotFoundError(
                f"{CACHE / name} 가 없다.\n"
                "     먼저 받아야 한다:  python build_subgraph.py --fetch"
            )

    # -- 1) 노드 분류 읽기 --------------------------------------------------
    cx_ids: set[int] = set()
    dn_ids: set[int] = set()
    type_of: dict[int, str] = {}
    with gzip.open(CACHE / "classification.csv.gz", "rt", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        c_root = _pick(r.fieldnames, "root_id", "rootid")
        c_super = _pick(r.fieldnames, "super_class", "superclass")
        c_type = _pick(r.fieldnames, "cell_type", "celltype", "type")
        for row in r:
            try:
                rid = int(row[c_root])
            except (TypeError, ValueError):
                continue
            ctype = (row.get(c_type) or "").strip()
            sclass = (row.get(c_super) or "").strip().lower()
            if ctype.startswith(CX_PREFIXES):
                cx_ids.add(rid)
                type_of[rid] = ctype
            elif sclass == "descending":
                dn_ids.add(rid)
                type_of[rid] = ctype or "DN"
    print(f"[분류] CX 후보 {len(cx_ids)}개 · 하강뉴런 {len(dn_ids)}개")
    if not cx_ids:
        raise RuntimeError("CX 세포타입을 하나도 못 찾았다 — cell_type 컬럼 값을 확인할 것.")

    # -- 2) 연결 읽기: CX 내부 + CX->DN 1홉 ---------------------------------
    kept: list[tuple[int, int, int, str]] = []
    dn_hit: set[int] = set()
    with gzip.open(CACHE / "connections.csv.gz", "rt", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        c_pre = _pick(r.fieldnames, "pre_root_id", "pre_pt_root_id", "pre")
        c_post = _pick(r.fieldnames, "post_root_id", "post_pt_root_id", "post")
        c_syn = _pick(r.fieldnames, "syn_count", "synapses", "weight")
        c_nt = _pick(r.fieldnames, "nt_type", "neurotransmitter", "nt")
        for row in r:
            try:
                a, b, n = int(row[c_pre]), int(row[c_post]), int(float(row[c_syn]))
            except (TypeError, ValueError):
                continue
            if n < min_syn or a == b:
                continue
            a_cx = a in cx_ids
            if a_cx and b in cx_ids:
                kept.append((a, b, n, (row.get(c_nt) or "").strip().upper()))
            elif a_cx and b in dn_ids:
                kept.append((a, b, n, (row.get(c_nt) or "").strip().upper()))
                dn_hit.add(b)
    print(f"[연결] 1차 통과 {len(kept)}개 · CX가 닿는 DN {len(dn_hit)}개")

    if drop_modulatory:
        before = len(kept)
        kept = [e for e in kept if e[3] not in MODULATORY]
        print(f"[조절성 제거] {before} -> {len(kept)}")

    # -- 3) 크기 맞추기: 연결이 약한 뉴런부터 떨어뜨린다 ---------------------
    strength: dict[int, int] = {}
    for a, b, n, _ in kept:
        strength[a] = strength.get(a, 0) + n
        strength[b] = strength.get(b, 0) + n
    nodes = sorted(strength, key=lambda k: strength[k], reverse=True)[:max_nodes]
    keep = set(nodes)
    kept = [e for e in kept if e[0] in keep and e[1] in keep]
    if not kept:
        raise RuntimeError(
            "자르고 나니 남은 연결이 없다 — --min-syn 을 낮추거나 --max-nodes 를 키울 것."
        )

    # 남은 노드만 다시 모아 지역 인덱스를 새로 매긴다. (여기를 빼먹으면 edge_index가
    # 원본 root_id 범위를 가리켜서 graph.validate()가 잡는다.)
    nodes = sorted({e[0] for e in kept} | {e[1] for e in kept})
    local = {rid: i for i, rid in enumerate(nodes)}

    pre = np.array([local[a] for a, _, _, _ in kept], dtype=np.int64)
    post = np.array([local[b] for _, b, _, _ in kept], dtype=np.int64)
    # log1p: syn_count가 1~1000+ 로 퍼져 있어 선형으로 쓰면 소수의 굵은 연결이 전부를
    # 지배한다. 로그로 눌러 초기값을 만들고, 실제 스케일은 normalize_weights가 잡는다.
    w = np.log1p(np.array([n for _, _, n, _ in kept], dtype=np.float64)).astype(np.float32)
    sign = np.array([NT_SIGN.get(nt, 1.0) for _, _, _, nt in kept], dtype=np.float32)

    types = np.array([type_of.get(rid, "?") for rid in nodes], dtype="<U24")
    is_dn = np.array([rid in dn_ids for rid in nodes])
    motor_idx = np.flatnonzero(is_dn).astype(np.int64)
    if motor_idx.size == 0:
        raise RuntimeError("남은 노드에 하강뉴런이 없다 — --max-nodes 를 키울 것.")

    # 감각 주입 위치: FlyWire는 '뇌만' 담고 있어서 평형곤(haltere, 초파리의 자이로)
    # 감각뉴런이 아예 없다. 그래서 IMU를 EPG/PEN 링에 직접 꽂는다 — 이건 생물학적
    # 충실도를 한 단계 포기한 것이고, 제대로 하려면 MaleCNS(뇌+VNC)로 가야 한다.
    # docs/design/connectome-control.md 의 "알려진 한계" 참고.
    ring_like = np.array([str(t).startswith(("EPG", "PEN")) for t in types])
    sensory_idx = np.flatnonzero(ring_like).astype(np.int64)
    if sensory_idx.size == 0:
        sensory_idx = np.argsort(-np.bincount(post, minlength=len(nodes)))[:16].astype(np.int64)

    g = ConnectomeGraph(
        node_ids=np.array(nodes, dtype=np.int64),
        node_type=types,
        edge_index=np.stack([pre, post]),
        edge_w=w,
        edge_sign=sign,
        sensory_idx=sensory_idx,
        motor_idx=motor_idx,
        meta={"source": "flywire-v783-cx-dn", "max_nodes": max_nodes, "min_syn": min_syn,
              "drop_modulatory": drop_modulatory},
    )
    g.normalize_weights()
    return g


# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="커넥톰 서브그래프 생성")
    p.add_argument("--source", choices=("synthetic", "flywire"), default="synthetic")
    p.add_argument("--out", default=None, help="출력 npz (기본: graphs/<source>.npz)")
    p.add_argument("--fetch", action="store_true", help="FlyWire CSV 내려받기만 하고 끝낸다")
    p.add_argument("--force", action="store_true", help="캐시가 있어도 다시 받는다")
    p.add_argument("--ring", type=int, default=16, help="합성: 링 뉴런 수")
    p.add_argument("--max-nodes", type=int, default=1200, help="FlyWire: 노드 상한")
    p.add_argument("--min-syn", type=int, default=5, help="FlyWire: 시냅스 수 하한")
    p.add_argument("--drop-modulatory", action="store_true", help="FlyWire: DA/SER/OCT 제외")
    a = p.parse_args()

    if a.fetch:
        fetch_flywire(force=a.force)
        return 0

    if a.source == "synthetic":
        g = build_synthetic(ring=a.ring)
    else:
        g = build_flywire(a.max_nodes, a.min_syn, a.drop_modulatory)

    out = Path(a.out) if a.out else Path(__file__).resolve().parent / "graphs" / f"{a.source}.npz"
    g.save(out)
    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"\n{g.summary()}\n저장: {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
