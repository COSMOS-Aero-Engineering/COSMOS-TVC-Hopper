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

**마지막 갱신: 2026-10-16.**

---

## 핵심 규칙 (사람과 모든 AI 도구 공통, 2026-10-16)

Claude Code, Codex, OpenCode 등 어떤 도구를 쓰든 이 규칙을 먼저 지킨다. 자세한 순서는 바로 아래 §작업 순서에 있다.

1. 작업은 GitHub 이슈에서 시작한다. 이슈가 없으면 먼저 만든다. 필요한 도구는 `python ship.py tools`가 확인한다. 설치할 수 있으면 설치하고, 못 하면 설치 방법을 출력한다.
2. `main`에 직접 커밋하거나 푸시하지 않는다. AI는 머지하지 않는다.
3. 구현하기 전에 Best practice를 조사한다: 공식 문서, 데이터시트, 라이브러리가 권장하는 방식, 잘 관리된 참고 프로젝트, 이 저장소의 기존 코드와 문서. 조사한 출처는 PR의 "근거"에 적는다.
4. 추측하지 않는다. 실행한 명령과 출력이 없으면 "완료"라고 쓰지 않는다.
5. 이슈 범위 밖의 문제는 고치지 않고 새 이슈로 남긴다.
6. 이슈, PR, 커밋 메시지는 `ste-ko` 스킬(`.claude/skills/ste-ko/SKILL.md`)을 불러온 뒤 쓴다. 스킬 목록에 `ste-ko`가 없는 도구(예: Codex는 `.agents/skills`만 읽는다)는 그 파일을 직접 읽는다. `ship-issue` 스킬(`.claude/skills/ship-issue/SKILL.md`)도 같다.
7. force push, `git reset --hard`, 푸시한 커밋 amend, 여러 파일 삭제를 하지 않는다. `.env`와 비밀 키를 읽지 않는다.
8. **사람만 하는 일**을 만나면 AI는 멈추고 라벨 `agent physically incapable` 이슈를 연다: 돈 쓰기(부품 구매), 외부 계정, 비밀 키, 물리 동작(EDF·ESC 전원 인가, 실물 업로드, LiPo 충전). 이슈 본문은 "풀 방법 / 선택지 / 근거"로 쓴다.

---

## 작업 순서 — 이슈에서 PR까지 (ship-issue 방식, 2026-10-16)

사람이든 AI 에이전트든 이 저장소에서 작업할 땐 예외 없이 아래 순서를 따른다. AI는 사람이 막는 단계(§핵심 규칙 8)가 아니면 단계 사이에 멈추지 않고 진행한다.

