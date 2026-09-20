# COSMOS — TVC 착륙 호퍼 + 강화학습

청도대원학교 항공우주공학 동아리 COSMOS의 26–27학년도 1학기 프로젝트.
단일 EDF 추력 + 배기 베인 4개로 자세를 제어하는 소형 VTOL 호퍼를 만들고,
전통 제어(PID/LQR)와 강화학습(RL) 제어를 정량 비교한다. SpaceX식 재사용 로켓의
역학을 안전한 축소 규모로 재현하는 게 목표.

## 시작점

- **[`AGENTS.md`](AGENTS.md)** — 정본 컨텍스트 문서: 설계 의도·확정 방향·현재 상태·문서 맵·다음 액션·안전 원칙. AI 세션이든 사람이든 기술적인 걸 파악하려면 이거 먼저. (`CLAUDE.md`는 이 파일로 가는 한 줄짜리 안내판)
- **[`docs/design/00-hopper-master-design.md`](docs/design/00-hopper-master-design.md)** — 마스터 설계도 (rev C)
- **[`docs/execution/TIMELINE.md`](docs/execution/TIMELINE.md)** — ⭐ **전체 타임라인 한 장** (간트차트로 한 것/남은 것/현재 병목). 진행 상황이 궁금하면 여기부터
- **[`docs/execution/week-01-kickoff.md`](docs/execution/week-01-kickoff.md)** — 1–2주차 실행 계획

지금 당장 개발환경만 세팅하고 싶다면 바로 아래 "부원 퀵스타트"로.

---

## 부원 퀵스타트

처음 이 저장소를 받으면 아래에서 본인 팀 항목만 따라가면 된다. 두 팀 모두 제일 먼저 할 일은 같다.

```bash
git clone https://github.com/COSMOS-Aero-Engineering/COSMOS-TVC-Hopper.git
cd COSMOS-TVC-Hopper
git config user.name  "본인 이름"
git config user.email "본인 이메일"
```

### 소프트웨어팀

