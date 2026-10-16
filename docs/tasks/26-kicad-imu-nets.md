# #26 KiCad IMU 넷 대조와 ERC (이민우)

## 지금 상태

- 회로도 `kicad/cosmos-avionics/cosmos-avionics.kicad_sch`는 사람이 그린 게 아니라 `kicad/_tools/gen_schematic.py`가 만든 파일이다. 부품 20개, 넷 30개.
- KiCad에 Teensy·BNO085 전용 심볼이 없어서 범용 커넥터 심볼로 대신했다. **핀 번호보다 옆의 넷 이름(레이블)이 실제 신호다.**
- 실제 KiCad ERC(전기 규칙 검사)는 아직 아무도 돌리지 못했다. 김민찬 PC에서는 Windows 랜섬웨어 보호 기능 때문에 `kicad-cli`가 죽는다(`kicad/README.md` "알려진 문제"). 다른 PC에서는 될 수 있다.

## 용어

- **넷(net):** 전기적으로 이어진 점들의 묶음. 이름이 같은 레이블은 선이 없어도 연결된 것으로 본다.
- **SPI:** IMU와 Teensy가 데이터를 주고받는 4선 방식. CS(선택), SCK(클록), MOSI(Teensy→IMU), MISO(IMU→Teensy).
- **실크:** 모듈 기판에 인쇄된 핀 이름. 우리 GY-BNO08X 모듈은 한 핀에 이름이 여러 개다(SDA/MISO/TX 등).
- **ERC:** KiCad가 "출력끼리 붙었다", "연결 안 된 핀" 같은 규칙 위반을 찾는 검사.

## 미리 만든 것

[`kicad/_tools/check_imu_nets.py`](../../kicad/_tools/check_imu_nets.py)는 회로도를 만드는 원본(`gen_schematic.py`)에서 IMU 관련 넷을 읽어, 01 문서 §2.2 핀맵과 실물 실크를 한 표로 대조한다. KiCad가 없어도 돈다.

2026-10-16 결과: **원본 스크립트 기준 10행 모두 일치.** PRD #26 6절 표의 "회로도 결과" 칸을 원본 기준으로는 채운 셈이다.

## 첫 30분

```bash
python kicad/_tools/check_imu_nets.py
```

정상 결과는 10행이 전부 "일치"인 표다. 그다음 KiCad로 `kicad/cosmos-avionics/cosmos-avionics.kicad_pro`를 열고, 회로도 편집기에서 J6(BNO085) 심볼을 찾아 핀 옆 레이블을 표와 하나씩 비교한다.

## 이어서 할 일

1. **회로도 실물 대조:** 스크립트는 원본을 본 것이고, 실제 `.kicad_sch` 화면은 사람이 봐야 한다. J3(Teensy IMU 핀)와 J6의 레이블이 표와 같은지 확인하고 화면 캡처를 남긴다.
2. **ERC:** Inspect → Electrical Rules Checker. 오류·경고 수와 내용을 그대로 적는다. 범용 커넥터 심볼은 핀 종류가 "passive"라서 "출력 없음" 경고가 많이 날 수 있다. 경고마다 실제 문제인지 이유를 적는다. 실행이 안 되면 오류 메시지를 그대로 남긴다.
3. **불일치가 있으면** 회로도를 손으로 고치지 않는다. 목록만 남기고 `gen_schematic.py`를 고쳐 다시 생성하는 방향을 김민찬과 정한다(`kicad/README.md` "재생성 방법").
4. **김시우와 교차 확인:** 펌웨어 `firmware/cosmos/imu_test/src/imu_test.ino`의 핀 정의가 같은 표와 맞는지 같이 본다.
5. **PR:** `[kicad] BNO085 SPI 넷 대조와 ERC 결과`. 스크립트 출력, 화면 캡처, ERC 결과 파일 또는 실패 기록.

## 확인 못 한 것

- 실제 `.kicad_sch`를 KiCad 화면에서 열어 본 대조와 ERC는 하지 않았다.
- `gen_schematic.py`는 KiCad 설치 경로가 코드에 고정돼 있어 다른 PC에서 재생성하려면 `KICAD` 경로를 바꿔야 한다.
