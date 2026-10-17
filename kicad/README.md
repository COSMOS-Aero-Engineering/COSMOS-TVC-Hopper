# kicad/ — 회로도(스키매틱) 캡처

## 현재 상태 (2026-10-17)

**스키매틱은 사람이 그린 파일이 아니라 생성물이다** — `cosmos-avionics/cosmos-avionics.kicad_sch` + `.kicad_pro`.
`01-avionics-integration-final.md` §2.2(Teensy 핀맵)·§3(전원계통)을 넷리스트로 옮긴 것. 부품 20개, 넷 30개, 배선 83개.
전부 `_tools/gen_schematic.py`가 만든다. 손으로 좌표를 찍은 곳이 없다(이 프로젝트의 "프리핸드 CAD 금지,
코드 기반 파라메트릭 우선" 원칙을 회로도에도 그대로 적용한 것).

**2026-10-17: ERC(전기 규칙 검사)를 처음으로 실제로 돌렸다**(이민우 PC, KiCad 10.0.6). 결과는 **오류 4개, 경고 129개**다.
리포트는 [`cosmos-avionics/cosmos-avionics-erc.rpt`](cosmos-avionics/cosmos-avionics-erc.rpt)에 있다.
종류별 판정은 아래 "2026-10-17 ERC 결과와 넷 대조" 절에 있다.

**⚠️ 같은 날 생성된 회로도를 넷리스트로 뽑아 대조한 결과, 생성기 결함 1건과 §2.2 표 불일치 10행을 찾았다.**
`_tools/gen_schematic.py`가 심볼 라이브러리 좌표를 회로도 좌표로 옮길 때 Y축 부호를 바꾸지 않아서, 핀 위치와
레이블이 부품마다 거울처럼 뒤집혀 있다. 그 결과 짝수 핀 커넥터의 마지막 핀이 연결되지 않고(ERC 오류 4개가
전부 이것), 레이블 순서가 `Value` 문자열과 어긋난다. **회로도를 손으로 고치지 않는다.** 고치는 일은 이슈 #66에서 한다.

자체 검사 스크립트 두 개 중 `check_imu_nets.py`는 생성기 원본만 보고, `validate_sch.py`의 넷 검사는 레이블
글자 수만 센다. **둘 다 생성된 `.kicad_sch`의 실제 연결을 보지 않는다.** 그래서 둘 다 "일치"로 나왔지만
실제로는 GND 1행이 끊겨 있었다. 자세한 내용은 아래 절에 있다.

## 왜 KiCad를 쓰나

이 프로젝트는 PCB를 새로 설계하지 않는다 — 아비오닉스는 만능기판(perfboard) 수작업 배선이 정본
(`docs/design/01-avionics-integration-final.md` §5). **KiCad는 새 회로를 설계하는 도구가 아니라, 이미
확정된 핀맵·배선을 정식 회로도로 문서화하는 도구**로 쓴다.

- 조립 중 오배선을 조기에 발견하는 대조 도구(전자 탑재 시 스키매틱과 실물 대조).
- 발표·인수인계 자료 — 다음 학기 팀이 마크다운 표 대신 정식 회로도로 배선을 볼 수 있음.
- (스트레치) rev D에서 실제 커스텀 PCB로 갈 경우의 출발점.

## 열어보는 법

1. KiCad 10 설치(무료, [kicad.org](https://www.kicad.org/)) — 이미 이 PC엔 설치돼 있음
   (`%LOCALAPPDATA%\Programs\KiCad\10.0\`).
2. `cosmos-avionics/cosmos-avionics.kicad_pro`를 더블클릭 → KiCad가 열림 → Eeschema(회로도 편집기)
   아이콘 클릭.
3. **회로도를 바꾼 뒤에는 Inspect → Electrical Rules Checker(ERC)를 돌린다.** kicad-cli로도 돌릴 수 있다
   (아래 "2026-10-17 ERC 결과와 넷 대조"). 여기서 나오는 오류·경고를 먼저 확인할 것.
4. 부품 20개가 격자로 나열돼 있음 — 예쁜 배치가 아니라 **넷 연결 확인용 1차 캡처**다. 팀에서 보기 좋게
   재배치해도 되고(같은 파일에 계속 편집), 그대로 둬도 넷 정보는 정확하다.

## 회로 구성 (`_tools/gen_schematic.py`에 넷리스트 그대로 있음)

Teensy 4.0·BNO085·MG90S 서보·FS-iA6B 수신기·ESC·UBEC·레벨시프터 전부 **공식 KiCad 심볼이 없어서**
`Connector_Generic:Conn_01xNN`(범용 핀헤더)로 대체 표시했다 — 각 부품의 `Value` 필드에 실제 정체를
적어뒀다(예: J6의 Value = "BNO085 IMU (CS,SCK,MOSI,MISO,INT,RST,WAK,PS1,VIN,GND)"). **핀 번호 자체는
의미 없고, 옆에 붙은 넷 이름(레이블)이 실제 신호다** — `01-avionics-integration-final.md` §2.2 표와
1:1 대조 가능. 다만 `Value` 문자열이 나열한 순서와 화면의 핀 순서는 맞아야 한다. 2026-10-17에 이 순서가
뒤집힌 것을 찾았다(아래 "생성기 결함").

| 부품 | 대응 |
|---|---|
| J1~J5 | Teensy 4.0의 기능별 핀 그룹(서보출력·RC입력·IMU SPI·DShot·전원) |
| J6 | BNO085 IMU |
| U1, U2 | 레벨시프터 #1(CH1,2) · #2(CH3,4,5) |
| J7 | FS-iA6B 수신기 |
| S1~S4 | MG90S 서보 ×4 |
| ESC1, M1 | ESC · EDF 모터 |
| U3, C1, C2 | UBEC · 캐패시터 2개 |
| SW1, BT1 | 킬스위치 · 4S LiPo |

## 2026-10-17 ERC 결과와 넷 대조

돌린 명령 (이민우 PC, KiCad 10.0.6):

```bash
kicad-cli sch erc --output kicad/cosmos-avionics/cosmos-avionics-erc.rpt \
  kicad/cosmos-avionics/cosmos-avionics.kicad_sch
kicad-cli sch export netlist --output netlist.net \
  kicad/cosmos-avionics/cosmos-avionics.kicad_sch
```

### ERC 결과 — 오류 4개, 경고 129개

| 종류 | 개수 | 등급 | 실제 문제인가 | 이유 |
|---|---|---|---|---|
| `pin_not_connected` | 4 | 오류 | **그렇다** | J1 4번, U1 6번, U2 8번, J6 10번이 어떤 배선에도 닿지 않는다. 아래 생성기 결함 때문이다. |
| `unconnected_wire_endpoint` | 4 | 경고 | **그렇다** | 위 4개 핀으로 가야 할 배선 4개가 허공에서 끝난다. 같은 원인이다. |
| `isolated_pin_label` | 2 | 경고 | **그렇다** | `SERVO4_RIGHT` 레이블이 붙은 넷에 핀이 S4 하나뿐이다. J1 쪽 배선이 끊겨 있어서다. |
| `endpoint_off_grid` | 103 | 경고 | 아니다 | 부품 원점이 1.27 mm 격자 밖에 있다(예: y = 25.00). 우리는 PCB를 만들지 않고 문서로만 쓰므로 전기적 문제가 아니다. 다만 소음이 크다. |
| `lib_symbol_issues` | 20 | 경고 | 아니다 | 심볼 라이브러리 `Connector_Generic`·`Device`·`Switch`가 프로젝트 설정에 없다는 경고다. 심볼 정의는 `.kicad_sch` 안에 들어 있어 ERC가 정상으로 읽는다. |

**`J6 Pin 10`의 정체:** `gen_schematic.py`에서 J6 10번은 BNO085의 **GND**다. 그런데 생성된 회로도에서 이 핀은
비어 있다. 즉 회로도에 BNO085의 GND 연결이 없다. 안 쓰는 핀이 아니라 실수로 빠진 것이다.

### 넷 대조 — §2.2 표 10행

`check_imu_nets.py`는 생성기 **원본**만 본다. 실제 `.kicad_sch`는 `kicad-cli sch export netlist`로 확인했다.
두 결과가 다르다. 아래는 생성된 회로도 기준 판정이다. 괄호 안은 그 자리가 `Value` 문자열상 몇 번 핀인지다.

| 신호 | Teensy 핀(§2.2) | 회로도에서 레이블이 붙은 자리 | 넷 이름 | 판정 |
|---|---|---|---|---|
| CS | 10 | J3 7번(D22 자리) · J6 9번(VIN 자리) | `IMU_CS` | 불일치 |
| SCK | 13 | J3 4번(D13 자리) · J6 8번(PS1 자리) | `IMU_SCK` | 불일치 |
| MOSI | 11 | J3 6번(D21 자리) · J6 7번(WAK 자리) | `IMU_MOSI` | 불일치 |
| MISO | 12 | J3 5번(D20 자리) · J6 6번(RST 자리) | `IMU_MISO` | 불일치 |
| RST | 20 | J3 3번(D12 자리) · J6 4번(MISO 자리) | `IMU_RST` | 불일치 |
| INT | 21 | J3 2번(D11 자리) · J6 5번(INT 자리) | `IMU_INT` | 불일치 |
| WAK/PS0 | 22 | J3 1번(D10 자리) · J6 3번(MOSI 자리) | `IMU_WAK` | 불일치 |
| PS1 | 3V3 | J6 2번(SCK 자리) | `+3V3` | 불일치 |
| VIN | 3V3 | J6 1번(CS 자리) | `+3V3` | 불일치 |
| GND | G | 없음(J6 10번에 레이블이 없다) | 없음 | 불일치 |

- 넷 이름 자체는 10행 모두 맞다. `IMU_CS`는 `IMU_CS`끼리 이어진다. J3와 J6가 둘 다 뒤집혀서 넷의 짝은 살아 있다.
- 그래서 연결만 보면 9행이 맞다. 그러나 화면에서 각 레이블이 붙은 **핀 번호 자리**가 전부 다르고, GND 한 행은
  연결 자체가 없다. 조립할 때 이 회로도를 펴 놓고 배선하면 순서를 반대로 읽게 된다.
- `check_imu_nets.py`가 "10행 모두 일치"로 나온 이유는 그 스크립트가 `gen_schematic.py`의 `COMPONENTS`만 읽기
  때문이다. 생성된 `.kicad_sch`를 읽지 않는다. `validate_sch.py`의 넷 검사도 레이블 글자 수만 세므로
  `SERVO4_RIGHT`를 2개로 세고 통과시킨다.

### 화면 증거

**KiCad GUI(Eeschema)를 열어 찍은 스크린샷이다.** 2026-10-17, 이민우 PC.

- [`cosmos-avionics/gui-eeschema-2026-10-17.png`](cosmos-avionics/gui-eeschema-2026-10-17.png) — Eeschema 창 전체
- [`cosmos-avionics/gui-sch-j3-j6-2026-10-17.png`](cosmos-avionics/gui-sch-j3-j6-2026-10-17.png) — J3·J6 확대. J6 10번에 레이블이 없는 것이 보인다.
- [`cosmos-avionics/gui-inspect-menu-2026-10-17.png`](cosmos-avionics/gui-inspect-menu-2026-10-17.png) — 검사(I) 메뉴의 "전기 규칙 검사자 (ERC)"

`kicad-cli`가 그린 렌더도 함께 남긴다. 넷리스트 대조를 할 때 쓴 그림이다.

- [`cosmos-avionics/sch-2026-10-17-j3-j6.png`](cosmos-avionics/sch-2026-10-17-j3-j6.png) — J3(Teensy IMU 핀)과 J6(BNO085)
- [`cosmos-avionics/sch-2026-10-17-j1.png`](cosmos-avionics/sch-2026-10-17-j1.png) — J1(서보 출력) 4번 핀 누락

**GUI에서 ERC를 자동으로 실행하지는 못했다.** 검사(I) 메뉴에 "전기 규칙 검사자 (ERC)" 항목이 있는 것까지
확인했고, 실제 ERC는 `kicad-cli`로 돌렸다(같은 엔진). GUI로도 한 번 돌려 같은 결과(오류 4개·경고 129개)가
나오는지 사람이 확인하면 좋다.

### 생성기 결함 (이슈 #66)

`_tools/gen_schematic.py`가 심볼 라이브러리 좌표를 회로도 좌표로 그대로 쓴다. 심볼 라이브러리는 Y가 위로
커지고 회로도는 Y가 아래로 커진다. 그래서 배선과 레이블이 핀의 실제 위치가 아니라 원점 기준으로 뒤집힌
자리에 그려진다.

- `Conn_01x10` 1번 핀의 로컬 좌표는 `y = +10.16`이다. J6 원점이 `y = 105`이므로 실제 1번 핀은 `105 - 10.16 = 94.84`에 있다.
- 생성기는 `105 + 10.16 = 115.16`에 배선을 그린다. 그 자리는 9번 핀 자리다.
- ERC 리포트가 이 계산을 확인해 준다. KiCad는 J1 4번 핀을 `(19.92, 30.08)`에 두는데 생성기가 그린 배선 끝은 `(19.92, 19.92)`다.

## 알려진 문제 — 김민찬 PC에서 kicad-cli가 죽는다 (이민우 PC에서는 해결)

김민찬 PC에서 `kicad-cli.exe`가 `C:\Users\mimin\Documents\KiCad` 폴더를 만들지 못해 크래시했다. 원인은
Windows Controlled Folder Access(랜섬웨어 방지)가 `Documents` 폴더를 보호하고 있어서다
(`Get-MpPreference`로 확인). **이민우 PC에는 이 문제가 없어서 2026-10-17에 ERC를 돌렸다.**

김민찬 PC에서도 돌리려면 둘 중 하나를 한다(사람이 해야 함):

1. 파일 탐색기로 `C:\Users\mimin\Documents\KiCad` 폴더를 직접 만든다.
2. Windows 보안 → 바이러스 및 위협 방지 → 랜섬웨어 방지 → 폴더 액세스 제어에서 `kicad-cli.exe`·`kicad.exe`를 허용 목록에 넣는다.

## 재생성 방법 (핀맵이 바뀌면)

`01-avionics-integration-final.md` §2.2·§3이 바뀌면, `_tools/gen_schematic.py`의 `COMPONENTS` 리스트만
고치고 다시 실행하면 된다 — 손으로 `.kicad_sch`를 고치지 않는다(파라메트릭 CAD와 같은 원칙).

```bash
cd kicad/_tools
python gen_schematic.py     # cosmos-avionics.kicad_sch 재생성
python validate_sch.py <저장소 루트>/kicad/cosmos-avionics/cosmos-avionics.kicad_sch   # 구조 자체검증
```

`validate_sch.py`는 인자를 주지 않으면 작성자 PC의 절대경로를 쓴다(이슈 #67). 인자로 `.kicad_sch` 경로를 넘긴다.
이 스크립트의 검사는 문법 수준이다 — 괄호 균형, `lib_id` 선언, UUID 중복. **넷 검사는 레이블 글자 수를 세는
것이라 실제 연결을 보지 않는다.** 연결을 확인하려면 `kicad-cli sch export netlist`와 ERC를 돌린다.

`_tools/extract_symbols.py`는 KiCad 번들 심볼 라이브러리에서 실제 심볼 정의·핀 좌표를 그대로
추출하는 유틸 — 좌표를 손으로 베끼지 않으려고 만든 것(정확성 확보).

## 다음 단계

1. **생성기 Y축 결함을 고치고 회로도를 다시 만든 뒤 ERC를 다시 돌린다** — 이슈 #66.
2. `_tools` 스크립트의 절대경로를 없앤다 — 이슈 #67.
3. 김민찬 PC에서도 ERC를 돌려 같은 결과인지 확인한다 — 위 "알려진 문제" 참고.
4. Eeschema에서 열어 보기 좋게 재배치(선택 — 넷 정보엔 영향 없음).
5. 실물 조립(전자 탑재, `semester-roadmap.md` Week 4-5) 때 이 스키매틱과 실제 배선 대조.
6. 커밋 태그: `[kicad]`(회로도 단독 변경). 전자 회로도를 기구와 함께 다룰 때는 `[cad]`.
