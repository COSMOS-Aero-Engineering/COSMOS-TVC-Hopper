# COSMOS — TVC 착륙 호퍼 + 강화학습 프로젝트

국제학교(청도대원학교) 항공우주공학 동아리 COSMOS의 26-27학년도 1학기 프로젝트. 이 파일은 Cowork/Codex 세션이 이어받기 위한 컨텍스트 문서다. 새 세션을 열 때 이 파일을 먼저 읽을 것.

**이 파일은 Codex.ai "COSMOS" 프로젝트와 로컬 저장소(`C:\Users\mimin\Desktop\cosmos-tvc-hopper\AGENTS.md`) 양쪽에 동일한 내용으로 유지한다 — 둘이 따로 놀지 않도록 앞으로 한쪽만 고치지 말고 항상 같이 갱신할 것.**

**마지막 갱신: 2026-09-14.**

---

## 문서 맵 (파일 위치 안내)

| 경로 | 내용 |
|---|---|
| `docs/design/00-hopper-master-design.md` | 마스터 설계도 rev C — 아키텍처·치수·질량·전자·펌웨어·시험카드·리스크 |
| `docs/design/research-open-source-references.md` | rev C 근거 리서치 (SolidGeek·Bresciani/PX4·기타 비교) |
| `docs/design/BOM-revC-teensy.md` | 구매 리스트 (현행, ₩310–530k) |
| `docs/design/BOM.md` | 구 BOM (rev B) — 추진·구조·안전 항목만 유효, FC 계통은 rev C로 대체 |
| `docs/design/general-arrangement.svg` | 기체 개략 배치도 |
| `docs/design/references/Jacobsen2021_*.pdf` | SolidGeek 논문 전문 (제작·제어 이론의 1차 자료) |
| `docs/design/modelling-notes-ch3.md` | 논문 3장(Modelling) 정리 — 운동방정식·베인 공력식 (한국어 재정리본) |
| `docs/execution/week-01-kickoff.md` | 1–2주차 마스터 실행계획 — 타임라인·부장 준비·부품 전체·세션 진행 |
| `docs/execution/procurement-review.md` | 부장 구글시트 행별 검토 (✅/⚠️/❌/➕) |
| `docs/execution/bench-wiring.svg` | 벤치 배선도 (Week 1 브링업 → Week 2 확장) |
| `firmware/reference/SingleRotorUAV/` | SolidGeek 펌웨어 원본 vendor-copy (MIT, `ORIGIN.md`에 수정 계획) — 컴파일 성공 확인(2026-09-13) |
| `firmware/singlecopter.param.md` | ArduPilot SingleCopter 파라미터 — PID 베이스라인 경로 |
| `cad/hopper_params.scad` | 파라메트릭 CAD 본체 (rev C, EDF 클램프 마운트 방식) |
| `cad/print_parts/` | 외주 프린트용 STL 7종 |
| `sim/sim_stage1/hopper_aviary.py` | RL Stage 1 커스텀 환경(자세 안정화, 위치 구속) + 도메인 랜덤화 |
| `sim/sim_stage1/params.yaml` | 물리 상수(PLACEHOLDER) + 도메인 랜덤화 설정 |
| `sim/sim_stage1/train.py`, `sanity_check.py` | PPO 학습·환경 점검 스크립트 |
| `test_cartpole.py`, `test_pendulum.py` | Stable-Baselines3 워크플로우 익히기용 (완료) |
| `docs/presentation/` | 동아리 설명회 발표자료(.pptx) + 대본 |

## 현재 진행 상태 요약 (2026-09-14 기준)

