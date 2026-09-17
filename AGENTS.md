# COSMOS — TVC 착륙 호퍼 + 강화학습 프로젝트

국제학교(청도대원학교) 항공우주공학 동아리 COSMOS의 26–27학년도 1학기 프로젝트. 이 파일은 이
저장소에서 작업하는 **모든 AI 에이전트(Claude Code·Codex·Cursor 등)와 사람 모두를 위한 정본
컨텍스트 문서**다. 새 세션/새 팀원은 이 파일부터 읽을 것.

**이 파일이 유일한 정본이다.** claude.ai나 Codex 같은 챗 프로젝트 사이드바에 이 내용을 붙여넣어
쓰고 있다면, 그건 복사본이지 정본이 아니다 — **복사본을 직접 고치지 말고, 항상 이 git 저장소의
`AGENTS.md`를 최신으로 만든 다음 그걸 복사본에 덮어써서 갱신할 것.** (예전엔 반대로 "양쪽에 동일하게
유지"라고만 적어놨었는데, 실제로는 한쪽(Codex 복사본)을 기계적 find-replace로 만들다가 `claude.ai`
링크가 `Codex.ai`로 깨지는 사고가 있었다 — 2026-09-17 발견·수정. 정본을 하나로 못박아야 이런 사고가
안 난다.)

사람 팀원용 실전 가이드(개발환경 세팅·협업 규칙·트러블슈팅)는 **[`README.md`](README.md)**에 따로
있다 — 이 파일과 역할이 다르다: AGENTS.md = 설계 의도·확정 결정·현재 상태(왜 이렇게 하는지),
README.md = 지금 당장 뭘 타이핑해야 하는지.

**마지막 갱신: 2026-09-18.**

---

## 문서 맵

