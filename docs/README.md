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
| `sim/sim_stage1/` | Stage 1 환경(`hopper_aviary.py`, 관측 6·행동 5), `params.yaml`, `train.py`, `export_episode.py` | #21 베인 제어력 정정(CL 기하 인자·`vane_arm_l`, PR #35). 값은 아직 추정값 |
| `sim/connectome/` | 확장 트랙 A: 커넥톰 제약 정책망 | 파이프라인 검증 |
| `kicad/` | 회로도(생성물)와 생성·검증 스크립트(`_tools/`) | ERC 미실행 |
| `web/` | CSV 재생 3D 뷰어(W-A 뼈대) | 신규, 10/16 |
| `data/` | 실험 로그. 파일명 `YYYYMMDD-TCx-런번호` | 비어 있음 |
| `tasks.py`, `pyproject.toml`, `sim/pyproject.toml`, `uv.lock` | 작업 실행기와 파이썬 의존성 고정. `sim/requirements.txt`는 생성물 | |
| `ship.py` | ship-issue 도구(`tools`/`wt`/`capped`/`review`/`skills`). 5절 작업 순서의 명령을 모든 PC에 준다. 표준 라이브러리만 쓴다 | 10/16 |
| `.claude/skills/ship-issue/`, `.claude/skills/ste-ko/` | AI 도구용 스킬(정본). 이슈·PR·커밋 문장은 `ste-ko`를 따른다 | 10/16 |
| `.agents/skills/` | Codex용 스킬 복사본. 직접 고치지 않는다. `python ship.py skills`가 정본에서 만든다 | 10/16 |
| `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/task.yml` | PR 본문 양식(결정·교차 리뷰·알게 된 것 포함), 작업 이슈 양식 | 10/16 |
| `docs/presentation/`, `club promoting material/` | 설명회 발표(9/5 완료)·홍보 자료 | |
