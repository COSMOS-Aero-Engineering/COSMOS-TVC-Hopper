# #26 KiCad IMU 넷 대조와 ERC (이민우)

> **2026-10-17 완료.** ERC를 돌려 오류 4개·경고 129개를 기록했고, 생성된 회로도를 넷리스트로 대조해
> §2.2 표 10행이 모두 불일치임을 찾았다(넷 이름은 맞고 레이블이 붙은 핀 자리가 뒤집혔다. GND 1행은
> 연결 자체가 없다). 원인은 `gen_schematic.py`의 Y축 반전 결함이다. 이 결함은 부품 20개 모두에 걸리고,
> **배터리·UBEC·Teensy 전원·ESC의 극성이 반대가 된다(그대로 배선하면 기판이 탄다).** 결과와 판정은
> [`kicad/README.md`](../../kicad/README.md)의 "2026-10-17 ERC 결과와 넷 대조" 절에 있고,
> 결함 수정은 이슈 #66, 도구 경로 하드코딩은 #67에서 없앴다(10/17). KiCad GUI(Eeschema)를 열어 J3·J6 화면을 찍은
> 스크린샷도 `kicad/cosmos-avionics/`에 남겼다. 펌웨어 핀 표 교차확인은 이슈 #89로 옮겼다.

## 지금 상태

- 회로도 `kicad/cosmos-avionics/cosmos-avionics.kicad_sch`는 사람이 그린 게 아니라 `kicad/_tools/gen_schematic.py`가 만든 파일이다. 부품 20개, 넷 30개.
- KiCad에 Teensy·BNO085 전용 심볼이 없어서 범용 커넥터 심볼로 대신했다. **핀 번호보다 옆의 넷 이름(레이블)이 실제 신호다.** 단, 지금 회로도는 레이블이 뒤집혀 있으므로 이 규칙으로 읽으면 오배선한다(맨 위 안내 참고).
- ~~실제 KiCad ERC(전기 규칙 검사)는 아직 아무도 돌리지 못했다.~~ **10/17 이민우 PC에서 실행 완료(맨 위 안내 참고).** 김민찬 PC에서는 Windows 랜섬웨어 보호 기능 때문에 `kicad-cli`가 죽는다(`kicad/README.md` "알려진 문제").

## 용어

- **넷(net):** 전기적으로 이어진 점들의 묶음. 이름이 같은 레이블은 선이 없어도 연결된 것으로 본다.
- **SPI:** IMU와 Teensy가 데이터를 주고받는 4선 방식. CS(선택), SCK(클록), MOSI(Teensy→IMU), MISO(IMU→Teensy).
- **실크:** 모듈 기판에 인쇄된 핀 이름. 우리 GY-BNO08X 모듈은 한 핀에 이름이 여러 개다(SDA/MISO/TX 등).
- **ERC:** KiCad가 "출력끼리 붙었다", "연결 안 된 핀" 같은 규칙 위반을 찾는 검사.

## 미리 만든 것

[`kicad/_tools/check_imu_nets.py`](../../kicad/_tools/check_imu_nets.py)는 회로도를 만드는 원본(`gen_schematic.py`)에서 IMU 관련 넷을 읽어, 01 문서 §2.2 핀맵과 실물 실크를 한 표로 대조한다. KiCad가 없어도 돈다.

2026-10-16 결과: **원본 스크립트 기준 10행 모두 일치.** PRD #26 6절 표의 "회로도 결과" 칸을 원본 기준으로는 채운 셈이다. **→ 10/17 정정: 원본은 맞지만 생성된 `.kicad_sch`는 다르다(맨 위 안내 참고).**

## 첫 30분

```bash
python kicad/_tools/check_imu_nets.py
```

정상 결과는 10행이 전부 "일치"인 표다. 그다음 KiCad로 `kicad/cosmos-avionics/cosmos-avionics.kicad_pro`를 열고, 회로도 편집기에서 J6(BNO085) 심볼을 찾아 핀 옆 레이블을 표와 하나씩 비교한다.

## 이어서 할 일

1. **회로도 실물 대조:** ~~스크립트는 원본을 본 것이고, 실제 `.kicad_sch` 화면은 사람이 봐야 한다.~~ **10/17 완료:** Eeschema로 열어 J3·J6 화면을 찍었다(`kicad/cosmos-avionics/gui-sch-j3-j6-2026-10-17.png`). 화면에서도 J6 10번에 레이블이 없고 레이블 순서가 모듈 실크와 뒤집혀 있다.
2. **ERC:** ~~Inspect → Electrical Rules Checker.~~ **10/17 완료(CLI):** `kicad-cli sch erc`로 돌렸다. GUI의 검사(I) → 전기 규칙 검사자 (ERC) 항목이 있는 것까지 확인했지만 GUI 자동 실행은 실패했다. GUI로도 한 번 돌려 같은 값(오류 4개·경고 129개)이 나오는지 사람이 확인한다.
3. **불일치가 있으면** 회로도를 손으로 고치지 않는다. 목록만 남기고 `gen_schematic.py`를 고쳐 다시 생성하는 방향을 김민찬과 정한다(`kicad/README.md` "재생성 방법").
4. **김시우와 교차 확인:** 펌웨어 `firmware/cosmos/imu_test/src/imu_test.ino`의 핀 정의가 같은 표와 맞는지 같이 본다. **10/17에 이 항목만 남아서 이슈 #89로 옮겼다**(AI 대조는 끝났고 사람 확인이 남았다).
5. **PR:** `[kicad] BNO085 SPI 넷 대조와 ERC 결과`. 스크립트 출력, 화면 캡처, ERC 결과 파일 또는 실패 기록.

## 확인 못 한 것

- ~~실제 `.kicad_sch`를 KiCad 화면에서 열어 본 대조와 ERC는 하지 않았다.~~ 10/17 Eeschema 화면 캡처와 CLI ERC를 했다. **남은 것: GUI에서 ERC를 열어 오류 4개·경고 129개가 같은지 눈으로 확인하는 일(사람 필요).**
- 펌웨어 핀 표 대조를 김시우가 확인하는 일은 이슈 #89로 옮겼다.
- ~~`gen_schematic.py`는 KiCad 설치 경로가 코드에 고정돼 있어 다른 PC에서 재생성하려면 `KICAD` 경로를 바꿔야 한다.~~ 10/17 이슈 #67에서 경로를 없앴다. 이제 어느 PC에서든 저장소 루트에서 두 스크립트가 돈다.