1. **이슈를 읽고 선점한다.** `gh issue view <번호> --comments`로 본문과 댓글을 전부 읽는다. 다른 사람이 이미 `claimed by ...`를 남겼거나 이슈가 닫혔으면 멈추고 알린다. 아니면 2단계에서 브랜치를 만든 뒤 댓글 `claimed by <브랜치 이름>`을 남긴다.
2. **이슈 전용 worktree와 브랜치를 만든다.** `python ship.py wt <이슈 번호>`가 최신 `origin/main`에서 `../<저장소>-wt/issue-<번호>` 폴더와 브랜치 `<태그>/<이슈 번호>`를 만든다. 태그는 이슈 제목의 `[태그]`나 라벨에서 정하고, 없으면 `--tag`로 준다. 태그는 `cad`/`fw`/`sim`/`web`/`kicad`/`data`/`docs`/`infra`. 그 폴더로 이동해서 작업한다. 같은 폴더를 다른 세션과 같이 쓰지 않는다.
3. **조사한 뒤 구현한다.** §핵심 규칙 3대로 Best practice를 먼저 조사한다. 부원은 §일하는 방식의 "이해 먼저"도 함께 한다. 구현은 이슈 범위만 한다.
4. **검사를 통과시킨다.** 바꾼 영역의 검사를 직접 돌린다: `python tasks.py check`(sim), `pio run`(펌웨어), KiCad ERC, 문서 링크 확인. 학습처럼 메모리를 많이 쓰는 명령은 `python ship.py capped 8G -- <명령>`으로 상한을 건다(Windows에서는 상한이 걸리지 않고 경고만 나온다). 실패하면 고칠 때까지 반복한다. 커밋은 작게 나누고 제목은 `[태그] 무엇을 바꿨는지`로 쓴다.
5. **PR을 연다.** `.github/pull_request_template.md`를 채운다. 본문에 `Closes #<이슈 번호>`를 쓴다. **실제로 해 본 확인만 체크**하고 범위를 "빌드만 확인", "ESC 없이 Teensy에서만 확인"처럼 쓴다. 확인 못 한 값은 `확인 필요`로 적는다. 작성자가 아래 권한자가 아니면 권한자 한 명을 리뷰어로 지정한다(`gh pr create --base main --reviewer junwonkim07`).
6. **다른 회사의 모델로 교차 리뷰한다.** `python ship.py review --author <작성한 모델>`이 작성자와 다른 계열의 리뷰어를 고른다: Codex, Claude Code 순서로 로그인된 것을 쓰고, 둘 다 없으면 OpenCode 무료 모델(로그인 불필요)을 쓴다. 리뷰 요청에는 범위(브랜치나 PR 번호)만 쓰고 의심 가는 점이나 체크리스트를 넣지 않는다. 맞는 지적은 고쳐서 푸시하고, 받아들이지 않는 지적은 이유를 한 줄 남긴다. 결과는 PR 템플릿의 "교차 리뷰"에 쓴다.
7. **CI를 통과시킨다.** `gh pr checks --watch`. 실패하면 `gh run view --log-failed`로 로그를 읽고 고친다.
8. **마무리하고 멈춘다.** 남은 일, 확인하지 못한 항목, 미룬 결정은 하나씩 후속 이슈로 만든다. 사람만 확인할 수 있는 것(Windows 실행, 실물 동작 등)은 라벨 `agent physically incapable`을 단다. 이슈 번호는 PR 템플릿의 "후속 이슈"에 적는다. 이슈 없이 대화나 PR 본문에만 "남은 것"을 남기지 않는다. PR 템플릿의 "알게 된 것"에 새로 알게 된 사실과 틀렸던 가정을 쓴다. 모든 에이전트가 알아야 할 교훈이면 이 PR에서 아래 §교훈에 한 줄 추가한다. 그다음 PR 링크를 알리고 멈춘다.

**리뷰·머지 권한**: 부장 김민찬(`MINBBBB1201`)과 차장 김준원(`junwonkim07`) 두 명뿐이다. 두 사람은 CI(`.github/workflows/ci.yml`)가 초록불인 것을 확인하고 변경사항을 직접 검토한 뒤, 본인이 올린 PR도 스스로 머지할 수 있다. 그 외 사람은 두 사람 중 한 명의 승인(Approve)을 받아야 하며 직접 머지하지 않는다. 머지는 squash 방식이다: `gh pr merge --squash --delete-branch`.

**남의 브랜치**: 권한자가 요청하면 다른 사람의 브랜치나 PR에도 커밋을 더할 수 있다. 새 커밋만 더하고, 푸시 전에 원격 브랜치의 최신 커밋을 확인해서 남이 먼저 푸시한 커밋을 덮지 않는다.

왜 PR을 거치나(2026-09-18): 이전 규칙은 "작업 폴더가 팀별로 나뉘어 있으니 `main`에 직접 커밋"이었다. 충돌은 확실히
줄지만, 그 규칙의 진짜 비용은 충돌이 아니라 **깨진 코드가 곧바로 모두의 `git pull`에 실려 간다**는
점이다. 부원이 자기 작업을 시작하고 나서야 남의 실수를 발견하면 "내가 뭘 잘못했나"와 구분이 안 되고,
되돌릴 단위도 불분명해진다. PR은 (a) CI가 사람보다 먼저 깨진 걸 잡고, (b) 부장이 머지 전에 한 번 보고,
(c) 문제가 생겼을 때 되돌릴 단위가 PR 하나로 명확하다 — 이 셋을 동시에 준다.