먼저 [uv](https://docs.astral.sh/uv/)를 한 번만 깔아둔다. 파이썬 버전과 패키지를 한꺼번에 맞춰주는
도구다 — 부원마다 파이썬 버전이 다른 문제까지 같이 없애준다.

```powershell
# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```
```bash
# Mac / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

그다음은 어느 OS든 같다. (Mac은 **Apple Silicon만** 된다 — 고정된 torch 2.14.0에 Intel Mac용
휠이 없다. Intel Mac이면 Windows/Linux PC를 쓰거나, 부장에게 말해서 torch 버전을 조정한다.)

```bash
python tasks.py setup      # .venv 생성 + 고정 버전 의존성 설치 (torch 포함, 3~5분)
python tasks.py sanity     # 환경이 살아 있는지 확인
```

`환경 정상 동작 확인 완료`가 뜨면 끝. 안 뜨면 아래 [트러블슈팅](#트러블슈팅)부터 본다.

버전은 `uv.lock`에 고정돼 있다 — 손으로 `pip install` 하지 말 것. 부원마다 다른 버전이
깔리면 학습 결과가 서로 재현되지 않아, 문제가 생겼을 때 코드 탓인지 환경 탓인지 구분할 수 없다.
버전을 바꿔야 하면 `sim/pyproject.toml`을 고치고 `python tasks.py lock`을 돌린다(`uv.lock`과
`sim/requirements.txt`가 함께 갱신된다). 쓸 수 있는 명령 전체는 인자 없이 `python tasks.py`로 확인.

`python tasks.py check`는 한 번 통과한 검사를 건너뛴다 — 읽는 파일의 내용이 지난번과 같으면
다시 돌리지 않는다(약 39초 → 1초). 어떤 작업이 왜 건너뛰어지는지는 `python tasks.py graph`,
캐시를 무시하려면 `--force`, 아예 비우려면 `python tasks.py clean`.

환경을 다 갖췄으면 `hopper_aviary.py`를 열어보고, AI에게 이렇게 물어본다 — 그냥 읽고 넘어가지 말고 답을 **자기 말로 3문장**으로 줄여 팀 채팅방에 올릴 것. 서로 다르게 요약된 지점이 팀이 헷갈리는 지점이다.

```
이건 1인용 EDF 호퍼의 자세 제어를 학습시키는
강화학습 환경 코드야. 초보자에게 세 가지를 설명해줘.
1) observation이 무엇이고 왜 6개인지
2) action 5개가 각각 물리적으로 뭘 움직이는지
3) reward 식이 어떤 행동을 장려하고 어떤 걸 벌하는지
전문용어는 처음 나올 때 풀어서 써줘.
```

작업 폴더: `sim/`(RL 환경·학습 스크립트), `firmware/cosmos/`(Teensy 펌웨어 — **VSCode + PlatformIO 익스텐션** 필요, 펌웨어 담당만 설치하면 됨. 2026-09-19부터 Arduino IDE 대신 이걸 씀, `firmware/cosmos/README.md` 참고). 폴더마다 `platformio.ini`가 있는 독립 프로젝트라 `cd firmware/cosmos/imu_test && pio run -t upload`로 바로 업로드.

#### 확장 트랙 — 커넥톰 제약 정책망 (`sim/connectome/`)

초파리 커넥톰(실제 뇌 배선도)을 PPO 정책망의 **연결 구조**로 쓰는 비교군. 메인 트랙을
대체하지 않고 비교군을 하나 더 얹는 것이다. 설계 의도는
[`docs/design/connectome-control.md`](docs/design/connectome-control.md),
실행법은 [`sim/connectome/README.md`](sim/connectome/README.md).

```bash
python tasks.py connectome   # 그래프 생성 (합성 CX 링 어트랙터 + 셔플 대조군)
python tasks.py conncheck    # 제대로 도는지 확인
```

⚠ **지금 비교 결과를 읽으면 안 된다.** `params.yaml`의 `Kf`가 실제값보다 약 37배 작아서
베인이 5초 동안 자세를 5.8°밖에 못 바꾸는데 초기 교란은 최대 17°다 — 어떤 제어기도
Stage 1을 못 푸는 상태다. 실험 A로 `Kf`를 채우는 게 먼저다.
진단: `python sim/connectome/authority.py`

### 엔지니어링팀

캘리퍼스로 잰 부품 실측값은 `cad/measurements.md`에 기록하고(없으면 새로 만들 것), CAD 파라미터(`cad/hopper_params.scad`)에 반영한 뒤 커밋한다. 배선 참고는 `docs/execution/bench-wiring.svg`.

작업 폴더: `cad/`(파라메트릭 CAD), `data/`(실험 로그 — 없으면 새로 만들 것).

핵심 배선 3갈래:

| 연결 | 비고 |
|---|---|
| Teensy ↔ BNO085 | I2C, SDA=18 / SCL=19, 둘 다 3.3V |
| Teensy ↔ 수신기 | **레벨 시프터 필수** — 수신기 5V, Teensy 3.3V 전용 |
| Teensy → ESC | DShot 신호선 + 공통 접지. ESC의 BEC 5V는 Teensy에 물리지 않음 |

---

## 협업 규칙

- **`main`에 직접 커밋하지 않는다.** 작업은 항상 브랜치에서 하고 PR로 올린다.
  (정본 규칙은 [`AGENTS.md`](AGENTS.md)의 "작업 규칙 — 브랜치·PR")
- **PR 리뷰어는 부장(`junwonkim07`)으로 지정하고, 승인 전에는 머지하지 않는다.**
  **머지할 수 있는 사람은 김준원(`junwonkim07`)·김민찬(`MINBBBB1201`) 둘뿐** — 본인이 올린 PR이라도
  직접 머지하지 않는다.
- **PR 올리기 전에 `python tasks.py check`.** CI가 볼 걸 로컬에서 미리 보는 것 — 2분이면 끝난다.
- **남의 폴더는 건드리지 않는다.** 소프트웨어팀은 `sim/`·`firmware/cosmos/`, 엔지니어링팀은 `cad/`·`data/`.
- **매 작업 전에 `git switch main && git pull`부터.**
- **충돌(conflict)이 뜨면 혼자 풀지 말고 부장 호출.** 처음 겪으면 대부분 잘못 뭉갠다.
- PLACEHOLDER 값(예: `sim/params.yaml`의 추력 상수)을 실측값으로 바꿀 땐 커밋 메시지에 출처를 남긴다.

### 커밋 태그

커밋 메시지 앞에 대괄호 태그 하나를 붙인다.

| 태그 | 범위 | 예시 |
|---|---|---|
| `[cad]` | 기구 설계 | 상판 EDF 홀 실측값 반영 |
| `[fw]` | 펌웨어 | BNO085 쿼터니언 출력 추가 |
| `[sim]` | 시뮬 · RL | params.yaml 추력 상수 교체 |
| `[data]` | 실험 로그 | 9/19 실험 A 추력곡선 |
| `[docs]` | 문서 | README 트러블슈팅 추가 |

```bash
git switch main && git pull              # 항상 최신 main에서 시작
git switch -c sim/thrust-const-실측반영    # 브랜치부터 만든다
# ... 작업 ...
python tasks.py check                    # CI가 볼 걸 미리 확인
git add -A
git commit -m "[sim] params.yaml 추력 상수 실측값 반영"
git push -u origin HEAD
gh pr create --base main --reviewer junwonkim07
# gh가 없으면: push 후 터미널에 뜨는 링크를 열어 웹에서 PR 생성 → 우측 Reviewers에 junwonkim07
```

브랜치 이름은 `<커밋 태그>/<짧은 설명>` 형태로. 머지된 브랜치는 지운다(`gh pr merge --delete-branch`).

---

## 트러블슈팅

이 섹션은 계속 채워나간다 — 새로 겪은 오류와 해결법은 발견한 사람이 바로 여기 추가하고 `[docs]` 태그로 커밋할 것.

| 증상 | 원인 | 해결 |
|---|---|---|
| `python`, `pip` 명령이 안 먹음 | 설치 시 PATH 미등록 | 파이썬 재설치 시 "Add python.exe to PATH" 체크. 이미 설치했다면 제어판에서 python 재설치(Modify) |
| `.venv\Scripts\activate` 실행 시 오류(실행 정책) | Windows 기본 PowerShell 스크립트 실행 제한 | PowerShell을 관리자로 열고 `Set-ExecutionPolicy RemoteSigned` 후 재시도, 또는 명령 프롬프트(cmd)에서 `.venv\Scripts\activate.bat` 사용. 애초에 활성화 없이 `python tasks.py <작업>`만 써도 된다 |
| `sanity_check.py` 실행 시 `ModuleNotFoundError` | 활성화가 안 된 상태로 직접 실행 | `python tasks.py sanity` 로 실행하면 uv가 알아서 맞춰준다. 직접 실행하려면 프롬프트 앞에 `(.venv)`가 보이는지 확인 |
| `git push` 시 로그인 창이 반복됨 | Git Credential Manager 인증 만료 | 뜨는 브라우저 창에서 GitHub 로그인 재시도. 안 뜨면 Settings → Developer settings → Personal access tokens에서 토큰 생성 후 비밀번호 칸에 붙여넣기 |
| Teensy 업로드 시 보드가 안 잡힘 | USB 드라이버 미인식 또는 프로그램 버튼 타이밍 | PlatformIO가 필요한 툴체인은 자동 설치하지만 Windows에서 드라이버가 안 잡히면 [PJRC Teensy Loader](https://www.pjrc.com/teensy/loader_win10.html) 드라이버만 별도 설치, 업로드 시작 직후 보드의 프로그램 버튼 눌러주기(버튼 손상 시 접점 순간 단락으로 대체 가능) |
| BNO085 값이 안 뜸 | I2C 배선 순서 또는 주소 문제 | I2C 스캔 스케치로 장치 인식 여부 확인(보통 `0x4A`/`0x4B`), SDA/SCL 순서 재확인 |
| `pip install` 중 `OSError: [Errno 2] No such file or directory: ...torch\include\...` | Windows 경로 길이 260자 제한 (torch는 경로가 아주 깊다) | 저장소를 더 짧은 경로로 옮기거나(예: `C:\dev\COSMOS-TVC-Hopper`), [긴 경로 지원 활성화](https://pip.pypa.io/warnings/enable-long-paths) |
| 설치 후 OneDrive가 몇 GB를 동기화하기 시작함 | `.venv`(torch 포함 ~1GB)가 OneDrive 폴더 안에 생겨서 | OneDrive 설정 → 백업/폴더 선택에서 `.venv` 제외. 지워도 `python tasks.py setup`으로 언제든 다시 만든다 |
| `uv: command not found` / `uv 이(가) 없다` | uv 미설치 또는 설치 후 터미널 미재시작 | 위 [소프트웨어팀](#소프트웨어팀) 설치 명령 실행 후 터미널을 새로 연다 |
| `환경을 uv.lock 에 맞추지 못했다` 또는 CI의 `uv sync --locked` 실패 | `pyproject.toml`만 고치고 `uv.lock`을 갱신하지 않음 | `python tasks.py lock` 후 `uv.lock`·`sim/requirements.txt`를 함께 커밋 |

## 구조

| 폴더 | 내용 |
|---|---|
| `docs/design/` | 설계도 · BOM · 리서치 · 참고 논문 |
| `docs/execution/` | 주차별 계획 · 조달 · 배선도 |
| `docs/presentation/` | 동아리 설명회 발표자료 |
| `firmware/` | 펌웨어 — `reference/SingleRotorUAV/`는 [SolidGeek/SingleRotorUAV](https://github.com/SolidGeek/SingleRotorUAV) (MIT) vendor-copy, `cosmos/`는 우리 코드 |
| `cad/` | 자체 파라메트릭 CAD (대안 — 주 경로는 SolidGeek Onshape 포크) |
| `sim/sim_stage1/` | 시뮬레이션 · RL — Stage 1 환경 + PPO 학습 1회 성공 완료 |
| `sim/connectome/` | 커넥톰 제약 정책망 (확장 트랙) — 초파리 배선을 정책망 구조로 |
| `data/` | 실험 로그 (CSV) |
| `tasks.py` | 작업 실행기 — 작업 순서와 입력 해시 캐시. 인자 없이 실행하면 목록 |
| `pyproject.toml` · `uv.lock` | 파이썬 워크스페이스 경계와 의존성 고정본 (`sim/pyproject.toml`이 sim 의존성 정본) |
| `.github/workflows/` | CI — PR마다 sim 환경 로딩 + SB3 연결 자동 확인 |

## 라이선스 / 출처

`firmware/reference/SingleRotorUAV/`는 Emil Jacobsen (Aalborg University)의 MIT 라이선스 프로젝트를
그대로 포함한 것 — 해당 폴더의 `LICENSE`·`ORIGIN.md` 참고. 그 외 이 저장소의 내용은 COSMOS 동아리 작업물.
