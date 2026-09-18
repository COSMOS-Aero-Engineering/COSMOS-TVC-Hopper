# cad/ — 파라메트릭 CAD

CLAUDE.md/AGENTS.md 원칙: **프리핸드 CAD 금지.** 코드 기반 파라메트릭 설계 우선.

## 현재 정본

**[`hopper_params.scad`](hopper_params.scad)** — rev C 오픈 스탠드오프 프레임 전체를 담은 단일 파일.
EDF 실측(2026-09-13, 하우징 외경 72mm·볼트 플랜지 없음 확인) 반영해서 **분할 클램프(collar clamp)
마운트**로 설계됨(원래 볼트 마운트 가정이었던 게 실물과 안 맞아서 변경). 기둥-베인링 반경 불일치, 다리
스태거 미적용 등 구조 버그 2건도 수정된 상태.

- 맨 위 **"MEASURED"** 블록만 실측값. 나머지는 `docs/design/00-hopper-master-design.md` §4 값 그대로.
- 파일 맨 아래 `echo()`들이 조립 정합성을 콘솔에 출력 — 값 바꾼 뒤 OpenSCAD 콘솔에서 반드시 확인.
- `render_mode = "preview"` (조립 미리보기, 구매품인 탄소관·서보·배터리는 색블록으로만 표시) /
  `"print"` (실제 프린트 대상 파츠만) 두 모드. **`"print"`로 렌더해도 파츠 7개가 합쳐진 채로 나오니,
  외주용 STL은 모듈 하나씩 남기고 개별 export 필요** — 순서는 [`print_parts/README.md`](print_parts/README.md).

## 폴더

| 경로 | 내용 |
|---|---|
| `hopper_params.scad` | 정본 (위 설명) |
| `print_parts/` | 외주용 STL 7종을 여기다 export (아직 비어 있음 — OpenSCAD 로컬 미설치, `print_parts/README.md` 참고) |
| `print-orders/` | 실제로 외주에 발주 넣은 STL의 스냅샷(그때그때 폴더 만들어서). `.gitignore` 예외로 커밋됨 — 나머지 STL은 재생성 가능이라 커밋 안 함 |
| `legacy/` | rev B 단계에서 쓰던 3분할 스크립트(`params.scad`/`top_plate.scad`/`vane_ring.scad`) — **`hopper_params.scad`로 대체돼 더 이상 안 씀.** 과거 계산 참고용으로만 보존 |

## 워크플로

1. [OpenSCAD](https://openscad.org/downloads.html) 설치(무료). `hopper_params.scad` 열고 F5.
2. 부품 실측값이 바뀌면 파일 맨 위 `MEASURED` 블록만 수정 — 나머지는 자동 갱신.
3. 콘솔 `echo()` 출력으로 조립 정합성(클램프가 EDF 몸통 범위 안에 있는지, 트레이가 안 겹치는지 등) 확인.
4. 개별 모듈만 남기고 `F6`(Render) → STL export → `print_parts/`에 저장 (순서: [`print_parts/README.md`](print_parts/README.md)).
5. 슬라이서에서 확인(PETG, 인필 40%, 벽 4라인 — PLA 금지, 모터 폐열).
6. 실제 외주 발주 시 그 STL을 `print-orders/<날짜>/`로 복사해서 커밋.

## 재사용 검토한 기존 STL (참고 기록, rev C에선 안 씀)

- SolidGeek/SingleRotorUAV의 Onshape CAD — `firmware/reference/SingleRotorUAV/ORIGIN.md`·
  `docs/design/research-open-source-references.md` 참고. 펌웨어는 그쪽을 vendor-copy해서 쓰지만,
  CAD는 결국 이 저장소의 `hopper_params.scad`로 직접 구현하는 쪽으로 감(실측 기반 클램프 마운트가
  SolidGeek 원본 형상과 안 맞아서).
- K-9 TVC Hopper Test Vehicle(printables.com/model/164897) — 다리 배치 기하만 참고, 동체 재사용 안 함.

## 좌표 관례

- Z = 0: EDF 배기면(§4 기준면). +Z 위(흡기), −Z 아래(배기).
- 베인 0°(중립) = 시위가 Z축과 평행. 부호는 실기 TC-1에서 정합.