---

## 일하는 방식: 팀별 PRD와 이해 먼저 (2026-10-16)

- **할 일은 GitHub 이슈의 팀별 PRD로 받는다**(라벨 `prd` + 영역 라벨 `fw`/`sim`/`web`/`cad`/`kicad`).
  PRD는 기한·담당·목표(판정 형태)·배경(현재 상태와 숫자)·판정 기준·사람별 작업·결과물(PR 제목까지)·제외·협업·
  볼 것(자료실 ID)·진행 보고로 쓴다. 한 이슈는 PR 하나 이상으로 끝나는 크기로 쪼갠다.
- **이해 먼저.** PRD를 받으면 바로 구현하지 않는다. ① 프로젝트에서 어떤 의미인지 ② 잘못되면 무엇이
  깨지는지 ③ 알아야 할 개념을 자기 말로 PRD 이슈 댓글에 쓴 뒤 시작한다. 이해가 안 되면 될 때까지 AI에게
  묻는다.
- **진행 보고**는 PRD 이슈 댓글로 "한 일(숫자 포함) / 올린 PR 번호 / 다음 할 일" 세 줄.
- AI가 부원과 일할 때: 쉬운 한국어로 말하고 전문 용어는 처음 나올 때 풀어서 설명한다. 위 세 가지를 먼저
  설명하고 부원이 자기 말로 설명하게 한 뒤 할 일 목록을 같이 정하고, 작은 단위로 구현하며 단계마다 무엇을
  왜 바꿨는지 알린다. Git 명령(최신 `main` 받기, 브랜치, 커밋, 푸시, `gh pr create`)은 대신 실행하되 명령마다
  한 줄로 설명한다. `main` push, force push, `reset --hard`, 여러 파일 삭제는 하지 않는다.
- 부품 사양·핀 번호·치수·물리 상수를 추측하지 않는다. 데이터시트(링크와 쪽 번호), 실측값, CAD 변수를 근거로
  쓴다. 실물로 확인하지 않은 동작을 "동작함"으로 보고하지 않는다.

---

## 문서 맵

