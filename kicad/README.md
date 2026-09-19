# kicad/ — 회로도(스키매틱) 캡처

## 현재 상태 (2026-09-18)

**스키매틱 실제로 생성 완료** — `cosmos-avionics/cosmos-avionics.kicad_sch` + `.kicad_pro`.
`01-avionics-integration-final.md` §2.2(Teensy 핀맵)·§3(전원계통)을 그대로 넷리스트로 옮긴 것.
부품 20개, 넷 30개, 배선 83개 — 전부 스크립트로 생성(`_tools/gen_schematic.py`), 손으로 좌표를
찍은 게 하나도 없다(이 프로젝트의 "프리핸드 CAD 금지, 코드 기반 파라메트릭 우선" 원칙을 회로도에도
그대로 적용한 것).

**⚠️ 실제 KiCad ERC(오류검사)는 아직 못 돌렸다 — 이 PC의 환경 문제 때문**(아래 "알려진 문제" 참고).
대신 자체 구조 검증 스크립트(`_tools/validate_sch.py`)로 확인한 것: 괄호 균형 OK, 모든 `lib_id`가
`lib_symbols`에 실제로 선언돼 있음, UUID 중복 없음, 30개 넷 전부 연결점 2개 이상(끊어진 넷 없음).
**이건 "문법이 깨지지 않았다"는 확인이지 "회로가 맞다"는 확인이 아니다** — 진짜 ERC는 KiCad GUI로
열어서 돌려야 한다.

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
3. **처음 열면 반드시 Inspect → Electrical Rules Checker(ERC) 실행** — 아직 아무도 실제로 돌려본 적이
   없다(아래 "알려진 문제" 때문에 이 세션에서 CLI로는 못 돌렸음). 여기서 나오는 오류·경고를 먼저 확인할 것.
4. 부품 20개가 격자로 나열돼 있음 — 예쁜 배치가 아니라 **넷 연결 확인용 1차 캡처**다. 팀에서 보기 좋게
   재배치해도 되고(같은 파일에 계속 편집), 그대로 둬도 넷 정보는 정확하다.

## 회로 구성 (`_tools/gen_schematic.py`에 넷리스트 그대로 있음)

Teensy 4.0·BNO085·MG90S 서보·FS-iA6B 수신기·ESC·UBEC·레벨시프터 전부 **공식 KiCad 심볼이 없어서**
`Connector_Generic:Conn_01xNN`(범용 핀헤더)로 대체 표시했다 — 각 부품의 `Value` 필드에 실제 정체를
적어뒀다(예: J6의 Value = "BNO085 IMU (CS,SCK,MOSI,MISO,INT,RST,WAK,PS1,VIN,GND)"). **핀 번호 자체는
의미 없고, 옆에 붙은 넷 이름(레이블)이 실제 신호다** — `01-avionics-integration-final.md` §2.2 표와
1:1 대조 가능.

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

## 알려진 문제 — kicad-cli가 이 PC에서 죽는다

`kicad-cli.exe`(그리고 아마 `kicad.exe`도 처음 실행 시)가 **`C:\Users\mimin\Documents\KiCad` 폴더를
못 만들어서 크래시**한다. 원인 확인함: **Windows Controlled Folder Access(랜섬웨어 방지)가 켜져 있고
(`Get-MpPreference`로 확인, `EnableControlledFolderAccess=1`), `Documents` 폴더를 보호 대상으로 잡고
있어서 kicad-cli를 포함한 모든 프로세스의 쓰기를 막고 있다.** 이건 보안 설정이라 AI가 직접 끄지 않았다.

**해결 방법 (둘 중 하나, 사람이 해야 함)**:
1. 가장 간단: **파일 탐색기로 `C:\Users\mimin\Documents\KiCad` 폴더를 직접 만든다** — 탐색기는 보통
   CFA 허용 목록에 있어서 이 한 폴더만 만들어두면 kicad-cli가 그 안에 쓰기만 하면 되니 넘어갈 수 있음
   (스크립트/터미널로는 이 폴더 생성 자체가 막혀서 이번 세션에서 못 했다 — 직접 테스트해봄, `mkdir`도
   `New-Item`도 전부 조용히 실패).
2. Windows 보안 → 바이러스 및 위협 방지 → 랜섬웨어 방지 → 폴더 액세스 제어에서 `kicad-cli.exe`·
   `kicad.exe`를 허용 목록에 추가(또는 일시적으로 기능 끄기).

이 중 하나를 하고 나면 `kicad-cli.exe sch erc kicad/cosmos-avionics/cosmos-avionics.kicad_sch` 로
진짜 ERC를 돌릴 수 있다 — 그때 결과를 이 문서에 반영할 것.

## 재생성 방법 (핀맵이 바뀌면)

`01-avionics-integration-final.md` §2.2·§3이 바뀌면, `_tools/gen_schematic.py`의 `COMPONENTS` 리스트만
고치고 다시 실행하면 된다 — 손으로 `.kicad_sch`를 고치지 않는다(파라메트릭 CAD와 같은 원칙).

```bash
cd kicad/_tools
python gen_schematic.py     # cosmos-avionics.kicad_sch 재생성
python validate_sch.py      # 구조 자체검증(문법/넷 연결)
```

`_tools/extract_symbols.py`는 KiCad 번들 심볼 라이브러리에서 실제 심볼 정의·핀 좌표를 그대로
추출하는 유틸 — 좌표를 손으로 베끼지 않으려고 만든 것(정확성 확보).

## 다음 단계

1. **Documents\KiCad 폴더 문제 해결 후 진짜 ERC 실행** — 위 "알려진 문제" 참고.
2. Eeschema에서 열어 보기 좋게 재배치(선택 — 넷 정보엔 영향 없음).
3. 실물 조립(전자 탑재, `semester-roadmap.md` Week 4~5) 때 이 스키매틱과 실제 배선 대조.
4. 커밋 태그: `[cad]` (전자 회로도도 기구·전자팀 소관, `README.md` 협업 규칙 참고).
