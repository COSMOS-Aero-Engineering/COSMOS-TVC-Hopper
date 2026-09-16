# COSMOS — TVC 착륙 호퍼 + 강화학습

청도대원학교 항공우주공학 동아리 COSMOS의 26–27학년도 1학기 프로젝트.
단일 EDF 추력 + 배기 베인 4개로 자세를 제어하는 소형 VTOL 호퍼를 만들고,
전통 제어(PID/LQR)와 강화학습(RL) 제어를 정량 비교한다. SpaceX식 재사용 로켓의
역학을 안전한 축소 규모로 재현하는 게 목표.

## 시작점

- **[`CLAUDE.md`](CLAUDE.md)** — 현재 진행 상태 · 확정 방향 · 문서 맵 · 다음 액션. 새 세션은 이거 먼저.
- **[`docs/design/00-hopper-master-design.md`](docs/design/00-hopper-master-design.md)** — 마스터 설계도 (rev C)
- **[`docs/execution/week-01-kickoff.md`](docs/execution/week-01-kickoff.md)** — 1–2주차 실행 계획

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

```bash
cd sim/sim_stage1
python -m venv venv
venv\Scripts\activate            # Mac/Linux: source venv/bin/activate
pip install gymnasium stable-baselines3[extra] pyyaml numpy
python sanity_check.py
```

`환경 정상 동작 확인 완료`가 뜨면 끝. 안 뜨면 아래 [트러블슈팅](#트러블슈팅)부터 본다.

환경을 다 갖췄으면 `hopper_aviary.py`를 열어보고, AI에게 이렇게 물어본다 — 그냥 읽고 넘어가지 말고 답을 **자기 말로 3문장**으로 줄여 팀 채팅방에 올릴 것. 서로 다르게 요약된 지점이 팀이 헷갈리는 지점이다.

```
이건 1인용 EDF 호퍼의 자세 제어를 학습시키는
강화학습 환경 코드야. 초보자에게 세 가지를 설명해줘.
1) observation이 무엇이고 왜 6개인지
2) action 5개가 각각 물리적으로 뭘 움직이는지
3) reward 식이 어떤 행동을 장려하고 어떤 걸 벌하는지
전문용어는 처음 나올 때 풀어서 써줘.
```

작업 폴더: `sim/`(RL 환경·학습 스크립트), `firmware/cosmos/`(Teensy 스케치 — Arduino IDE + Teensyduino 필요, 펌웨어 담당만 설치하면 됨).

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

- **브랜치 없이 `main`에 직접 커밋**한다. 팀별로 작업 폴더가 나뉘어 있어 충돌이 거의 안 난다.
- **남의 폴더는 건드리지 않는다.** 소프트웨어팀은 `sim/`·`firmware/cosmos/`, 엔지니어링팀은 `cad/`·`data/`.
- **매 작업 전에 `git pull`부터.**
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
git pull
git add -A
git commit -m "[sim] params.yaml 추력 상수 실측값 반영"
git push
```

---

## 트러블슈팅

이 섹션은 계속 채워나간다 — 새로 겪은 오류와 해결법은 발견한 사람이 바로 여기 추가하고 `[docs]` 태그로 커밋할 것.

| 증상 | 원인 | 해결 |
|---|---|---|
| `python`, `pip` 명령이 안 먹음 | 설치 시 PATH 미등록 | 파이썬 재설치 시 "Add python.exe to PATH" 체크. 이미 설치했다면 제어판에서 python 재설치(Modify) |
| `venv\Scripts\activate` 실행 시 오류(실행 정책) | Windows 기본 PowerShell 스크립트 실행 제한 | PowerShell을 관리자로 열고 `Set-ExecutionPolicy RemoteSigned` 후 재시도, 또는 명령 프롬프트(cmd)에서 `venv\Scripts\activate.bat` 사용 |
| `sanity_check.py` 실행 시 `ModuleNotFoundError` | 가상환경 활성화 전에 `pip install` 했거나, 활성화가 안 된 상태로 실행 | 터미널 프롬프트 앞에 `(venv)`가 보이는지 확인 후 `pip install` 다시 |
| `git push` 시 로그인 창이 반복됨 | Git Credential Manager 인증 만료 | 뜨는 브라우저 창에서 GitHub 로그인 재시도. 안 뜨면 Settings → Developer settings → Personal access tokens에서 토큰 생성 후 비밀번호 칸에 붙여넣기 |
| Teensy 업로드 시 보드가 안 잡힘 | USB 드라이버 미인식 또는 프로그램 버튼 타이밍 | Teensyduino 재설치, 업로드 시작 직후 보드의 프로그램 버튼 눌러주기 |
| BNO085 값이 안 뜸 | I2C 배선 순서 또는 주소 문제 | I2C 스캔 스케치로 장치 인식 여부 확인(보통 `0x4A`/`0x4B`), SDA/SCL 순서 재확인 |

## 구조

| 폴더 | 내용 |
|---|---|
| `docs/design/` | 설계도 · BOM · 리서치 · 참고 논문 |
| `docs/execution/` | 주차별 계획 · 조달 · 배선도 |
| `docs/presentation/` | 동아리 설명회 발표자료 |
| `firmware/` | 펌웨어 — `reference/SingleRotorUAV/`는 [SolidGeek/SingleRotorUAV](https://github.com/SolidGeek/SingleRotorUAV) (MIT) vendor-copy, `cosmos/`는 우리 코드 |
| `cad/` | 자체 파라메트릭 CAD (대안 — 주 경로는 SolidGeek Onshape 포크) |
| `sim/` | 시뮬레이션 · RL — Stage 1 환경 + PPO 학습 1회 성공 완료 |
| `data/` | 실험 로그 (CSV) |

## 라이선스 / 출처

`firmware/reference/SingleRotorUAV/`는 Emil Jacobsen (Aalborg University)의 MIT 라이선스 프로젝트를
그대로 포함한 것 — 해당 폴더의 `LICENSE`·`ORIGIN.md` 참고. 그 외 이 저장소의 내용은 COSMOS 동아리 작업물.