| 경로 | 내용 | 상태 |
|---|---|---|
| `docs/design/00-hopper-master-design.md` | **마스터 설계도 rev C** — 아키텍처·치수·질량·전자·펌웨어·시험카드·리스크. 이 밑의 요약이 아니라 **이 파일이 기구 설계의 단일 진실 소스** | 현행 |
| `docs/design/01-avionics-integration-final.md` | **아비오닉스·배선·기계통합 확정판 rev C.1** — Teensy 핀맵·전원계통·빵판/만능기판 배치(홀 좌표까지)·기계 통합(장비선반 등)·CG 재계산·조립순서·브링업절차. 마스터 §6.5·§7과 충돌 시 이 문서가 최신(§12에 충돌지점 명시) | 현행, 2026-09-17 |
| `docs/design/02-web-dashboard-design.md` | **웹 대시보드·3D 인터페이스 설계도(신규)** — 소프트웨어팀 "웹으로 구현"의 정확한 스펙: 목표·산출물 3종(비교대시보드/3D뷰어/sim뷰어)·아키텍처·**CSV 데이터 계약**(펌웨어↔웹 연결점)·기술스택 추천 | 신규, 2026-09-18 |
| `docs/design/03-control-pipeline-design.md` | **제어 파이프라인 심화 설계(신규)** — PID/RL 아키텍처(직접비교 vs Residual RL)·3D 물리엔진 전환(Stage 1 PoC→Stage 2 후보 검증)·Stage별 State/Action Space·Domain Randomization 갭·온보드 배포(ONNX/TFLite Micro)·참고 오픈소스 검증상태. **PID vs RL 관련 내용의 단일 진실 소스 — 아래 §확정된 방향의 관련 서술은 이 문서로 이동함** | 신규, 2026-09-18 |
| `docs/design/research-open-source-references.md` | rev C 근거 리서치 (SolidGeek·Bresciani/PX4·기타 비교) | 완료 |
| `docs/design/BOM-revC-teensy.md` | 구매 리스트 (현행, ₩310–530k) | 현행 |
| `docs/design/modelling-notes-ch3.md` | 논문 3장 정리 + `hopper_aviary.py` 코드 대응표(어디가 논문과 다른지 포함) | 2026-09-17 재작성 |
| `docs/design/general-arrangement.svg`, `avionics-breadboard.svg`, `avionics-perfboard.svg` | 배치도·빵판/만능기판 배선도(01번 문서 §4·§5 대응 도면) | — |
| `docs/design/tools/gen_board_svgs.py` | 위 보드 SVG 생성 스크립트 | — |
| `docs/design/references/Jacobsen2021_*.pdf` | SolidGeek/Jacobsen 논문 전문 — 제작·제어 이론의 1차 자료 | — |
| `docs/execution/week-01-kickoff.md` | 1–2주차 마스터 실행계획 — 타임라인·부장 준비·부품 전체·세션 진행 | 9/18–19 세션용 |
| `docs/execution/semester-roadmap.md` | **3–10주차 세션별 실행계획(신규)** — week-01-kickoff.md를 이어받아 팀 3개를 매주 세션 단위로 배치. KiCad 착수(Week 4)·baseline 확정(Week 7)·RL 비교(Week 8)·발표(Week 10). §0.1에 원래 매크로 로드맵과의 일정 차이 분석 포함 | 신규, 2026-09-18 |
| `docs/execution/procurement-review.md` | 구글시트 행별 검토 | — |
| `docs/execution/bench-wiring.svg` | 벤치 배선도(구버전 — `01-avionics-integration-final.md` §4로 대체됨) | — |
| `kicad/` | 아비오닉스 배선 스키매틱 캡처(신규 — 아직 비어있음, Week 4 착수 예정) | 착수 전 |
| `firmware/reference/SingleRotorUAV/` | SolidGeek 펌웨어 원본 vendor-copy(MIT, `ORIGIN.md`에 수정 계획) — **컴파일 성공 확인**(2026-09-13) | 원본, 손대지 않음 |
| `firmware/cosmos/imu_test/` | BNO085 브링업 스케치(실험 B용) — 원본 드라이버 복사, 실물 업로드는 아직 | 작성 완료 |
| `firmware/cosmos/throttle_serial/` | DShot 스로틀 시리얼 테스트 스케치(실험 A·C용, 2초 무입력 자동0% 페일세이프 포함) | 작성 완료 |
| `firmware/singlecopter.param.md` | ArduPilot SingleCopter 파라미터 — **대안 경로**(rev C가 막힐 때) | 보존 |
| `cad/hopper_params.scad` | **CAD 정본.** EDF 실측(하우징 외경 72mm, 볼트 플랜지 없음 → 클램프 마운트) 반영, 구조버그 2건 수정 완료 | 2026-09-13 |
| `cad/measurements.md` | 실측값 기록 표 | 빈 템플릿 |
| `cad/print_parts/` | 외주 프린트용 STL — **아직 실제 파일 없음**, export 방법은 `cad/print_parts/README.md` | TODO |
| `cad/legacy/` | rev B 단계 3분할 스크립트 — `hopper_params.scad`로 대체됨, 더 이상 안 씀 | 보존만 |
| `sim/sim_stage1/hopper_aviary.py` | RL Stage 1 환경(자세 안정화, 위치 구속) — 관측 6·행동 5차원, 도메인 랜덤화 포함 | 구현·검증 완료 |
| `sim/sim_stage1/params.yaml` | 물리 상수 — **거의 전부 PLACEHOLDER**, `vane_arm_l/r`만 실측 기반 | 실측 대기 |
| `test_cartpole.py`, `test_pendulum.py` | SB3 워크플로 익히기용 | 완료 |
| `data/` | 실험 로그(CSV) | 착수 전 |
| `docs/presentation/` | 동아리 설명회 발표자료(.pptx) + 대본 | 발표 완료(9/5) |
| `club promoting material/` | 홍보용 PDF/PPTX | — |

---

## 문서 경계 — 헷갈리기 쉬운 지점

같은 걸 두 번 설명하지 않으려고 문서를 쪼갠 대신, **어디서 뭘 찾아야 하는지**를 여기 명시해둔다.
아래에 없는 질문은 문서 맵(위 표)에서 "내용" 컬럼으로 찾을 것.