| 경로 | 내용 | 상태 |
|---|---|---|
| `docs/learning/README.md` | 새 부원용 학습 입구: 한국어 프로젝트 설명, 담당별 첫 실습, 글·그림·영상 자료실. `week-02.md`는 프린트 미발주·Teensy 업로드 미확인 조건의 활동 운영안. 기술 설계 정본을 대체하지 않음 | 2026-10-14 추가 |
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
| `docs/execution/TIMELINE.md` | **전체 타임라인 한 장 요약(신규)** — Mermaid 간트차트(팀별 트랙, 완료/진행/병목 색 구분), 한 것·남은 것 표, 현재 병목 3개. 세부는 아래 문서들로 링크만 | 신규, 2026-09-20 |
| `docs/execution/week-01-kickoff.md` | 1–2주차 마스터 실행계획 — 타임라인·부장 준비·부품 전체·세션 진행 | 9/18–19 세션용 |
| `docs/execution/semester-roadmap.md` | **3–10주차 세션별 실행계획(신규)** — week-01-kickoff.md를 이어받아 팀 3개를 매주 세션 단위로 배치. KiCad 착수(Week 4)·baseline 확정(Week 7)·RL 비교(Week 8)·발표(Week 10). §0.1에 원래 매크로 로드맵과의 일정 차이 분석 포함 | 신규, 2026-09-18 |
| `docs/execution/member-weekly-tasks.md` | **부원 7명 개인별 주간 태스크(신규)** — 팀 단위 계획을 Week 1 잔여~Week 10까지 이름별로 배정(엔지니어링: 김민찬·박지훈·이민우·김시우 / 소프트웨어: 김준원·김민지·권재후) | 신규, 2026-09-18 |
| `docs/execution/procurement-review.md` | 구글시트 행별 검토 | — |
| `docs/execution/bench-wiring.svg` | 벤치 배선도(구버전 — `01-avionics-integration-final.md` §4로 대체됨) | — |
| `kicad/` | Teensy·IMU·서보·RC·ESC 전원/신호 계통 KiCad 스키매틱 + 코드 기반 생성·검증 도구 | 생성 완료, ERC 확인 대기 |
| `firmware/reference/SingleRotorUAV/` | SolidGeek 펌웨어 원본 vendor-copy(MIT, `ORIGIN.md`에 수정 계획) — **컴파일 성공 확인**(2026-09-13) | 원본, 손대지 않음 |
| `firmware/cosmos/imu_test/` | BNO085 SPI 스케치(최종 핀맵). 배선 주석은 10/15 실물 실크 기준으로 정정 | 작성 완료, SPI 실물 미검증 |
| `firmware/cosmos/imu_test_i2c/` | BNO085 4선 I2C 브링업 스케치(3V·G·18·19). I2C 스캔 후 0x4A/0x4B 자동 연결 | 2026-10-15 실물 확인 |
| `firmware/cosmos/throttle_serial/` | DShot 스로틀 시리얼 테스트 스케치(실험 A·C용, 2초 무입력 자동0% 페일세이프 포함) | 작성 완료 |
| `firmware/singlecopter.param.md` | ArduPilot SingleCopter 파라미터 — **대안 경로**(rev C가 막힐 때) | 보존 |
| `cad/hopper_params.scad` | **CAD 정본.** EDF 실측(하우징 외경 72mm, 볼트 플랜지 없음 → 클램프 마운트) 반영, 구조버그 2건 수정 완료 | 2026-09-13 |
| `cad/measurements.md` | 실측값 기록 표 | 빈 템플릿 |
| `cad/print_parts/` | 외주 프린트용 STL 9종 — **실제로 export 완료(2026-09-18)** | 완료 |
| `cad/renders/` | 조립 렌더 PNG(전체·베인링 클로즈업) | 2026-09-18 |
| `cad/legacy/` | rev B 단계 3분할 스크립트 — `hopper_params.scad`로 대체됨, 더 이상 안 씀 | 보존만 |
| `sim/sim_stage1/hopper_aviary.py` | RL Stage 1 환경(자세 안정화, 위치 구속) — 관측 6·행동 5차원, 도메인 랜덤화 포함 | 구현·검증 완료 |
| `sim/sim_stage1/params.yaml` | 물리 상수 — **거의 전부 PLACEHOLDER**, `vane_arm_l/r`만 실측 기반 | 실측 대기 |
| `sim/connectome/` | **확장 트랙 A: 커넥톰 제약 정책망**(B와 택1) — 초파리 배선을 PPO 정책망 구조로. 합성 CX 그래프 + FlyWire 실측 경로, 차수보존 셔플 대조군, PD baseline, 평가지표, 제어권한 진단 | 2026-09-18 착수 |
| `docs/design/connectome-control.md` | 위 트랙의 목표·설계·한계·구현 중 겪은 함정 | 2026-09-18 |
| `test_cartpole.py`, `test_pendulum.py` | SB3 워크플로 익히기용 | 완료 |
| `data/` | 실험 로그(CSV) | 착수 전 |
| `pyproject.toml` · `sim/pyproject.toml` · `uv.lock` | 파이썬 워크스페이스 경계와 의존성 **버전 고정본**(uv) — 부원마다 다른 버전이 깔려 결과가 재현 안 되는 걸 막는 용도. `sim/pyproject.toml`이 sim 의존성 정본, `uv.lock`이 실제 고정본 | 2026-09-18 추가 |
| `sim/requirements.txt` | 위 lock에서 생성되는 **사본**(`python tasks.py lock`) — uv 없이 pip만 쓸 때용. 손으로 고치지 않는다 | 2026-09-18 생성물로 전환 |
| `ship.py` | ship-issue 도구(`tools`/`wt`/`capped`/`review`) — §작업 순서의 명령을 모든 PC에 준다. 없는 도구(gh, opencode)는 처음 쓸 때 설치한다. 표준 라이브러리만 쓴다 | 2026-10-16 추가 |
| `.claude/skills/ship-issue/`, `.claude/skills/ste-ko/` | AI 도구용 스킬. Claude Code와 OpenCode가 읽는다 | 2026-10-16 추가 |
| `tasks.py` | 작업 실행기(`setup`/`lock`/`compile`/`sanity`/`smoke`/`check`/`train`/`deck`/`graph`/`clean`) — 작업 간 순서와 입력 해시 캐시를 갖는다. Windows에 `make`가 없어서 파이썬 stdlib로 구현. CI도 `python tasks.py check`를 그대로 호출한다 | 2026-09-18 추가 |
| `.github/workflows/ci.yml` | CI — PR마다 sim 문법·sanity·PPO 스모크 + PlatformIO 펌웨어 2종 빌드. 학습은 돌리지 않는다 | 2026-09-19 갱신 |
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
| "지금 전체적으로 어디까지 왔지? 뭐가 남았지?" | `docs/execution/TIMELINE.md` — **한 장 요약(간트차트)** |
| "이번 주 동아리 시간에 뭘 하나?" | `docs/execution/semester-roadmap.md` (1–2주차는 `week-01-kickoff.md`) — **팀 단위** |
| "이번 주에 (내 이름)이 뭘 해야 하나?" | `docs/learning/README.md`의 **"지금 할 일" 표**(현재 과제의 유일한 기준). `member-weekly-tasks.md`는 9월 기준 원래 계획이라 실제보다 약 3주 앞서 있다 |
| "전자 배선·핀맵이 정확히 어떻게 되나?" | `01-avionics-integration-final.md` (마스터 설계도 §6.5·§7보다 이 문서가 최신) |
| "기구 형상·치수·질량예산은?" | `00-hopper-master-design.md` §3~§7 |

