// COSMOS PRJ-01 · IMU 테스트 스케치
// BNO085 자세값(Roll/Pitch/Yaw)을 시리얼로 출력한다.
//
// 이 폴더의 BNO080.h / BNO080.cpp는 firmware/reference/SingleRotorUAV/src/에서
// 그대로 복사해온 것이다 — 새로 드라이버를 만들지 않고 이미 검증된 코드를 재사용한다.
// (Arduino IDE는 스케치 폴더 안에 있는 .h/.cpp만 같이 컴파일하기 때문에 복사가 필요함)
//
// 배선: Teensy 4.0 기본 I2C → SDA=핀18, SCL=핀19, 둘 다 3.3V (5V 절대 금지)

#include "BNO080.h"

BNO080 imu;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {
    // 시리얼 모니터가 열릴 때까지 최대 3초 대기 (없어도 진행됨)
  }

  Wire.begin();

  if (imu.begin() == false) {
    Serial.println("BNO085를 찾을 수 없음.");
    Serial.println("확인할 것: SDA=18, SCL=19 배선 / 3.3V·GND 연결 / I2C 주소(기본 0x4B)");
    while (1) {
      // 여기서 멈춤 — 배선부터 다시 확인
    }
  }

  imu.enableRotationVector(50); // 50ms마다 갱신 = 20Hz

  Serial.println("BNO085 연결 성공. Roll / Pitch / Yaw 를 도(degree) 단위로 출력합니다.");
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