| 질문 | 볼 문서 |
|---|---|
| "PID vs RL, 정확히 어떤 구조로 비교하나?" | `03-control-pipeline-design.md` §3 (여기만 — `AGENTS.md` 본문엔 원칙 한 줄만 남겨둠) |
| "RL 상태/행동 벡터가 몇 차원이지?" | `03-control-pipeline-design.md` §4 (`00-hopper-master-design.md` §9는 폐기됨) |
| "시뮬레이션 3D랑 웹 3D 뷰어랑 뭐가 다르지?" | 둘 다 — `03-control-pipeline-design.md` §1.1 과 `02-web-dashboard-design.md` §1.1에 **같은 표**가 있음(어느 쪽을 먼저 읽어도 됨) |
| "이번 주 동아리 시간에 뭘 하나?" | `docs/execution/semester-roadmap.md` (1–2주차는 `week-01-kickoff.md`) |
| "전자 배선·핀맵이 정확히 어떻게 되나?" | `01-avionics-integration-final.md` (마스터 설계도 §6.5·§7보다 이 문서가 최신) |
| "기구 형상·치수·질량예산은?" | `00-hopper-master-design.md` §3~§7 |

## 현재 상태 (최신 항목: 2026-09-18)

- **CAD**: EDF 실측 완료(9/13) — 볼트 플랜지 없는 제품이라 클램프 마운트로 설계 변경. 구조 버그 2건
  (기둥-베인링 반경 불일치, 다리 스태거 미적용) 발견·수정. `cad/hopper_params.scad`가 정본.
  **STL은 아직 export 안 됨**(OpenSCAD 로컬 미설치, `cad/print_parts/README.md`에 재현 순서 있음) —
  이전 상태 로그에 "print-ready 7종 완성"이라 적혀 있었던 건 부정확한 기록이었다.
- **펌웨어**: Arduino IDE+Teensyduino 설치, `firmware/reference/SingleRotorUAV/` 컴파일 성공
  (BasicLinearAlgebra/SerialTransfer 라이브러리 이슈 해결). `firmware/cosmos/`에 단위 테스트 스케치
  2개 작성 완료(`imu_test/`, `throttle_serial/` — 원본 드라이버 재사용, 안전장치 포함). 통합 펌웨어는
  아직. Teensy 4.0 실물 USB 업로드도 아직 — 핀헤더 미납땜.
- **소프트웨어(RL)**: SB3 CartPole-v1/Pendulum-v1 완료. `sim/sim_stage1/hopper_aviary.py` — 논문
  3장 운동방정식을 numpy로 직접 적분하는 순수 `gymnasium.Env`(gym-pybullet-drones 포기 이유는
  아래 §소프트웨어 스택). 도메인 랜덤화 포함, PPO 1회 학습 성공(파이프라인 검증 목적, 물리값이
  PLACEHOLDER라 성능 숫자 자체는 무의미). 코드-논문 대응 검토 결과 베인력 계산에 단순화 지점 발견 —
  `docs/design/modelling-notes-ch3.md` §2 참고, 실측값 넣을 때 반드시 확인.
- **Git**: `origin` = `github.com/COSMOS-Aero-Engineering/COSMOS-TVC-Hopper`(팀 공용). 로컬은 최신,
  커밋 이력 정상.
- **문서 정합성 점검(2026-09-17)**: 이전 상태 로그가 실제로 존재하지 않는 파일(`cad/print_parts/`의
  STL 7개, 예전 버전 `modelling-notes-ch3.md`)을 "완성"으로 적어놓고 있었던 걸 발견 — 이번에 바로잡음.
  **앞으로 "완료"라고 적을 땐 실제로 그 경로에 파일이 있는지 확인하고 적을 것.**