## 부원이 AI에게 자기 과제를 물을 때

부원이 "내 과제를 이해하게 도와줘", "이거 같이 해줘"라고 하면 AI는 이 순서를 따른다.

1. **이름부터 확인한다.** 모르면 묻는다. `docs/learning/README.md`의 "지금 할 일" 표에서 그 사람의 행을 찾고, 그 행의 **PRD 이슈**(라벨 `prd`)에서 그 사람 담당 절을 읽는다. 표의 날짜가 오래됐거나 이 절의 현재 상태와 다르면 그 사실을 먼저 말하고 부장·차장에게 확인하라고 한다.
2. **그 행의 근거(이슈 번호, 파일)를 직접 연다.** 이슈는 `gh issue view <번호> -R COSMOS-Aero-Engineering/COSMOS-TVC-Hopper`, 파일은 저장소에서 읽는다. 기억이나 일반 지식으로 대신하지 않는다.
3. **설명은 그 사람 담당 안내서(`docs/learning/tracks/`) 수준에서 시작한다.** 입력·출력·정상 결과를 먼저 보여주고, 부원이 자기 말로 다시 설명하게 한다. 처음 하는 사람에게 범위가 큰 지시("PID 구현")를 그대로 넘기지 않는다.
4. **실행은 작은 단위로, 결과를 기록하게 한다.** 측정값·로그는 `data/`, 코드·문서 변경은 이슈, 브랜치, PR 순서로(위 §작업 순서). AI는 머지하지 않는다.