- **CAD**: EDF 실측 완료 — 볼트 플랜지 없는 제품으로 확인되어 클램프(collar clamp) 마운트로 설계 변경. 구조 버그 2건(기둥-베인링 반경 불일치, 다리 스태거 미적용) 발견·수정. print-ready 파츠 7종 완성, 외주 발주는 아직 안 함.
- **펌웨어**: Arduino IDE+Teensyduino 설치, SingleRotorUAV 펌웨어 컴파일 성공(BasicLinearAlgebra/SerialTransfer 라이브러리 이슈 해결). 실제 Teensy 4.0 USB 업로드는 아직 — 핀헤더 미납땜 상태로 보류 중.
- **소프트웨어(RL)**: Stable-Baselines3 CartPole-v1/Pendulum-v1 퀵스타트 완료. 논문 3장(Modelling) 정리 완료. `sim/hopper_aviary.py` Stage 1(위치 구속·자세 제어만) 커스텀 환경 + 도메인 랜덤화(Jxx/Jyy/Jzz, 베인 모멘트암, Kf, 무게중심-추력축 오프셋) 구현·검증 완료.
- **RL 시뮬레이션 프레임워크 변경(2026-09-14)**: 원래 계획했던 gym-pybullet-drones는 검토 후 미채택 — 아래 "소프트웨어 스택" §2 참고.
- **Git**: 로컬 저장소에 커밋 이력 있음(리모트 `origin` 연결됨). 단, 최근 변경분(펌웨어 수정, CAD 업데이트, `sim/` 신규 파일들)이 실제로 커밋됐는지는 이 세션에서 재확인 필요 — 부장이 `git status`로 확인 후 커밋 권장.

## 다음 액션 (부장)

1. 최근 변경사항 git 커밋 (펌웨어 fix, CAD rev, sim/ 신규 파일)
2. 3D프린트 외주업체 확정 + 발주 (print-ready 파츠 7종 이미 완성됨)
3. 안전 계획서 지도교사 서명 (완료 여부 미확인 — 하드 데드라인이었던 9/15 지났으면 우선 확인)
4. 안전스테이션 재고 확인: 밸런스충전기·삼각대·소화기
5. FS-i6X 송신기 배터리 방식 결정 (AA 알칼라인 vs 충전식)
6. Teensy 4.0 핀헤더 납땜 (인두기 접근 가능해지는 대로) → Experiment B(IMU 브링업) 재개
7. 실험 A(EDF 추력곡선) 진행 → `sim/params.yaml`의 PLACEHOLDER 값(Jxx/Jyy/Jzz, CLα/CD0, Kf) 실측값으로 교체

---

## 프로젝트 배경

- 이전 학기: 로켓 모터 추력 측정 스탠드, AEROVIEW 풍동(wind tunnel) 실험 완료.
- 이번 학기 목표: 기존 엔지니어링 실험에 AI(강화학습) 요소를 접목, 대학 수준의 제어공학 실험을 자체 설계·검증.
- 동아리부장: 김민찬.

## 확정된 방향 (더 이상 바꾸지 않는 골격)

**PRJ-01: TVC 착륙 호퍼 + 강화학습**을 확정판으로 채택함. 이 밑의 세 가지(정의·설계 방식·BOM)는 계속 재검토하지 않기로 함 — 세부 스펙만 실측 후 미세조정.

### 정의
- **TVC(추력벡터제어)**: 엔진/팬 추력의 방향을 기계적으로 꺾어 자세를 제어. 핀(제어면)은 공기흐름이 있어야 작동하므로 호버링·저속 구간에서는 TVC가 유일한 수단.
- **TVC 모델로켓(상승 전용)** vs **TVC 착륙 호퍼(VTVL)**: 전자는 고체모터로 상승 중에만 TVC를 쓰고 낙하산으로 회수(BPS.Space Signal R2/Alpha, OpenRTVC, K-9 TVC V8 등 대부분이 여기 속함). 후자는 전기 추진(EDF)으로 스로틀을 임의 조절해 이륙→호버링→강하→착륙까지 전 구간을 제어(SpaceX Grasshopper/Starhopper, Masten Xombie, bribro12의 SpaceX-inspired EDF rocket). **우리 프로젝트는 후자.**

### 설계 방식 — 핀 방식 채택
EDF(전기 덕티드팬)를 고정하고 배기 기류에 제어핀 4개(서보 구동)를 움직여 방향 전환. 짐벌 방식(모터 자체가 기울어지는 BPS.Space식)보다 기구 설계가 단순하고, ArduPilot의 "SingleCopter" 프레임을 그대로 활용 가능해 PID baseline 구축이 쉬움.