- **로드맵 공백 해소(2026-09-18)**: `docs/execution/week-01-kickoff.md`가 1–2주차까지만 있고 그 뒤가
  하나도 안 짜여 있어서 소프트웨어팀에게 "산출물이 정확히 뭐고 어떻게 진행하는지"를 설명할 수 없는
  상태였음. 두 문서로 메움: ①`docs/design/02-web-dashboard-design.md` — "웹으로 구현"이 정확히 뭔지
  (비교 대시보드 + 3D 자세뷰어, CSV 데이터 계약 포함) ②`docs/execution/semester-roadmap.md` — 3–10주차
  세션별 실행계획(KiCad 스키매틱 캡처 Week 4 포함). **§0.1에 중요 발견**: 원래 매크로 로드맵(1–3주차
  baseline 확보 가정)이 실제 진행 상황(핀헤더 납땜도 아직인 상태)과 안 맞아서, baseline 확정을 7주차로
  다시 잡음 — 부장이 "8–10주 압축 vs 학기 연장" 판단 필요(아래 다음 액션 8).
- **PID/RL 심화 + 문서 중복 정리(2026-09-18, 같은 날 2차)**: 부장이 "이미 대학급 프로젝트, `sim_stage1`은
  최종이 아니라 테스트 단계, PID·RL 다 수준급으로"라며 심화 리서치 제공 → `docs/design/03-control-pipeline-design.md`
  신설(PID/RL 아키텍처·3D 물리엔진 전환·온보드 배포·오픈소스 검증). **리서치 항목을 WebFetch/WebSearch로
  직접 검증**(PyFlyt는 유망하나 소스 미검증, Rocket-Lander는 3D가 아니라 2D Box2D로 정정, 새로 발견한
  `UrosKukovic/TVC_Self_Landing_Rocket`은 액추에이션은 다르지만 센서스택이 우리 BOM과 거의 동일해
  STAGE 3 참고가치 높음 — 상세는 03번 문서 §7). 동시에 **문서 간 중복 제거**: 이 파일의 "PID vs RL
  비교 실험 프로토콜"과 `00-hopper-master-design.md` §9(낡은 12/4차원 스펙, 실제 코드와 이미 안
  맞았음)를 03번 문서로 흡수·삭제, "문서 경계" 섹션(아래) 신설.

## 다음 액션 (부장)

1. **9/18(금) 1h + 9/19(토) 2h — 첫 세션.** 상세 진행은 `docs/execution/week-01-kickoff.md`. 요약:
   금요일은 팀 확정+착수, 토요일은 실험 A(EDF 추력곡선)·B(IMU 브링업)·C(DShot 모터제어).
2. 실험 A 진행 → `sim/sim_stage1/params.yaml`의 PLACEHOLDER(Kf 등) 실측값으로 교체
   (`docs/design/modelling-notes-ch3.md` §2·§6 대응표 보고 반영).
3. Teensy 4.0 핀헤더 납땜 → 실물 업로드 → Experiment B(IMU 브링업) 재개.
4. `cad/print_parts/`의 STL 실제로 export(`cad/print_parts/README.md` 순서대로) → 3D프린트 외주 발주.
5. 안전 계획서 지도교사 서명 — 완료 여부 미확인, **9/18 전에 확인/완료 우선**.
6. 안전스테이션 재고 확인: 밸런스충전기·삼각대·소화기.
7. FS-i6X 송신기 배터리 방식 결정 (AA 알칼라인 vs 충전식).
8. **`docs/execution/semester-roadmap.md` §0.1 읽고 일정 리스크 판단** — 8–10주 안에 압축(TC-6·TC-7
   저고도 홉을 제일 먼저 자름) vs 학기 11–12주로 연장. Week 3 세션 A에서 팀에 공유.
9. 소프트웨어팀에 `docs/design/02-web-dashboard-design.md` 공유 — "웹으로 구현"의 정확한 스펙을
   이 문서로 설명하고, `semester-roadmap.md` §3 Week 3부터 웹 뼈대(W-A) 착수 가능함을 전달.
10. 소프트웨어팀(RL 담당)에 `docs/design/03-control-pipeline-design.md` 공유 — 특히 §8-1
    "PyFlyt 소스코드 직접 검증"을 가장 먼저 맡길 것(이 결과가 나와야 Stage 2 일정을
    `semester-roadmap.md` §0.2에 배치할 수 있음).

---

## 프로젝트 배경

