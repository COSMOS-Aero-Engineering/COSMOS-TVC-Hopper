# `sim/connectome/` — 커넥톰 제약 정책망

초파리 커넥톰의 배선을 PPO 정책망의 **연결 구조**로 쓰는 확장 트랙.
설계 의도·목표·한계는 **[`docs/design/connectome-control.md`](../../docs/design/connectome-control.md)**에 있다.
여기는 "지금 뭘 타이핑하면 되는지"만 적는다.

## 빠른 시작

```bash
# 1) 그래프 만들기 (합성 CX 링 어트랙터 — 네트워크 불필요, 몇 초)
python tasks.py connectome

# 2) 전부 제대로 도는지 확인
python tasks.py conncheck

# 3) 4개 비교군 돌리기 (PD / MLP / 커넥톰 / 셔플)
cd sim/connectome
python run_comparison.py --timesteps 60000 --seeds 3
```

`tasks.py`를 쓰면 `.venv`가 `uv.lock`에 자동으로 맞춰진다. 직접 실행할 거면 먼저
`python tasks.py setup`.

## 파일

| 파일 | 하는 일 |
|---|---|
| `graph.py` | 서브그래프 자료구조 — 저장·적재·정합성 검증·스펙트럼 반경 정규화 |
| `build_subgraph.py` | 그래프 생성. `--source synthetic`(기본) / `--source flywire` |
| `shuffle.py` | 차수보존 셔플 대조군 — **이게 이 실험의 핵심** |
| `policy.py` | `ConnectomeExtractor` — SB3에 꽂는 정책망 |
| `baseline_pd.py` | PD baseline + 게인 격자탐색 |
| `evaluate.py` | 복원시간·오버슈트·정상상태오차·추락률 측정 (모든 비교군 공통) |
| `authority.py` | **제어권한 진단** — "이 과제가 애초에 풀 수 있는가" |
| `run_comparison.py` | 4개 비교군을 같은 조건에서 돌리고 표로 출력 |
| `check.py` | 자체 점검 (CI가 매 PR마다 실행) |
| `graphs/` | 생성된 `.npz` — **커밋 안 한다**, 위 1번으로 다시 만든다 |

## ⚠ 지금 결과를 읽으면 안 되는 이유

`sim/sim_stage1/params.yaml`의 물리 상수가 아직 PLACEHOLDER인데, 그중 `Kf`가 실제값보다
약 37배 작아서 **베인이 5초 동안 자세를 5.8°밖에 못 바꾼다**(초기 교란은 최대 17°).
어떤 제어기도 못 푸는 상태라 네 비교군이 다 같이 실패한다.

```bash
python sim/connectome/authority.py     # 진단표 보기
```

실험 A(EDF 추력곡선)로 `Kf`를 채운 뒤 여유 배수가 2.0 이상이 되면 그때가 본 실험이다.
`run_comparison.py`는 시작할 때 이 경고를 자동으로 띄운다.

## FlyWire 실측 데이터 쓰기 (선택)

```bash
cd sim/connectome
python build_subgraph.py --fetch                          # 수백 MB, 한 번만
python build_subgraph.py --source flywire --max-nodes 1200
python shuffle.py --in graphs/flywire.npz --out graphs/flywire_shuffled.npz
python run_comparison.py --graph graphs/flywire.npz --shuffled graphs/flywire_shuffled.npz
```

데이터는 `.cosmos-cache/flywire/`에 받아지고 레포에는 안 들어간다.
FlyWire v783은 CC-BY — 발표·보고서에 쓸 때 출처를 밝힐 것.

`--max-nodes`는 Teensy 4.0 메모리 예산에서 역산한 값이다(실질 상한 1000~1500뉴런).
`ConnectomeExtractor.describe()`가 실제 파라미터 수와 KB를 찍어준다.