### 확정 BOM (bribro12의 실제 완성/비행 빌드 기준)
| 분류 | 부품 | 비고 |
|---|---|---|
| 추진 | 70mm EDF + 브러시리스 모터(2300KV) | 6S 기준 약 2.5kg 추력 |
| ESC | 80A급 브러시리스 ESC | BEC 내장, 2–6S |
| 배터리 | 6S 1000mAh 70C LiPo | 순간전류 중요 |
| 제어핀 서보 | 9g 금속기어 서보 ×4 | 백래시 적은 제품 |
| 비행 컨트롤러 | Pixhawk 4 + ArduPilot v4.0.4 (SingleCopter) | 저예산 대안: Arduino/Teensy + 자체 PID |
| 수신기 | Spektrum DSM2/DSM-X 호환 | 수동 안전 개입용 필수 |
| 구조재 | PLA 3D프린팅 프레임 | K-9 TVC Hopper Test Vehicle의 공개 STL 활용 가능 (CAD 설계 불필요) |

**단순화 포인트**: 원 빌드는 착륙다리 전개용 서보 4개+보조 Arduino Nano 보드가 추가되지만, 우리 연구 질문(구속 상태 자세 안정화 비교)엔 불필요 — 고정형 다리로 대체해 생략.

### 장비·기술 부족 시 축소판 (PHASE 0 → 1 → 2)
- PHASE 0: 추력벡터 없이 스로틀만으로 시소 수평 유지. 참고: [ugursoydan/arduino-propellars-pid-balancing-beam](https://github.com/ugursoydan/arduino-propellars-pid-balancing-beam) (완전한 코드·회로도·PID 게인값 공개).
- PHASE 1: 서보 1개로 실제 추력벡터 추가(배기구 베인).
- PHASE 2: PID 자리에 RL 정책을 넣고 비교.
- 장비 대체: 3D프린터 없음→나무/아크릴+기성 팬틸트 브라켓, 납땜 없음→브러시드 모터+L298N/TB6612 드라이버.

### 소프트웨어 스택
1. Baseline: ArduPilot SingleCopter 또는 자체 Arduino+MPU6050 PID 루프.
2. 시뮬레이션: ~~gym-pybullet-drones~~ → **자체 제작 커스텀 `gymnasium.Env`로 변경(2026-09-14 결정)**.
   gym-pybullet-drones의 `_physics()`/`_dynamics()`가 "모터 4개 대칭 배치" 믹싱 공식으로 하드코딩돼있어
   우리처럼 모터 1개+베인 4개 구조를 넣으려면 라이브러리 내부를 사실상 통째로 새로 써야 함(포크 수준,
   확장 지점 아님) — 소스코드 직접 확인 후 판단. 도메인 랜덤화도 그 라이브러리엔 기본 내장이 아니라
   원래도 직접 구현해야 하는 부분이었음. Jacobsen 논문·bribro12 빌드·K-9 TVC Hopper 등 참고 프로젝트
   중 이 기체 형태(EDF 1개+베인 4개)로 공개된 시뮬레이션 코드는 존재하지 않음(직접 검색 확인).
   → `sim/hopper_aviary.py`: numpy로 논문 3장 운동방정식 직접 적분하는 순수 gymnasium.Env(Stage 1,
   위치 구속·자세 제어만). `sim/params.yaml`에 물리상수(전부 PLACEHOLDER, 실측 전) + `domain_rand`
   설정(Jxx/Jyy/Jzz, 베인 모멘트암, Kf를 매 에피소드 ±비율로 무작위화 + 무게중심-추력축 오프셋을
   잔류 토크로 반영)을 분리해둬서, 실측값이 나와도 코드는 안 건드리고 params.yaml만 교체하면 됨.
   PPO(stable-baselines3)로 학습, 3D 시각화는 학습에 불필요(필요하면 나중에 PyBullet/MuJoCo를
   기존 state 위에 얇은 시각화 레이어로만 얹는 것 고려 — 물리 엔진 자체를 학습에 쓰진 않음).
3. 실기 이식 후 PID baseline과 정량 비교(복원시간·오버슈트·정상상태오차).
4. RL 학습 전 Stable-Baselines3 공식 퀵스타트(CartPole-v1/Pendulum-v1)로 워크플로우 먼저 익힐 것 — 완료(2026-09-13, CartPole/Pendulum 둘 다 실행 성공).

### PID vs RL 비교 실험 프로토콜
- 같은 물리적 테스트 리그(구속 상태 테스트 스탠드), 같은 외란 조건(수동으로 일정 각도 기울이기 또는 목표 자세 스텝 변경)을 고정해두고, **제어 알고리즘 블록만 PID ↔ RL 정책으로 교체**해가며 두 번 돌려 비교.
- PID 구현 경로: ① ArduPilot 사용 시 PID는 이미 내장되어 있으므로 Kp/Ki/Kd 게인만 Mission Planner 등 지상국에서 튜닝. ② Arduino+MPU6050 저예산 경로면 직접 코드 작성(자이로 각도 오차 → P/I/D 항 계산 → 서보 보정값).
- RL 정책은 커스텀 시뮬레이션(`sim/hopper_aviary.py`, 위 소프트웨어 스택 §2 참고)에서 질량·관성·무게중심을 매 에피소드 랜덤화해 학습 후 동일 하드웨어에 이식. **시뮬레이션은 학습 단계(비행 전)에서만 쓰이고, 실제 비행 중에는 관여하지 않음** — 실비행 시 PID·RL 모두 픽스호크 위에서 동일하게 EKF가 계산한 자세값을 입력받아 서보를 출력.
- PID와 RL의 근본 차이: 둘 다 "상태→서보값" 함수라는 점은 같지만, PID는 사람이 공식과 게인 3개를 직접 정하는 반면 RL은 신경망이 시뮬레이션에서 수만 번 시행착오를 거치며 스스로 파라미터를 고쳐나간 결과물 — 이 자기수정 과정 자체가 "학습(AI)"의 정의.
- 이 프로젝트의 핵심 질문은 "RL이 더 낫다"를 전제하지 않고 "실제로 더 나은지"를 데이터로 검증하는 것 — PID가 이미 충분할 가능성도 열어둠.

### 안전 원칙 (필수)
- LiPo: 방화용기 충전·보관, 1C 이하 충전, 손상 시 즉시 폐기, 물리 킬스위치 상시 확보.
- 회전체: 흡배기구 그릴, 초기 테스트는 반드시 구속 상태(케이지/텐서), 보안경 착용, RC 수신기로 수동 킬스위치 별도 확보.
- 테스트 순서: ①구속+스로틀만 → ②구속+제어핀 작동 확인 → ③구속+PID 안정화 → ④구속+RL 비교 → ⑤(확장) 구속 서서히 해제.

### 학기 로드맵 (8–10주)
- 1–3주차: 기구·전자팀 제작 + baseline PID 확보 (RL은 이 전에 시작하지 않음).
- 2–5주차(병렬): 소프트웨어팀 시뮬레이션 구축 + RL 학습.
- 6–7주차: 실기 이식 + 정량 비교.
- 8–10주차: 발표 준비 + (여유 시) 자유도 확장.

## 검토했지만 채택 안 한 대안 (참고용, 방향 변경 아님)

- **Sparrow TVC Hopper**([GitHub](https://github.com/waaaaaaaaah/sparrow-tvc-hopper)): 고체모터(Estes D12) 2발 순차점화(상승+착륙감속) 방식. CAD(STEP/Onshape)·PCB(KiCad)·코드 전부 공개, 실비행 영상 있음. 단, 고체 에너지물질이라 현재 위치 기준 구매·수입·발사 규제 확인 필요 + 조립 튜토리얼 없음(JOURNAL.md는 설계일지일 뿐). 사용자가 "EDF 확정판 유지"로 명시적으로 결정함.
- **하이브리드/액체로켓 VTVL**: 물리적으로 진짜 스로틀·재점화가 가능한 유일한 화학추진 방식이지만, 가압 산화제·연소·발사장·모터 인증 등 학교 동아리 스코프를 크게 초과. 참고: Half Cat Rocketry Mojave Sphinx(오픈소스 액체로켓, 상승전용), VoidPropulsion JACKALOPE(개발중, 미공개).
- **HAB(고고도 기구) 미션(PRJ-08)**: 현재 위치(중국 산둥성) 기준 발사 허가·저고도 공역 규제로 보류. PRJ-13(자율 로버)/PRJ-14(연 기반 대기 프로파일링)이 허가 불필요 대체안.
- **gym-pybullet-drones (RL 시뮬레이션 프레임워크)**: 2026-09-14에 검토 후 미채택. 위 "소프트웨어 스택" §2 참고.

## 참고 아티팩트 (Cowork에서 게시, 계정 전체에서 접근 가능)

- 전체 후보 비교 문서: `https://Codex.ai/code/artifact/3444852b-6efa-4dd1-ba05-c541be3c20a6`
- PRJ-01 심화 착수 가이드(정의·BOM·안전·로드맵·저예산 오픈소스 레퍼런스 전부 포함): `https://Codex.ai/code/artifact/514a57d1-e1b7-4f8f-b024-3048e0416c44`
- COSMOS 학습 트랙(TVC·PID·RL·ArduPilot을 단계별로 익히기 위한 한국어/영어 영상·자료 로드맵): `https://Codex.ai/code/artifact/8f97f0db-40d6-4ecf-9f23-c923c19c1848`

## 완료된 관련 작업

- 동아리 활동계획서(`2627_1st 상설동아리 활동계획서 COSMOS`) 작성 완료 — 동아리 소개·활동 목표·주요 활동 내용(로드맵 5단계) 채워 넣음. 회원 명단은 개인정보라 부장이 직접 채워야 함(비워둠).
- 발표회용 6분 분량 한국어 발표 스크립트 + 심화 설명(픽스호크/아두파일럿, RL 구현 4단계) + 예상 질의응답 작성 완료. 발표 진행됨(2026-09-05 기준).
- 발표 후 이어지는 면접 예상 질문 준비 문서 작성 완료(`COSMOS_면접_예상질문.md`) — 프로젝트 개념, 설계 결정 이유(Sparrow·하이브리드로켓·CAD 미사용 이유), 일정·예산 실현가능성, 안전, 동아리 운영/개인 질문 포함. 예산 구체 금액과 팀 구성/개인 경험 관련 질문은 부장이 직접 채워야 하는 빈칸으로 남겨둠.
- EDF 실측 완료(2026-09-13) — 볼트 플랜지 없는 제품으로 확인되어 클램프 마운트로 CAD 설계 변경, print-ready 파츠 7개 외주용으로 완성.
- 소프트웨어 트랙 착수(2026-09-13~14): Arduino IDE+Teensyduino 설치, SingleRotorUAV 펌웨어 컴파일 성공(BasicLinearAlgebra/SerialTransfer 라이브러리 이슈 해결). Stable-Baselines3 CartPole-v1/Pendulum-v1 퀵스타트 완료. 논문 3장(Modelling) 정리 문서 작성(`docs/design/modelling-notes-ch3.md`). `sim/hopper_aviary.py` Stage 1(자세 안정화, 위치 구속) 커스텀 환경 + 도메인 랜덤화 구현 및 검증 완료.

## 이 Code 세션에서 다룰 것으로 예상되는 작업

- `firmware/`: Arduino/ESP32 PID 컨트롤러 코드 (PHASE 0→1), 이후 ArduPilot 파라미터 설정.
- `sim/`: 커스텀 `gymnasium.Env`(`hopper_aviary.py`, gym-pybullet-drones 아님 — 위 §2 참고) + PPO 학습 스크립트(`train.py`) + 도메인 랜덤화 설정(`params.yaml`). Stage 1(위치 구속·자세만) 완료, Stage 2(전체 6DOF)는 실험 A 데이터 확보 후 예정.
- `cad/`: EDF·서보 마운트용 OpenSCAD 파라메트릭 스크립트 (`hopper_params.scad`). CAD를 처음부터 프리핸드로 설계하지 않는 것이 원칙 — 기존 STL 재사용 또는 코드 기반 파라메트릭 설계 우선.
- `docs/`: 이 프로젝트의 실험 노트, 안전 점검표, 발표자료 초안, 물리 모델링 정리(`docs/design/modelling-notes-ch3.md`).

## 아직 열려 있는 질문

- 회원 명단(학년·학번·연락처·위챗)은 개인정보라 동아리 활동계획서에서 비워둠 — 부장이 직접 채워야 함.
- 최종 자유비행(구속 해제) 도전 여부는 STAGE 3 결과를 본 뒤 결정.
- 예산 구체 금액, 팀 구성 인원 및 실력 분포 — 면접 준비 문서에 빈칸으로 남겨둠, 부장이 채워야 함.
- 3D프린트 외주업체 미확정, 안전스테이션(밸런스충전기·삼각대·소화기) 재고 미확인, FS-i6X 송신기 배터리 방식 미결정 — 모두 부장 액션 아이템.
- 로컬 저장소의 최근 변경사항(펌웨어 수정, CAD rev, sim/ 신규 파일) 커밋 여부 재확인 필요.