- 이전 학기: 로켓 모터 추력 측정 스탠드, AEROVIEW 풍동(wind tunnel) 실험 완료.
- 이번 학기 목표: 기존 엔지니어링 실험에 AI(강화학습) 요소를 접목, 대학 수준의 제어공학 실험을 자체 설계·검증.
- 동아리부장: 김민찬.

## 확정된 방향 (더 이상 재검토하지 않는 골격)

**PRJ-01: TVC 착륙 호퍼 + 강화학습.**

### 정의
- **TVC(추력벡터제어)**: 엔진/팬 추력의 방향을 기계적으로 꺾어 자세를 제어. 핀(제어면)은 공기흐름이
  있어야 작동하므로 호버링·저속 구간에서는 TVC가 유일한 수단.
- **TVC 모델로켓(상승 전용)** vs **TVC 착륙 호퍼(VTVL)**: 전자는 고체모터로 상승 중에만 TVC를 쓰고
  낙하산으로 회수. 후자는 전기 추진(EDF)으로 스로틀을 임의 조절해 이륙→호버링→강하→착륙까지 전 구간을
  제어(SpaceX Grasshopper/Starhopper, Masten Xombie 계열). **우리 프로젝트는 후자.**

### 설계 방식 — 핀 방식
EDF(전기 덕티드팬)를 고정하고 배기 기류에 제어핀(베인) 4개(서보 구동)를 움직여 방향 전환. 짐벌 방식
(모터 자체가 기울어지는 BPS.Space식)보다 기구 설계가 단순함.

### 확정 스펙 — **상세는 `docs/design/00-hopper-master-design.md`(rev C), BOM은 `docs/design/BOM-revC-teensy.md`**
여기다 BOM 표를 따로 옮겨적지 않는다 — 예전에 그렇게 했다가 rev A(70mm EDF·6S·Pixhawk) 스펙이
rev C 결정 이후에도 이 파일에 그대로 남아있어서 **실제 상태와 모순되는 사고**가 있었다(2026-09-17
발견·수정). 요약만: **64mm급 EDF(실측 하우징 외경 72mm) · 4S · Teensy 4.0 · 베인 4개.**

