# COSMOS — TVC 착륙 호퍼 + 강화학습 프로젝트

청도대원학교 항공우주공학 동아리 COSMOS의 26–27학년도 1학기 프로젝트다. 이 파일은 이 저장소에서 일하는 **모든 AI 에이전트(Claude Code·Codex·Cursor 등)와 사람을 위한 정본 컨텍스트**다. 새 세션은 이 파일부터 읽는다. `CLAUDE.md`는 이 파일로 보내는 안내문일 뿐이고, 챗 사이드바 등에 붙여 둔 복사본은 정본이 아니다. 고칠 때는 이 파일을 고친 뒤 복사본을 덮어쓴다.

사람용 개발환경 세팅·협업 절차·트러블슈팅은 [`README.md`](README.md)에 있다. 이 파일은 "왜, 무엇을, 지금 어디까지", README는 "지금 무엇을 타이핑하나"다.

**마지막 갱신: 2026-10-16.**

---

## 1. 프로젝트 한눈에

**무엇을 만드나.** 전기 덕티드팬(EDF) 하나의 추력으로 뜨고, 배기 아래 베인(제어핀) 4개를 서보로 꺾어 자세를 잡는 소형 수직이착륙 호퍼다. SpaceX식 착륙 로켓의 자세 제어를 안전한 크기로 재현한다.

**무엇을 증명하나.** 같은 구속 시험대·같은 외란 조건에서 **제어기 블록만** PID/LQR ↔ 강화학습(RL) 정책으로 바꿔 끼워 복원시간·오버슈트·정상오차를 비교한다. "RL이 낫다"를 전제하지 않고 데이터로 확인한다.

**기체 숫자** (근거 문서와 함께)

| 항목 | 값 | 근거 |
|---|---|---|
| 추진 | 64 mm급 EDF(하우징 외경 실측 72 mm), 4S LiPo 1300 mAh, 60 A ESC(DShot) | 마스터 설계 §5.1, `cad/hopper_params.scad` |
| 제어면 | 반경 방향 평판 베인 4개(r 4~41 mm, 시위 25 mm), 서보 4개 | 01 문서 §7.4, §12-5 |
| 비행 컴퓨터·센서 | Teensy 4.0, BNO085 IMU(쿼터니언 내장 계산) | 01 문서 §2 |
| 전체 질량 | 약 735 g(추정), TWR 약 1.77(정적 추력 1300 gf 사양 기준) | 01 문서 §8.1 |
| 무게중심 목표 | 배기면 위 **60~75 mm**(계산 약 68 mm). 마스터 §5.3의 140~180 mm는 도달 불가로 정정됨 | 01 문서 §8.4 |
| 베인 피벗 / 토크 팔 | 피벗 z = −36 mm, 롤·피치 토크 팔 ≈ 104 mm | 01 문서 §7.7, §8.4 |

**좌표계** (01 문서 §1, 전 팀 공통). +X = FWD(0°, 베인1·서보1), +Y = LEFT(90°, 베인2), −X = AFT(베인3), −Y = RIGHT(베인4), +Z = 위(흡기 쪽), z = 0은 EDF 배기면. 다리·기둥은 45° 계열. 롤 = X축, 피치 = Y축, 요 = Z축 회전. 시뮬레이션과 웹 뷰어도 이 정의를 쓴다.

**전체 흐름**

```
CAD(cad/) ──질량·치수──▶ 시뮬레이션 상수(sim/sim_stage1/params.yaml)
                              │
실험 A(EDF 추력곡선) ──Kf──────┤
                              ▼
               Stage 1 시뮬레이션(gymnasium, numpy) ──PPO 학습──▶ RL 정책
                              │ export_episode.py                   │
                              ▼                                     ▼
펌웨어(firmware/cosmos/) ──CSV 계약(02 문서 §4)──▶ 웹 3D 뷰어(web/) ◀── 비교 결과
   Teensy + IMU + DShot ESC + 서보 → 구속 시험대에서 PID vs RL (시험 카드 TC-0~TC-5)
```

