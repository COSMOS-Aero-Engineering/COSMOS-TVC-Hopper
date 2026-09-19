// COSMOS PRJ-01 · IMU 테스트 스케치 (SPI 모드)
// BNO085 자세값(Roll/Pitch/Yaw)을 시리얼로 출력한다.
//
// 이 폴더의 BNO080.h / BNO080.cpp는 firmware/reference/SingleRotorUAV/src/에서
// 그대로 복사해온 것이다 — 새로 드라이버를 만들지 않고 이미 검증된 코드를 재사용한다.
// (Arduino IDE는 스케치 폴더 안에 있는 .h/.cpp만 같이 컴파일하기 때문에 복사가 필요함)
//
// 2026-09-19: I2C(SDA=18/SCL=19) → SPI로 전환. 이유: 핀 18/19은 나중에 RC 수신기
// (CH1 스로틀·CH2 롤)가 써야 할 핀이라, I2C로 계속 가면 RC 연결할 때 충돌한다.
// docs/design/01-avionics-integration-final.md §2.2~2.4 확정 핀맵과 1:1로 맞춤.
//
// 배선(전부 3.3V 로직 — 5V 절대 금지):
//   BNO085(GY-BNO08X)   Teensy 4.0
//   ------------------  ----------
//   UCC (전원)      →   3.3V
//   GND             →   GND
//   CS              →   핀 10
//   INT             →   핀 21
//   RST             →   핀 20
//   PS0             →   핀 22   (WAKE 겸용 — 스톡 코드가 이 핀을 토글)
//   PS1             →   3.3V    (PS1:PS0 = 1:1 로 SPI 모드 고정)
//   SCL             →   핀 13   (SCK, 하드웨어 SPI 기본핀 — beginSPI() 가 자동으로 씀)
//   SDA             →   핀 11   (MOSI/SDI)
//   AD0             →   핀 12   (MISO/SDO — ⚠️ 확인 포인트: 이 보드는 I2C 주소선(AD0)을
//                                SPI 모드에서 MISO로 겸용하는 것으로 보임. 실제 실크·후면
//                                표기가 다르면 이 한 줄만 배선 바꾸면 됨, 나머지는 안 바뀜)
//
// 브레드보드에 이미 SDA/SCL 로 I2C 배선을 해놨다면, 그 두 선을 위 표대로 SCL→13,
// SDA→11 로 옮기고 CS/INT/RST/PS0/PS1 5개를 새로 추가하면 된다(AD0/GND/UCC는 그대로).

#include "BNO080.h"

// SPI 핀 4개(CS, WAK/PS0, INT, RST) — 위 배선표와 순서 일치.
BNO080 imu(/*CSPin=*/10, /*WAKPin=*/22, /*INTPin=*/21, /*RSTPin=*/20);

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {
    // 시리얼 모니터가 열릴 때까지 최대 3초 대기 (없어도 진행됨)
  }

  // beginSPI()는 인자 없이 호출 — CS/WAK/INT/RST 4개 핀은 위 생성자에서 이미 넘겼고,
  // beginSPI() 자체는 (속도, SPI객체)만 받는다(둘 다 기본값 사용: 3MHz, 하드웨어 SPI).
  if (imu.beginSPI() == false) {
    Serial.println("BNO085를 찾을 수 없음.");
    Serial.println("확인할 것: CS=10 SCK=13 MOSI=11 MISO=12 배선 / PS0=22 PS1=3V3(SPI 모드 고정) / 3.3V·GND 연결");
    while (1) {
      // 여기서 멈춤 — 배선부터 다시 확인
    }
  }

  imu.enableRotationVector(50); // 50ms마다 갱신 = 20Hz

  Serial.println("BNO085 연결 성공(SPI). Roll / Pitch / Yaw 를 도(degree) 단위로 출력합니다.");
  Serial.println("보드를 손으로 기울여보면서 부호와 축이 맞는지 확인할 것.");
}

void loop() {
  if (imu.dataAvailable()) {
    // 드라이버는 라디안으로 반환 → 사람이 읽기 쉽게 도(degree)로 변환
    float roll  = imu.getRoll()  * 180.0 / PI;
    float pitch = imu.getPitch() * 180.0 / PI;
    float yaw   = imu.getYaw()   * 180.0 / PI;

    Serial.print("Roll: ");
    Serial.print(roll, 1);
    Serial.print("\tPitch: ");
    Serial.print(pitch, 1);
    Serial.print("\tYaw: ");
    Serial.println(yaw, 1);
  }
}