### 장비·기술 부족 시 축소판 (PHASE 0 → 1 → 2, 참고용 — 결국 풀빌드로 감)
- PHASE 0: 추력벡터 없이 스로틀만으로 시소 수평 유지. 참고: [ugursoydan/arduino-propellars-pid-balancing-beam](https://github.com/ugursoydan/arduino-propellars-pid-balancing-beam).
- PHASE 1: 서보 1개로 실제 추력벡터 추가(배기구 베인).
- PHASE 2: PID 자리에 RL 정책을 넣고 비교.

### 소프트웨어 스택
1. Baseline: PID 또는 LQR(둘 다 후보, §"PID vs RL" 참고) — Teensy(`firmware/cosmos/`) 자체 구현,
   또는 대안 경로로 ArduPilot SingleCopter(`firmware/singlecopter.param.md`).
2. 시뮬레이션: ~~gym-pybullet-drones~~ → **Stage 1: 자체 제작 커스텀 `gymnasium.Env`(2026-09-14 결정,
   `sim/sim_stage1/hopper_aviary.py`)**. gym-pybullet-drones의 `_physics()`/`_dynamics()`가 "모터 4개
   대칭 배치" 믹싱 공식으로 하드코딩돼 있어 모터 1개+베인 4개 구조를 넣으려면 포크 수준 수정이 필요해
   기각(소스코드 직접 확인 후 판단). → numpy로 논문 3장 운동방정식 직접 적분하는 순수 `gymnasium.Env`,
   물리상수는 `params.yaml`에 분리. PPO(stable-baselines3).
   **단, 이건 파이프라인 검증용 PoC이지 최종 목표가 아니다** — 3D 물리엔진 기반 Stage 2로 전환하는
   계획(후보 검증 포함)은 `docs/design/03-control-pipeline-design.md` §2 참고(2026-09-18 확정).
3. 실기 이식 후 baseline과 정량 비교(복원시간·오버슈트·정상상태오차).
4. RL 학습 전 SB3 공식 퀵스타트(CartPole-v1/Pendulum-v1)로 워크플로우 먼저 익힐 것 — **완료**(2026-09-13).
5. **웹 대시보드 + 3D 인터페이스**(신규, 2026-09-18 확정): PID vs RL 비교 결과와 기체 자세를 보여주는
   웹 앱 — 물리 연산은 안 하고 `data/`·`sim/` 로그를 읽는 **뷰어**다. 상세 스펙은
   `docs/design/02-web-dashboard-design.md`. RL/시뮬 트랙과 독립적으로 지금 바로 착수 가능(실측 데이터
   불필요, `docs/execution/semester-roadmap.md` Week 3 W-A부터).

### PID vs RL 비교 실험 프로토콜 — 상세는 `docs/design/03-control-pipeline-design.md`
- 원칙만: 같은 물리적 테스트 리그·외란 조건에서 **제어 알고리즘 블록만 PID/LQR ↔ RL 정책으로 교체**해
  비교. "RL이 더 낫다"를 전제하지 않고 **실제로 더 나은지를 데이터로 검증**하는 게 핵심 질문 —
  baseline이 이미 충분할 가능성도 열어둠.
- 아키텍처 옵션(직접비교 vs Residual RL)·정확한 state/action space·시뮬레이션 이식 방식·온보드 배포
  경로는 전부 `03-control-pipeline-design.md`가 정본 — **여기 다시 적지 않는다**(중복 방지, 2026-09-18
  정리).

### 안전 원칙 (필수)
- LiPo: 방화용기 충전·보관, 1C 이하 충전, 손상 시 즉시 폐기, 물리 킬스위치 상시 확보.
- 회전체: 흡배기구 그릴, 초기 테스트는 반드시 구속 상태(케이지/텐서), 보안경 착용, RC 수신기로
  수동 킬스위치 별도 확보.
- 테스트 순서: ①구속+스로틀만 → ②구속+제어핀 작동 확인 → ③구속+baseline 안정화 → ④구속+RL 비교 →
  ⑤(확장) 구속 서서히 해제.
- **지도교사 서명 전 EDF 전원 절대 안 넣음.**

### 학기 로드맵 (8–10주) — 매크로 골격, 세션 단위 배치는 `docs/execution/semester-roadmap.md`
- 1–3주차: 기구·전자팀 제작 + baseline 확보 (RL은 이 전에 시작하지 않음 — 단, RL *환경 코드* 준비와
  SB3 워크플로 학습은 병렬로 먼저 해둠, 실제로 그렇게 진행 중).
- 2–5주차(병렬): 소프트웨어팀 시뮬레이션 구축 + RL 학습.
- 6–7주차: 실기 이식 + 정량 비교.
- 8–10주차: 발표 준비 + (여유 시) 자유도 확장.

> ⚠️ **위 매크로 골격은 낙관적 가정("1–3주차에 baseline 확보")이고, 실제로는 더 뒤로 밀렸다.**
> `docs/execution/semester-roadmap.md` §0.1에서 실제 진행 상황(2026-09-18 기준 핀헤더 납땜도 아직) 기준으로
> 다시 계산한 결과 **baseline 확정 = 7주차, RL 비교 = 8주차**로 나온다 — 골격(제작→시뮬→이식→발표
> 4단계 순서)은 안 바뀌었지만 **몇 주차에 뭐가 끝나는지는 이 문단이 아니라 `semester-roadmap.md`를 봐야
> 정확하다.**

## 검토했지만 채택 안 한 대안

- **Sparrow TVC Hopper**([GitHub](https://github.com/waaaaaaaaah/sparrow-tvc-hopper)): 고체모터
  2발 순차점화 방식, CAD·PCB·코드 공개. 고체 에너지물질 규제 문제 + 조립 튜토리얼 없음 → 기각,
  "EDF 확정판 유지".
- **하이브리드/액체로켓 VTVL**: 학교 동아리 스코프 초과.
- **HAB(고고도 기구) 미션(PRJ-08)**: 현재 위치(중국 산둥성) 기준 발사 허가 문제로 보류.
- **fdiwth/tvc-drone** (GitHub): 코액시얼+짐벌 방식(우리와 다른 액추에이션), 커스텀 PCB 필요, 비행
  성공 미검증, 제작자 본인이 "따라하지 말라"고 명시 — 참고 안 함.
- **gym-pybullet-drones**: 2026-09-14 검토 후 미채택. 위 "소프트웨어 스택" §2 참고.

## 참고 아티팩트 (claude.ai 게시, Claude 계정 소유자만 열람 가능 — 다른 도구/계정에선 접근 불가)

- 전체 후보 비교 문서: `https://claude.ai/code/artifact/3444852b-6efa-4dd1-ba05-c541be3c20a6`
- PRJ-01 심화 착수 가이드: `https://claude.ai/code/artifact/514a57d1-e1b7-4f8f-b024-3048e0416c44`
- COSMOS 학습 트랙(TVC·PID·RL·ArduPilot 로드맵): `https://claude.ai/code/artifact/8f97f0db-40d6-4ecf-9f23-c923c19c1848`

## 완료된 관련 작업

- 동아리 활동계획서(`26-27_1st 상설동아리 활동계획서 (COSMOS).docx`, 레포 밖 — `~/Desktop/COSMOS 26 2nd/` 등) 작성 완료. 회원 명단은 개인정보라 비워둠 — 부장이 직접 채워야 함.
- 설명회 발표자료 + 대본(`docs/presentation/`) — 발표 완료(2026-09-05).
- 면접 예상 질문 준비 문서(`COSMOS_면접_예상질문.md`) — **레포 어디에도 실물이 없음, 로컬 다른 곳에도
  없음(2026-09-17 검색 확인). 유실된 것으로 보임 — 필요하면 다시 작성해야 함.**
- EDF 실측(2026-09-13) — 클램프 마운트로 CAD 설계 변경(`cad/hopper_params.scad`).
- 소프트웨어 트랙 착수(2026-09-13~14): 펌웨어 컴파일, SB3 퀵스타트, `sim/sim_stage1/` Stage 1 환경
  구현·검증. `docs/design/modelling-notes-ch3.md`는 2026-09-17에 (재)작성 — 예전 버전은 실물 유실 확인.

## 예상 작업 범위 (에이전트가 이 저장소에서 다룰 것)

- `firmware/cosmos/`: `firmware/reference/SingleRotorUAV/`를 우리 기체(단일 EDF)용으로 포크·수정.
- `sim/sim_stage1/`: PPO 학습, `params.yaml` 실측값 반영. Stage 2(전체 6DOF)는 실험 A 이후.
- `cad/hopper_params.scad`: 실측값 갱신, STL export(`cad/print_parts/`).
- `docs/`: 실험 노트, 안전 점검표, 물리 모델링 정리. **새 상태를 "완료"로 적기 전에 실제 파일이
  그 경로에 있는지 확인할 것** — 이번에 그렇지 않은 사례를 여럿 발견했다.

## 아직 열려 있는 질문

- 회원 명단(학년·학번·연락처·위챗) — 부장이 직접 채워야 함.
- 최종 자유비행(구속 해제) 도전 여부 — STAGE 3 결과를 본 뒤 결정.
- 예산 구체 금액, 팀 구성 인원 및 실력 분포 — 부장 액션.
- 3D프린트 외주업체 미확정, 안전스테이션 재고 미확인, FS-i6X 배터리 방식 미결정.
- `COSMOS_면접_예상질문.md` 유실 — 다시 작성 필요한지 확인.
- CONTRIBUTING.md를 따로 만들지 여부 — 지금은 `README.md`의 "부원 퀵스타트/협업 규칙/트러블슈팅"
  섹션이 그 역할을 이미 하고 있어서 안 만듦(내용 중복 방지). GitHub가 자동으로 찾는 파일명이라는
  이점은 있지만, 외부 기여자가 없는 학교 동아리 저장소라 지금은 실익이 적다고 판단 — 나중에 필요해지면
  `README.md`의 해당 섹션을 그대로 옮겨서 만들면 됨.
