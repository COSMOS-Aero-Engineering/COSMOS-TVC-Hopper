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
  `"print"` (실제 프린트 대상 파츠만) 두 모드. **`"print"`로 렌더해도 파츠 9개가 합쳐진 채로 나오니,
  외주용 STL은 모듈 하나씩 남기고 개별 export 필요** — 순서는 [`print_parts/README.md`](print_parts/README.md).

**2026-09-18: 실제로 렌더·export 완료.** 이 PC 바탕화면의 `openscad.exe`(2021.01, 정상 동작 — `Program
Files\OpenSCAD\`엔 껍데기만 남아있었던 게 원인이었음)로 렌더 확인. 검증 `echo()` 12개 전부 "정상" —
흡기 통로 안 막음, 베인이 제트 단면을 가로지름, 커플러가 캐비티 안에 들어감 등. 조립 미리보기 이미지는
[`renders/preview_colored.png`](renders/preview_colored.png)·[`renders/vane_ring_closeup.png`](renders/vane_ring_closeup.png).
9개 파츠 STL은 `print_parts/`에 실제로 있음(아래 "재사용 검토한 기존 STL" 밑 문단은 옛 상태 — 지금은
export 완료됨, `print_parts/README.md` 참고).

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

## 완성 모습 렌더 (`showcase.scad`, #59)

`cad/showcase.scad`는 프린트 부품에 구매품(EDF 본체, 배터리, Teensy·IMU 기판, ESC, 서보, 킬스위치)과 배선을 외형만 더한 발표용 장면이다. 프린트 대상이 아니다.

```bash
openscad -o cad/renders/showcase.png --imgsize=1600,1200 --camera=600,-720,420,0,0,30 --projection=p cad/showcase.scad
```

이 렌더에서 확인한 배선 지침:
- 서보선은 가장 가까운 기둥을 타고 올라가 흡입구(반경 39 mm) 바깥으로 돌린 뒤, 아비오닉스 선반의 배선 슬롯 2개(ESC 브래킷 바깥, 만능기판 밑)로 올린다. 흡입구 위를 가로지르면 선이 팬에 빨려 들어간다.
- 배선 슬롯은 10/16에 옮겼다(x 62-74, |y| 8-18). 예전 위치는 ESC 브래킷 플랜지에 절반 넘게 가려졌고, 첫 수정 위치는 만능기판 인서트 보스를 잘랐다(#59). 지금은 `hopper_params.scad` 검증 echo가 세 가지 간격을 모두 확인한다.
- 이 경로의 서보선 길이는 렌더 경로로 어림한 값이 약 290 mm(180°·270° 서보)와 약 370 mm(0°·90° 서보)다. MG90S 기본 리드(250 mm, TowerPro 공식)로는 모자라므로 서보 연장선 4개(150-200 mm)가 필요하다.

## 체결 목록 (2026-10-16, #59)

프린트 부품에는 나사산을 모델링하지 않는다. 구멍은 세 종류다: 볼트 관통(M3 3.4 / M2 2.2), 셀프탭 하부 구멍(M2 1.7), 열융착 인서트(M3, 4.2 막힌 구멍). 치수 변수는 `hopper_params.scad`의 `m3_clear`, `m2_clear`, `m2_tap`, `insert_d`, `insert_h`다.

| 연결 | 부품 | 구멍 | 체결재(개수) |
|---|---|---|---|
| EDF 클램프 이음부 2곳 | `edf_clamp` 반쪽 2개 | 탭 관통 3.4 (y 방향) | M3×16 볼트 + 너트 (2) |
| EDF 클램프 ↔ 기둥 4개 | `edf_clamp` 기둥 고리 | 쪼갠 고리 + 귀 관통 3.4 | M3×12 볼트 + 너트 (4). 높이를 맞춘 뒤 조인다 |
| 서보 ↔ 베인링 장착판 | `vane_ring` | 귀 슬롯 폭 2.2 (구멍 간격 19-41 mm 수용) | M2×8 볼트 + 너트 (8). 너트는 캐비티 안쪽 |
| 서보 혼 ↔ 커플러 | `vane_couplers_x4*` | 혼 물림 구간 전체 M2 셀프탭 홈 1.7 | M2×6 셀프탭 (8). 헐거우면 에폭시 |
| 만능기판 ↔ 아비오닉스 선반 | `avionics_shelf` 보스 4개 | M3 인서트 4.2, 깊이 4, 바닥 1.5 | M3 열융착 인서트 L4 (4) + M3 스탠드오프·볼트 (4) |
| ESC 브래킷 ↔ 아비오닉스 선반 | `esc_bracket`, `avionics_shelf` | 짝 맞춘 타이 슬롯 2쌍 | 케이블타이 2.5 mm (2) |
| ESC ↔ 브래킷 | `esc_bracket` | 타이 슬롯 4 | 케이블타이 (2) + 폼테이프 |
| 선반 ↔ 기둥 | 선반 새들 | 기둥 관통 6.6 + 타이 슬롯 | 케이블타이 + 에폭시 |
| 기둥·다리 ↔ 상판·베인링 | 소켓 6.6, 깊이 12 | — | 에폭시 |
| 배터리 ↔ 선반 | `battery_shelf` 스트랩 슬롯, 턱 사이 78 mm | — | 벨크로 스트랩 (2) |
| 트림 무게추 ↔ 아비오닉스 선반 | 선반 바깥 끝 구멍 2개 Ø5.5 | M5 볼트 + 와셔·너트 묶음 또는 납추, 0-72 g (2) |

`hopper_params.scad` 검증 echo가 배선 슬롯 간격(ESC 플랜지, 인서트 보스, 새들 타이 슬롯, ESC 타이 슬롯)과 배터리 높이 여유를 확인한다.

## 질량 특성 (`cad/cg/`)

`python cad/cg/cg_estimate.py`는 `cad/cg/parts.csv`의 부품별 질량·모양·위치로 총질량, 무게중심(x, y, z), 토크 팔, 관성 모멘트, 민감도를 낸다. 질량 출처는 행마다 적었다(공식 사양, 리스팅, STL 부피 × PETG 1.27 g/cm³ × 0.70, ESTIMATE). 실물을 저울로 재면 그 행을 바꾼다.

2026-10-16 결과(850 mAh 기준): 746 g, CG (+0.4, +1.6, 67.6) mm, l 103.6 mm, Jxx 0.0079 / Jyy 0.0070 / Jzz 0.0028 kg·m². 1300 mAh(156 g)를 쓰면 CG가 배터리 쪽으로 5.3 mm 치우친다. 베인 한계(약 6.5 mm 상당) 안이지만 Stage 1 PD가 기울기 5.6°를 남겨 합격 기준(5°)을 넘는다. 그래서 850 mAh를 권장한다(BOM A4와 같음). 최종 선택은 부장이 한다. CAD와 `parts.csv`는 850 mAh 치수·질량으로 계산했다.

## 조립 간섭 전수 검사 (`cad/tools/check_interference.py`, #59)

프린트 부품 9종과 구매품 외형 11종(EDF, 기둥, 다리, 스파, 서보, 배터리, ESC, 만능기판, 수신기, UBEC, 베일)을 조립 위치에 놓고 모든 쌍의 겹친 부피를 계산한다. 베인은 중립과 하드스톱(±`vane_stop_deg`) 상태를 따로 본다. 겹침이 0.001 cm³를 넘으면 실패한다(약 15분).

```bash
python cad/tools/check_interference.py
```

2026-10-17 결과: 쌍 198개, 정밀 검사 30쌍, **간섭 없음**. 이 검사로 찾아 고친 것: 발 범퍼에 다리 소켓 없음, 다리(수직에서 54°)가 수직 소켓에 안 들어감 → 링 바깥 보스와 기울인 소켓, 베인 꺾기 함수가 피벗이 아니라 원점 기준, ESC 모형 위치. 같은 검토에서 베일이 흡기 구멍 안쪽에 떨어지던 것도 고쳤다(반경 51 mm, 상판 구멍 2개).

이 검사가 보지 않는 것: 실물 치수(구매품은 공식·리스팅 외형), 조립 순서와 공구 접근, 출력 가능성(서포트·벽 두께), 강도, 배선 굽힘.

### 2026-10-17 실측 반영 (배터리 159.5 g, ESC 34.2 g)

배터리(+Y) 한쪽 배치라 옆 무게중심이 +Y로 9.2 mm 치우쳤다(베인 한계 약 6.5 mm 밖). 아비오닉스 선반 바깥 끝 아래에 M5 볼트 2개로 무게추를 다는 구멍을 냈다(01 문서 §8.3 트림). 지금 표 기준 약 72 g이면 치우침 0이다. 기판·수신기 같은 추정값 부품이 실제로 더 무거우면 무게추를 줄인다. 조립 뒤 01 문서 §8.3대로 매달아 보고 정한다.

무게추 72 g을 넣은 결과: 771 g, CG (+0.1, +0.1, 84.0) mm, l 120.0 mm, TWR 1.69. Stage 1 PD(공중 정지 추력, 시드 200개)는 설계 CG에서 넘어짐 0 %·기울기 0.1°, 랜덤화·서보 지연 100 ms에서도 0 %다. z_cg는 01 문서 목표 60-75 mm보다 높지만 토크 팔이 길어지는 쪽이다.

배터리 선반 턱 사이를 74 → 78 mm로 넓혔다(실측 최대 길이 76 mm).
