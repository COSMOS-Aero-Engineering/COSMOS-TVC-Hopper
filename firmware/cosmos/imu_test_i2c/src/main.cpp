// COSMOS PRJ-01 · IMU I2C 브링업 스케치
// 배선(3.3V만, 5V 금지):  Teensy 3V→VCC_3V3, G→GND, 19→SCL/SCK/RX, 18→SDA/MISO/TX
// 나머지 모듈 핀(ADDR/MOSI, CS, INT, RST, PS1, PS0)은 비워둔다 — 모듈 기본값이 I2C, 주소 0x4B.
// I2C 버스를 스캔해서 0x4A/0x4B 중 응답하는 주소로 붙고, 못 찾으면 2초마다 재시도한다.
#include <Arduino.h>
#include <Wire.h>
#include "BNO080.h"

BNO080 imu(255, 255, 255, 255);
uint8_t foundAddr = 0;

void scanBus() {
  Serial.println("I2C scan (SDA=18, SCL=19):");
  int n = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.print("  found 0x"); Serial.println(a, HEX);
      if (a == 0x4A || a == 0x4B) foundAddr = a;
      n++;
    }
  }
  if (n == 0) Serial.println("  nothing found");
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {}
  Wire.begin();
  delay(200);
}

void loop() {
  if (!foundAddr) {
    scanBus();
    if (foundAddr && imu.begin(foundAddr)) {
      imu.enableRotationVector(50);
      Serial.print("BNO085 OK at 0x"); Serial.println(foundAddr, HEX);
    } else {
      foundAddr = 0;
      Serial.println("BNO085 not ready, rescan in 2s");
      delay(2000);
    }
    return;
  }
  if (imu.dataAvailable()) {
    Serial.print("Roll: ");   Serial.print(imu.getRoll()  * 180.0 / PI, 1);
    Serial.print("\tPitch: "); Serial.print(imu.getPitch() * 180.0 / PI, 1);
    Serial.print("\tYaw: ");   Serial.println(imu.getYaw()   * 180.0 / PI, 1);
  }
}