AI가 지켜야 할 선:
- **EDF·ESC에 배터리 전원을 넣는 단계는 안내만 하고, 부장 입회와 아래 §안전 원칙 확인 전에는 진행하라고 하지 않는다.** 첫 회전 시험은 팬을 분리하거나 스탠드에 볼트로 고정한 상태에서만 한다(#24).
- 실물에서 확인하지 않은 것을 "된다"고 말하지 않는다. 배선은 실물 모듈의 실크 표기와 `01-avionics-integration-final.md`를 대조한다.
- `sim/sim_stage1`은 도메인 랜덤화를 켜면 어떤 정책도 안정화하지 못하는 버그(#21)가 있다. 고치기 전에는 RL 학습 결과를 성능으로 해석하지 않는다.
- Windows PowerShell 5.1에서는 `&&`가 안 된다. 명령을 이어 쓸 때는 `;`를 쓴다. Teensy가 안 잡히면 먼저 데이터 전송용 USB 케이블인지 확인한다(충전 전용 케이블이 실제 원인이었다).

## 현재 상태 (최신 항목: 2026-10-16)

- **2026-10-15~16 (실물 브링업, 시뮬레이션 점검)**: Teensy가 안 잡히던 원인은 충전 전용 USB 케이블이었다. 데이터 케이블로 업로드 성공, BNO085를 4선 I2C로 0x4B에서 인식하고 자세값 출력 확인(#18, `imu_test_i2c`). `imu_test`(SPI) 배선 주석의 MOSI/MISO 짝을 실물 실크 기준으로 정정. DShot 벤치 펌웨어를 arm 게이트·DShot 600 상한·램프·워치독·비상정지로 재작성(#19), 실물 ESC 시험은 #24. 시뮬레이션 점검에서 도메인 랜덤화의 CG 오프셋이 베인 최대 제어력의 약 20배라 어떤 정책도 안정화 못 하는 버그와 `vane_arm_l` 정의 불일치를 발견(#21). 에피소드를 웹 CSV 계약으로 내보내는 `export_episode.py` 추가(#23), 오픈소스 RL 환경 조사(#22, `docs/design/rl-open-source-survey.md`). 확장 트랙은 A(커넥톰)/B(리버스 엔지니어링) 택1로 정리(#20). 부원별 현재 과제는 `docs/learning/README.md`의 "지금 할 일" 표로 통일.

- **CAD**: EDF 실측 완료(9/13) — 볼트 플랜지 없는 제품이라 클램프 마운트로 설계 변경. rev C.1에서
  장비 선반·서보 보스·스파 커플러·다리 방위 등 구조 대폭 보강(`01-avionics-integration-final.md` §12
  참고). `cad/hopper_params.scad`가 정본. **STL 9종 실제로 export 완료(2026-09-18)** — 이 PC 바탕화면의
  `openscad.exe`(2021.01)가 정상 동작함을 확인(`Program Files\OpenSCAD\`는 깨진 설치였을 뿐). 검증
  `echo()` 12개 전부 통과. 조립 렌더는 `cad/renders/`, STL은 `cad/print_parts/`.
- **펌웨어**: `firmware/reference/SingleRotorUAV/` 컴파일 성공(BasicLinearAlgebra/SerialTransfer
  라이브러리 이슈 해결). `firmware/cosmos/`에 단위 테스트 스케치 2개 작성 완료(`imu_test/`,
  `throttle_serial/` — 원본 드라이버 재사용, 안전장치 포함). **2026-09-19: 개발환경 Arduino IDE →
  PlatformIO(VSCode)로 전환** — `firmware/cosmos/*/platformio.ini` 추가, 각 스케치를 `pio run`으로
  실제 빌드 검증(전에 아무도 실제로 컴파일해본 적이 없었음). 그 과정에서 `imu_test.ino`의 진짜 컴파일
  버그 발견·수정(`BNO080` 기본 생성자 없음 — `firmware/cosmos/README.md` 참고). 통합 펌웨어는 아직.
  이어 PR #13에서 BNO085 연결을 I2C(핀 18/19)에서 확정 핀맵의 SPI(CS=10, MOSI=11, MISO=12,
  SCK=13, RST=20, INT=21, WAK/PS0=22)로 전환해 RC CH1·CH2와의 핀 충돌을 제거했다. Teensy 4.0
  핀헤더 납땜·USB 연결 완료(2026-09-18~19). 실물 업로드는 2026-10-15 성공(위 최신 항목).
- **소프트웨어(RL)**: SB3 CartPole-v1/Pendulum-v1 완료. `sim/sim_stage1/hopper_aviary.py` — 논문
  3장 운동방정식을 numpy로 직접 적분하는 순수 `gymnasium.Env`(gym-pybullet-drones 포기 이유는
  아래 §소프트웨어 스택). 도메인 랜덤화 포함, PPO 1회 학습 성공(파이프라인 검증 목적, 물리값이
  PLACEHOLDER라 성능 숫자 자체는 무의미). 코드-논문 대응 검토 결과 베인력 계산에 단순화 지점 발견 —
  `docs/design/modelling-notes-ch3.md` §2 참고, 실측값 넣을 때 반드시 확인.
- **확장 트랙 A, 커넥톰(2026-09-18 착수, B와 택1)**: `sim/connectome/` — 초파리 커넥톰 배선을 PPO 정책망의
  연결 구조로 고정하고 가중치만 학습하는 비교군. 합성 CX 링 어트랙터 그래프(104뉴런)로
  파이프라인 검증 완료, 차수보존 셔플 대조군·PD baseline·공통 평가지표까지 구현. CI가
  `conncheck`로 매 PR 검사한다. FlyWire 실측 그래프 경로는 코드만 있고 아직 안 돌렸다(수백 MB
  다운로드 필요). 기존 `Kf=3.0e-8` 오류는 PR #10에서 잠정값 `1.1e-6`으로 보정돼 비교 파이프라인은
  다시 동작하지만, 실측값이 아니므로 결과를 최종 성능으로 해석하면 안 된다.
- **확장 트랙 B, 리버스 엔지니어링(2026-10-15 추가, A와 택1)**: 착수 전. 아래 §목표 6 참고.
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

> 아래는 9월 기준 목록이다. 지금 부장 과제는 `docs/learning/README.md`의 "지금 할 일" 표(3D프린트 외주 발주, 실험 A 안전 계획)를 본다.

1. **9/18(금) 1h + 9/19(토) 2h — 첫 세션.** 상세 진행은 `docs/execution/week-01-kickoff.md`. 요약:
   금요일은 팀 확정+착수, 토요일은 실험 A(EDF 추력곡선)·B(IMU 브링업)·C(DShot 모터제어).
2. 실험 A 진행 → `sim/sim_stage1/params.yaml`의 PLACEHOLDER(Kf 등) 실측값으로 교체
   (`docs/design/modelling-notes-ch3.md` §2·§6 대응표 보고 반영).
   기존 `Kf=3.0e-8` 오류는 PR #10에서 10 N 정적추력 기준 잠정값 `1.1e-6`으로 보정 완료.
   파이프라인 검증은 가능하지만 실제 성능 비교 전에는 실험 A 값으로 다시 교체해야 한다.
   진단: `python sim/connectome/authority.py`
3. ~~Teensy 4.0 핀헤더 납땜~~ — **완료(2026-09-18~19)**, PlatformIO 빌드까지 검증됨.
   다음: `pio run -t upload`로 실물 업로드 → Experiment B(IMU 브링업) 재개.
4. ~~`cad/print_parts/`의 STL 실제로 export~~ — **완료(2026-09-18)**. 다음: 슬라이서에서 치수·인필
   확인(PETG, 인필 40%) → 3D프린트 외주 발주.
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
- 동아리차장: 김준원.

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
6. (확장 트랙, **A 또는 B 중 하나만**, 2026-10-15 정정) 둘 다 메인 트랙(PID/LQR vs RL)을 대체하지
   않는 추가 산출물이다. 어느 쪽으로 갈지는 실험 A 이후 정한다(§아직 열려 있는 질문).
   - **A. 커넥톰 제약 정책망**(2026-09-18 착수): SB3 정책망의 연결 구조를 초파리
     커넥톰(FlyWire v783)으로 고정하고 가중치만 학습. 환경 코드는 안 건드리고 `policy_kwargs`만
     바꿔 끼우는 시뮬레이션 전용 비교군. 상세: `docs/design/connectome-control.md`.
   - **B. 리버스 엔지니어링(공개 자료 분석)**(2026-10-15 추가): 실제 착륙 로켓·TVC 기체가 쓰는
     제어 방식을 **공개된 자료로만** 분석해 우리 baseline(PID/LQR) 설계에 적용한다. 대상 예:
     SpaceX 착륙 유도의 기반이 된 볼록최적화 착륙 유도 논문(Açıkmeşe·Blackmore, G-FOLD 계열),
     소형 TVC 착륙 취미 프로젝트(BPS.space 등). 상용 기체의 비공개 펌웨어나 수출통제(ITAR) 대상
     자료는 쓰지 않는다. 산출물: 우리 구조(EDF+베인)와의 차이 비교 노트, 적용할 수 있는 기법을
     baseline 게인 설계(Week 6~7)에 반영.
   - 택1 대상이 아닌 것: 공개 시뮬레이터에서 **물리 모델**(서보 지연·데드밴드, 모터 응답 지연, 회전자
     자이로 반작용, 베인 측력 상한)을 가져와 `sim/sim_stage1`을 고치는 일은 확장 트랙이 아니라 메인
     트랙의 선행 작업이다. 시뮬레이션이 틀리면 PID vs RL 비교 자체를 믿을 수 없다. 이슈 #21,
     `docs/design/rl-open-source-survey.md` §6 참고.

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
- 확장 트랙을 A(커넥톰)와 B(리버스 엔지니어링) 중 무엇으로 갈지: 실험 A 이후 결정. A는
  `run_comparison.py` 결과가 셔플 대조군과 차이가 없으면 접고, 그 경우 B로 가거나 메인만 간다.
- CONTRIBUTING.md를 따로 만들지 여부 — 지금은 `README.md`의 "부원 퀵스타트/협업 규칙/트러블슈팅"
  섹션이 그 역할을 이미 하고 있어서 안 만듦(내용 중복 방지). GitHub가 자동으로 찾는 파일명이라는
  이점은 있지만, 외부 기여자가 없는 학교 동아리 저장소라 지금은 실익이 적다고 판단 — 나중에 필요해지면
  `README.md`의 해당 섹션을 그대로 옮겨서 만들면 됨.

## 교훈

에이전트가 틀렸다가 바로잡힌 것을 한 줄씩 남긴다. 같은 실수를 다음 세션이 반복하지 않게 하는 용도다.

- (2026-10-16) "X 방식을 원한다"는 요청은 X를 직접 실행하라는 뜻이 아니라 저장소 규칙과 템플릿에 X를 넣으라는 뜻일 수 있다. 둘 중 무엇인지 모호하면 먼저 묻는다.
- (2026-10-16) 부원 PC에 없는 도구라고 작업 단계를 빼지 않는다. 저장소가 그 도구를 주거나(`ship.py`) 없으면 자동으로 설치하게 한다.
- (2026-10-16) 남은 일과 확인하지 못한 항목을 보고만 하고 끝내지 않는다. 후속 이슈로 만들어야 추적된다(#36-#39).
- (2026-10-16) Claude Code는 같은 폴더나 상위 폴더에 `CLAUDE.md`가 있으면 `AGENTS.md`를 자동으로 읽지 않는다([공식 문서](https://code.claude.com/docs/en/memory#agents-md)). 그래서 `CLAUDE.md` 첫 줄에 `@AGENTS.md`를 둔다.
