# 문서 맵

`AGENTS.md`에서 옮긴 저장소 전체 문서·폴더 표다(#38). 경로는 저장소 루트 기준이다.

| 경로 | 내용 | 상태 |
|---|---|---|
| `docs/learning/README.md` | 부원 입구: "지금 할 일" 표, 담당별 첫 실습, 자료실(글·영상 64개), AI 질문 문장 | 현행, 10/16 |
| `docs/execution/STATUS.md` | 현재 상태: 된 것, 막혀 있는 것(`AGENTS.md`에서 옮김) | 10/16 |
| `docs/decisions.md` | 결정 경위: 왜 PR을 거치나, 채택 안 한 대안(`AGENTS.md`에서 옮김) | 10/16 |
| `docs/tasks/` | PRD별 착수 초안(현재 상태·첫 30분·이어서 할 일·확인 못 한 것) | 신규, 10/16 |
| `docs/design/00-hopper-master-design.md` | 마스터 설계 rev C: 아키텍처·치수·질량 예산·시험 카드(§11)·리스크. **CG 목표와 질량 합계는 01 문서가 정정함** | 현행(일부 01로 대체) |
| `docs/design/01-avionics-integration-final.md` | 아비오닉스·배선·기계 통합 rev C.1: 좌표계, Teensy 핀맵, 전원, 빵판·만능기판 배치, z 배치, 질량·CG 재계산, 조립·브링업 절차. 마스터와 충돌하면 이 문서가 최신(§12) | 현행 |
| `docs/design/02-web-dashboard-design.md` | 웹 대시보드·3D 뷰어 설계, **CSV 데이터 계약(§4)**, 개발 단계 W-A부터 W-F, 기술 스택 | 현행 |
| `docs/design/03-control-pipeline-design.md` | PID/RL 구조, 3D 물리엔진 전환(Stage 2), State/Action, 도메인 랜덤화, 온보드 배포. **PID vs RL의 단일 정본** | 현행 |
| `docs/design/modelling-notes-ch3.md` | 논문 3장 수식과 `hopper_aviary.py` 대응표, 코드와 다른 지점 | 현행. CL 결정은 PR #35 |
| `docs/design/rl-open-source-survey.md` | 오픈소스 RL 환경 조사(PyFlyt 등), 가져올 물리 모델 | 10/15 |
| `docs/design/research-open-source-references.md` | rev C 근거 리서치 | 완료 |
| `docs/design/connectome-control.md` | 확장 트랙 A(커넥톰) 설계와 한계 | 9/18 |
| `docs/design/BOM-revC-teensy.md`, `BOM.md` | 구매 리스트(현행) / rev B(기구 항목만 유효) | |
| `docs/design/*.svg`, `docs/design/tools/` | 배치도·배선도와 그 생성 스크립트 | |
| `docs/design/references/Jacobsen2021_*.pdf` | SolidGeek/Jacobsen 논문 전문(제작·제어의 1차 자료) | |
| `docs/execution/TIMELINE.md` | 한 장 타임라인, 현재 병목 | 10/16 갱신 |
| `docs/execution/countdown-1122.md` | 11/22 발표까지 주별 역산 일정과 축소 경로 판정(#258) | 초안, 10/31(11/21에 판정 근거 §3.1 추가) |
| `docs/execution/first-power-procedure.md` | 첫 전원 시험 절차서(P1-P8), 역할, 킬 2중 확인(#398) | 초안, 부장 검토 전 |
| `docs/execution/semester-roadmap.md`, `week-01-kickoff.md`, `member-weekly-tasks.md` | 9월 기준 원래 계획. 실제보다 약 3주 앞서 있음 | 기록 |
| `docs/execution/procurement-review.md`, `bench-wiring.svg` | 구매 시트 검토 / 구버전 배선도(01 문서 §4로 대체) | 기록 |
| `cad/hopper_params.scad` | **CAD 정본** | 현행 |
| `cad/cg/` | 무게중심·토크 팔 추정 표와 스크립트(#26) | 초안, 10/16 |
| `cad/measurements.md`, `cad/print_parts/`, `cad/renders/` | 실측 기록, 외주 STL 안내, 렌더 | |
| `cad/legacy/` | rev B 스크립트, 안 씀 | 보존 |
| `firmware/cosmos/imu_test_i2c/` | BNO085 4선 I2C 브링업 | 10/15 실물 확인 |
| `firmware/cosmos/imu_test/` | BNO085 SPI(최종 핀맵) | 빌드만 확인 |
| `firmware/cosmos/throttle_serial/` | DShot 벤치 펌웨어 | ESC 없이 확인 |
| `firmware/cosmos/servo_bench/` | 시리얼로 서보 번호(1-2)와 펄스폭(1000-2000 µs)을 받아 서보 하나를 움직인다. EDF·ESC 미연결 | 빌드만 확인. 실물 서보 시험은 #279 |
| `firmware/cosmos/rc_bench/` | RC 수신기 PWM 5채널 읽기와 킬 채널 스로틀 0 보고(브링업 P3). 모터 출력 없음 | 빌드만 확인 |
| `firmware/cosmos/policy_bench/` | PPO Actor 추론 시간·메모리 벤치(USB 출력만, 구동 코드 없음). 헤더는 `sim/deployment/check_parity.py`가 만든다 (#291) | 빌드만 확인 |
| `firmware/reference/SingleRotorUAV/` | SolidGeek 펌웨어 원본(MIT). 통합 펌웨어의 출발점 | 손대지 않음 |
| `firmware/singlecopter.param.md` | ArduPilot SingleCopter 대안 경로 | 보존 |
| `sim/sim_stage1/` | Stage 1 환경(`hopper_aviary.py`, 관측 7·행동 5), `params.yaml`, 학습 `ppo_ablation.py`(`tasks.py train`, #345), `export_episode.py`, PD, PID, PPO 네 지표 비교표 `compare_metrics.py`(학습 분포와 TC-3 기울기 10° 두 조건, #266 #276. `--tilt-deg`로 학습 분포 밖 기울기 고정 조건, #312), PID 게인 격자 탐색 `pid_tune.py`(#349) | #21 베인 제어력 정정(CL 기하 인자·`vane_arm_l`, PR #35). 값은 아직 추정값 |
| `sim/deployment/` | PPO Actor를 C++ 헤더로 내보내고 Python 예측과 비교하는 `check_parity.py` (#291) | PC 비교 통과: #230 모델 Linux GCC, #230 전 모델 Linux GCC·Windows MSVC |
| `sim/stage2/` | Stage 2 자유비행 6자유도 환경(MuJoCo). 공중 착륙(PD·PPO)과 지상 출발 임무(이륙·호버·이동·착륙, 참상태·추정 피드백), 웹 CSV 내보내기 (#289) | 시뮬레이션만. 상수는 실측 전 추정값 |
| `sim/connectome/` | 확장 트랙 A: 커넥톰 제약 정책망 | 파이프라인 검증 |
| `kicad/` | 회로도(생성물)와 생성·검증 스크립트(`_tools/`) | ERC 실행(10/17, 오류 4·경고 129). Y축 반전 결함 #66 — 배선에 쓰지 말 것(극성 반대) |
| `web/` | CSV 재생 3D 뷰어(W-A 뼈대) | 신규, 10/16 |
| `data/` | 실험 로그. 파일명 `YYYYMMDD-TCx-런번호` | 비어 있음 |
| `tasks.py`, `pyproject.toml`, `sim/pyproject.toml`, `uv.lock` | 작업 실행기와 파이썬 의존성 고정. `sim/requirements.txt`는 생성물 | |
| `ship.py`, `test_ship.py` | ship-issue 도구(`tools`/`wt`/`link`/`capped`/`review`/`skills`). `AGENTS.md` §작업 순서의 명령을 모든 PC에 준다. 표준 라이브러리만 쓴다. `test_ship.py`는 gh 없이 가짜 응답으로 도는 단위 검사다(`python tasks.py shiptest`, `check`에 포함) | 10/16, `link`와 `test_ship.py`는 #109 |
| `.claude/skills/ship-issue/`, `.claude/skills/ste-ko/` | AI 도구용 스킬(정본). 이슈·PR·커밋 문장은 `ste-ko`를 따른다 | 10/16 |
| `.agents/skills/` | Codex용 스킬 복사본. 직접 고치지 않는다. `python ship.py skills`가 정본에서 만든다 | 10/16 |
| `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/task.yml` | PR 본문 양식(결정·교차 리뷰·알게 된 것 포함), 작업 이슈 양식 | 10/16 |
| `docs/presentation/`, `club promoting material/` | 설명회 발표(9/5 완료)·홍보 자료 | |