**팀** (부원 7명, 리뷰·머지 권한은 부장·차장 둘)

| 이름 | GitHub | 담당 |
|---|---|---|
| 김민찬 (부장) | `MINBBBB1201` | CAD·총괄, 발주·실험 계획 |
| 김준원 (차장) | `junwonkim07` | 시뮬레이션·RL |
| 박지훈 | `qkrwlgns7275` | 실측·CAD |
| 이민우 | `kanedesu` | KiCad 회로도 |
| 김시우 | `siwoo090804-web` | 펌웨어(IMU) |
| 권재후 | `kwon6789` | 펌웨어(DShot·로그 형식) |
| 김민지 | `iammji9` | 웹·3D·데이터 |

## 2. 현재 상태 (2026-10-16)

**된 것 (확인 범위 포함)**
- CAD 정본 `cad/hopper_params.scad`, 외주용 STL 9종 export(9/18, 검증 `echo()` 통과). STL은 `.gitignore` 대상이라 저장소에는 없다.
- Teensy 업로드 성공(10/15). 안 되던 원인은 **충전 전용 USB 케이블**이었다. BNO085를 4선 I2C로 0x4B에서 인식하고 자세값 출력 확인(`firmware/cosmos/imu_test_i2c`). SPI 스케치(`imu_test`)는 빌드만 확인.
- DShot 벤치 펌웨어(`throttle_serial`): arm 게이트, 상한 DShot 600, 램프, 워치독, 비상정지. **ESC 없이 Teensy에서만 확인**(#19). 실물 시험은 #24.
- Stage 1 시뮬레이션(`sim/sim_stage1`)과 PPO 파이프라인, 에피소드를 웹 CSV로 내보내는 `export_episode.py`(#23).
- KiCad 회로도 생성(20부품, 30넷). 실제 ERC는 아직 못 돌림.
- 웹 뷰어 뼈대 `web/`(Vite + Three.js, 빌드 통과, 10/16). 축 변환은 판정 전.

**막혀 있는 것**
1. **실험 A(EDF 추력곡선) 미실시.** `Kf`(추력 상수)가 잠정값 `1.1e-6`(10 N 역산)이다.
2. **시뮬레이션 베인 제어력 버그(#21).** 도메인 랜덤화를 켜면 어떤 정책도 1초 안에 넘어진다. 유력 원인: `CLalpha`가 논문에서 **도(deg)당** 값인데 코드는 라디안 각도에 곱한다(57.3배 작음, 추정). `vane_arm_l`도 48 mm로 잘못 들어가 있다(≈104 mm여야 함). 고치기 전에는 **RL 결과를 성능으로 해석하지 않는다.** 근거와 후보 시험: [`docs/tasks/27-sim-vane-authority.md`](docs/tasks/27-sim-vane-authority.md).
3. **3D프린트 외주 미발주**(10/14 기준). 조립 일정 전체가 여기에 걸려 있다.
4. **IMU Yaw**가 돌린 만큼 안 변한다. 스케치가 지자기를 쓰는 Rotation Vector 모드인데 설계는 자력계를 안 쓰기로 했다. Game Rotation Vector로 비교 예정(#28).

## 3. 지금 할 일

- **사람별 현재 과제의 단일 기준**: [`docs/learning/README.md`](docs/learning/README.md)의 "지금 할 일" 표.
- **자세한 지시**: 팀별 PRD 이슈 #26(CAD·KiCad), #27(시뮬레이션), #28(펌웨어), #29(웹). 기한 10/24, 중간 점검 10/17.
- **어디서부터 손댈지**: [`docs/tasks/`](docs/tasks/README.md)의 착수 초안. 실행되는 뼈대 코드, 기록 양식, 미리 돌려 본 결과가 있다.
- 처음 온 부원은 학습 안내의 "처음 20분"과 첫 과제부터.

## 4. 작업 규칙: 브랜치·PR (2026-09-18 확정)

1. `main`에 직접 커밋·push하지 않는다. `git switch -c <태그>/<짧은-설명>`. 태그: `cad`, `fw`, `sim`, `web`, `kicad`, `data`, `docs`, `infra`.
2. PR을 올리고 리뷰어를 지정한다. 리뷰·머지 권한은 김민찬(`MINBBBB1201`)과 김준원(`junwonkim07`)뿐이다. 둘은 CI 초록불과 변경을 직접 확인한 뒤 자기 PR도 머지할 수 있다. 다른 부원은 둘 중 한 명의 Approve가 필요하다.
3. 머지는 squash: `gh pr merge --squash --delete-branch`.
4. PR 본문은 [`.github/pull_request_template.md`](.github/pull_request_template.md)를 채운다. **실제로 해 본 확인만 체크**하고 범위를 "빌드만 확인", "ERC만 확인", "ESC 없이 Teensy에서만 확인"처럼 쓴다. 확인 못 한 값은 `확인 필요`.
5. CI(`.github/workflows/ci.yml`): sim 검사(`python tasks.py check`)·학습 자료 링크 검사, 펌웨어 3종(`imu_test`, `imu_test_i2c`, `throttle_serial`) PlatformIO 빌드. 웹은 아직 CI에 없다.
6. **AI는 머지하지 않는다.** PR 생성과 CI 확인까지는 진행해도 된다.

왜: 깨진 코드가 곧바로 모두의 `git pull`에 실려 가는 걸 막고, 되돌릴 단위를 PR 하나로 만들기 위해서다.

## 5. 일하는 방식: 팀별 PRD와 이해 먼저 (2026-10-16)

- 할 일은 GitHub 이슈의 팀별 PRD로 받는다(라벨 `prd` + 영역 라벨). PRD는 기한·담당·목표(판정 형태)·배경(숫자)·판정 기준·사람별 작업·결과물(PR 제목)·제외·협업·볼 것(자료실 ID)·진행 보고로 쓴다.
- **이해 먼저.** 바로 구현하지 않는다. ① 프로젝트에서 어떤 의미인지 ② 잘못되면 무엇이 깨지는지 ③ 알아야 할 개념을 자기 말로 PRD 댓글에 쓴 뒤 시작한다.
- **착수 초안을 같이 준다.** PRD만 주고 "이거 해"라고 하지 않는다. `docs/tasks/`에 현재 상태·용어·미리 만든 것·첫 30분·이어서 할 일·확인 못 한 것을 둔다. 새 PRD를 만들면 착수 문서도 같이 만든다.
- **진행 보고**는 PRD 댓글로 "한 일(숫자) / 올린 PR 번호 / 다음 할 일" 세 줄.
- 부품 사양·핀 번호·치수·물리 상수를 추측하지 않는다. 데이터시트(링크와 쪽), 실측값, CAD 변수를 근거로 쓴다. 실물로 확인하지 않은 동작을 "동작함"이라고 하지 않는다. "완료"라고 적기 전에 그 경로에 파일이 실제로 있는지 확인한다.

## 6. 부원이 AI에게 자기 과제를 물을 때

1. **이름부터 확인한다.** "지금 할 일" 표에서 그 사람 행을 찾고, 그 행의 PRD 이슈에서 담당 절을 읽는다. 표 날짜가 오래됐거나 2절 현재 상태와 다르면 먼저 말하고 부장·차장에게 확인하라고 한다.
2. **근거를 직접 연다.** `gh issue view <번호> -R COSMOS-Aero-Engineering/COSMOS-TVC-Hopper`, 그리고 `docs/tasks/`의 착수 문서와 거기 연결된 파일. 기억이나 일반 지식으로 대신하지 않는다.
3. **설명은 쉬운 한국어로**, 담당 안내서(`docs/learning/tracks/`) 수준에서 시작한다. 전문 용어는 처음 나올 때 풀어서. 입력·출력·정상 결과를 먼저 보여 주고 부원이 자기 말로 다시 설명하게 한다. 범위가 큰 지시("PID 구현")를 그대로 넘기지 않는다.
4. **작은 단위로 실행하고 기록하게 한다.** 측정값·로그는 `data/`, 코드·문서는 브랜치와 PR. Git 명령은 대신 실행하되 명령마다 한 줄로 설명한다. `main` push, force push, `reset --hard`, 여러 파일 삭제는 하지 않는다.

AI가 지킬 선:
- EDF·ESC에 배터리 전원을 넣는 단계는 안내만 한다. 부장 입회와 7절 안전 원칙 확인 전에는 진행하라고 하지 않는다. 첫 회전 시험은 팬 분리 또는 스탠드 볼트 고정 상태에서만(#24).
- 배선은 실물 모듈 실크와 01 문서를 대조한다. GY-BNO08X 모듈은 한 핀에 이름이 여러 개다: SDA/MISO/TX = MISO, ADDR/MOSI = MOSI, SCL/SCK/RX = SCK.
- Windows PowerShell 5.1에서는 `&&`가 안 된다. `;`를 쓴다. Teensy가 안 잡히면 데이터 전송용 USB 케이블인지부터 본다.

## 7. 안전 원칙 (필수)

- **지도교사 서명 전 EDF 전원 절대 안 넣음.**
- LiPo: 방화용기 충전·보관, 1C 이하 충전, 손상 시 즉시 폐기, 물리 킬스위치 상시 확보.
- 회전체: 흡배기구 그릴, 초기 시험은 반드시 구속 상태(케이지/텐서), 보안경, RC 수신기로 수동 킬스위치 별도 확보. 사람은 배기 축선 밖.
- 시험 순서: ① 구속 + 스로틀만 → ② 구속 + 베인 동작 확인 → ③ 구속 + baseline 안정화 → ④ 구속 + RL 비교 → ⑤ (확장) 구속 서서히 해제. 첫 전원 절차는 01 문서 §10(P1~P8).

## 8. 문서 맵

| 경로 | 내용 | 상태 |
|---|---|---|
| `docs/learning/README.md` | 부원 입구: "지금 할 일" 표, 담당별 첫 실습, 자료실(글·영상 64개), AI 질문 문장 | 현행, 10/16 |
| `docs/tasks/` | PRD별 착수 초안(현재 상태·첫 30분·이어서 할 일·확인 못 한 것) | 신규, 10/16 |
| `docs/design/00-hopper-master-design.md` | 마스터 설계 rev C: 아키텍처·치수·질량 예산·시험 카드(§11)·리스크. **CG 목표와 질량 합계는 01 문서가 정정함** | 현행(일부 01로 대체) |
| `docs/design/01-avionics-integration-final.md` | 아비오닉스·배선·기계 통합 rev C.1: 좌표계, Teensy 핀맵, 전원, 빵판·만능기판 배치, z 배치, 질량·CG 재계산, 조립·브링업 절차. 마스터와 충돌하면 이 문서가 최신(§12) | 현행 |
| `docs/design/02-web-dashboard-design.md` | 웹 대시보드·3D 뷰어 설계, **CSV 데이터 계약(§4)**, 개발 단계 W-A~W-F, 기술 스택 | 현행 |
| `docs/design/03-control-pipeline-design.md` | PID/RL 구조, 3D 물리엔진 전환(Stage 2), State/Action, 도메인 랜덤화, 온보드 배포. **PID vs RL의 단일 정본** | 현행 |
| `docs/design/modelling-notes-ch3.md` | 논문 3장 수식과 `hopper_aviary.py` 대응표, 코드와 다른 지점 | 현행. CLalpha 단위 의심은 `docs/tasks/27` |
| `docs/design/rl-open-source-survey.md` | 오픈소스 RL 환경 조사(PyFlyt 등), 가져올 물리 모델 | 10/15 |
| `docs/design/research-open-source-references.md` | rev C 근거 리서치 | 완료 |
| `docs/design/connectome-control.md` | 확장 트랙 A(커넥톰) 설계와 한계 | 9/18 |
| `docs/design/BOM-revC-teensy.md`, `BOM.md` | 구매 리스트(현행) / rev B(기구 항목만 유효) | |
| `docs/design/*.svg`, `docs/design/tools/` | 배치도·배선도와 그 생성 스크립트 | |
| `docs/design/references/Jacobsen2021_*.pdf` | SolidGeek/Jacobsen 논문 전문(제작·제어의 1차 자료) | |
| `docs/execution/TIMELINE.md` | 한 장 타임라인, 현재 병목 | 10/16 갱신 |
| `docs/execution/semester-roadmap.md`, `week-01-kickoff.md`, `member-weekly-tasks.md` | 9월 기준 원래 계획. 실제보다 약 3주 앞서 있음 | 기록 |
| `docs/execution/procurement-review.md`, `bench-wiring.svg` | 구매 시트 검토 / 구버전 배선도(01 문서 §4로 대체) | 기록 |
| `cad/hopper_params.scad` | **CAD 정본** | 현행 |
| `cad/cg/` | 무게중심·토크 팔 추정 표와 스크립트(#26) | 초안, 10/16 |
| `cad/measurements.md`, `cad/print_parts/`, `cad/renders/` | 실측 기록, 외주 STL 안내, 렌더 | |
| `cad/legacy/` | rev B 스크립트, 안 씀 | 보존 |
| `firmware/cosmos/imu_test_i2c/` | BNO085 4선 I2C 브링업 | 10/15 실물 확인 |
| `firmware/cosmos/imu_test/` | BNO085 SPI(최종 핀맵) | 빌드만 확인 |
| `firmware/cosmos/throttle_serial/` | DShot 벤치 펌웨어 | ESC 없이 확인 |
| `firmware/reference/SingleRotorUAV/` | SolidGeek 펌웨어 원본(MIT). 통합 펌웨어의 출발점 | 손대지 않음 |
| `firmware/singlecopter.param.md` | ArduPilot SingleCopter 대안 경로 | 보존 |
| `sim/sim_stage1/` | Stage 1 환경(`hopper_aviary.py`, 관측 6·행동 5), `params.yaml`, `train.py`, `export_episode.py`, `check_issue21.py` | #21 버그 있음 |
| `sim/connectome/` | 확장 트랙 A: 커넥톰 제약 정책망 | 파이프라인 검증 |
| `kicad/` | 회로도(생성물)와 생성·검증 스크립트(`_tools/`) | ERC 미실행 |
| `web/` | CSV 재생 3D 뷰어(W-A 뼈대) | 신규, 10/16 |
| `data/` | 실험 로그. 파일명 `YYYYMMDD-TCx-런번호` | 비어 있음 |
| `tasks.py`, `pyproject.toml`, `sim/pyproject.toml`, `uv.lock` | 작업 실행기와 파이썬 의존성 고정. `sim/requirements.txt`는 생성물 | |
| `docs/presentation/`, `club promoting material/` | 설명회 발표(9/5 완료)·홍보 자료 | |

## 9. 어디서 찾나

| 질문 | 볼 곳 |
|---|---|
| 내가 지금 뭘 해야 하나 | `docs/learning/README.md` "지금 할 일" → PRD 이슈 → `docs/tasks/` |
| PID vs RL을 정확히 어떤 구조로 비교하나 | 03 문서 §3 |
| RL 상태/행동이 몇 차원인가 | 03 문서 §4 (마스터 §9는 폐기) |
| 핀맵·배선·전원 | 01 문서 §2~§6 |
| 형상·치수·z 배치·질량·CG | 01 문서 §7~§8, 그다음 마스터 §3~§5 |
| 펌웨어 ↔ 웹이 주고받는 형식 | 02 문서 §4 |
| 시험 카드와 합격 기준 | 마스터 §11 |
| 전체 진행과 병목 | `docs/execution/TIMELINE.md` |
| 시뮬레이션 수식이 논문과 어디서 다른가 | `modelling-notes-ch3.md` |

## 10. 확정된 방향 (다시 논의하지 않는 골격)

- **TVC 착륙 호퍼(VTVL), 베인 방식.** EDF를 고정하고 배기 흐름 속 베인 4개로 방향을 바꾼다. 짐벌(모터 자체를 기울이는) 방식보다 기구가 단순하다. 상승 전용 TVC 모델로켓이 아니라 이륙·호버·착륙 전 구간을 스로틀로 제어하는 쪽이다.
- **사양은 rev C** (위 1절 표). 사양 표를 이 파일에 따로 옮겨 적지 않는다. 예전에 rev A 사양이 남아 모순이 생긴 적이 있다.
- **펌웨어**: Teensy 4.0에서 SolidGeek 코드를 포크한다(마스터 §8.1). RL은 `control_hover()`의 `output = K * error` 자리에 정책 추론을 끼우는 구조. 막히면 ArduPilot SingleCopter 대안.
- **시뮬레이션**: Stage 1은 논문 3장 운동방정식을 numpy로 직접 적분하는 자체 `gymnasium.Env`(9/14 결정). gym-pybullet-drones는 모터 4개 대칭 믹싱이 하드코딩돼 기각. Stage 1은 파이프라인 검증용이고 3D 물리엔진 Stage 2는 03 문서 §2.
- **웹**: 물리 계산 없이 `data/`·`sim/` 로그를 읽는 뷰어. 펌웨어와 웹은 02 문서 §4 CSV 계약으로만 연결된다.
- **확장 트랙은 A 또는 B 중 하나만**(10/15). 메인(PID/LQR vs RL)을 대체하지 않는다. A는 커넥톰 제약 정책망(`sim/connectome/`), B는 공개 자료만 쓰는 리버스 엔지니어링(볼록최적화 착륙 유도 논문, BPS.space 등. 비공개 펌웨어·수출통제 자료 제외). 실험 A 이후 결정. 공개 시뮬레이터의 물리 모델(서보·모터 지연, 자이로 반작용, 베인 측력 상한)을 `sim_stage1`에 넣는 일은 확장이 아니라 메인의 선행 작업이다.
- **축소 경로**(참고): PHASE 0 스로틀만으로 시소 균형 → PHASE 1 서보 1개 → PHASE 2 PID 자리에 RL.

## 11. 검토했지만 채택 안 한 대안

- Sparrow TVC Hopper(고체모터 2발): 에너지물질 규제, 튜토리얼 없음.
- 하이브리드/액체로켓 VTVL: 동아리 규모 초과.
- HAB(고고도 기구): 현지 발사 허가 문제로 보류.
- fdiwth/tvc-drone: 다른 구동 방식, 비행 미검증, 제작자가 따라 하지 말라고 명시.
- gym-pybullet-drones: 10절 참고.

## 12. 아직 열려 있는 질문

- 3D프린트 외주업체와 발주 시점(#26).
- 실험 A 일정·장소·장비와 지도교사 서명 확인(#26).
- `CLalpha` 단위 해석과 우리 베인 기하로 다시 계산한 값, 측력 상한 처리 방식(#27).
- `web/` 폴더 위치와 웹 CI 추가 여부(#29).
- 확장 트랙 A/B 선택: 실험 A 이후. A는 셔플 대조군과 차이가 없으면 접는다.
- 최종 자유비행(구속 해제) 도전 여부: STAGE 3 결과를 본 뒤.
- 안전스테이션 재고, FS-i6X 송신기 배터리 방식.

## 13. 지난 실수에서 남긴 교훈

- **충전 전용 USB 케이블**로 Teensy가 안 잡혀 하루를 썼다(10/15). 연결 문제는 케이블부터 의심한다.
- **`Kf`가 실제의 1/37**이라 어떤 제어기도 못 버텼다(9/19, PR #10에서 잠정 보정). 상수는 단위와 크기를 실물 추정치와 비교한다.
- **CG 목표 140~180 mm는 도달 불가**였다(01 문서 §8.4). 설계 숫자도 계산으로 다시 확인한다.
- 존재하지 않는 파일을 "완료"로 적은 기록이 있었다(9/17). 완료는 경로를 확인하고 쓴다.
- `CLAUDE.md`와 `AGENTS.md`를 손으로 동기화하다 링크가 깨졌다(9/17). 정본은 하나만 둔다.
