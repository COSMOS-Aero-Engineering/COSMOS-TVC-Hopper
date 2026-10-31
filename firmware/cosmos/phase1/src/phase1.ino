// COSMOS PRJ-01 · PHASE 1 롤 PD 스케치 (모터·ESC 없음)
// IMU(BNO085, I2C) 롤 각도를 읽어 서보 1개(Teensy 핀 2)에 PD 제어로 펄스폭을 낸다.
// 선행 이슈: #235(서보 단독), #238(IMU 부호), #245(IMU 연결 방식).
//
// 제어 법칙:
//   펄스폭 = 1500 µs + P_GAIN_US_PER_DEG × 롤[deg] + D_GAIN_US_PER_DEGPERSEC × 롤속도[deg/s]
//   롤속도는 직전 샘플과 미분으로 구한다.
//   출력은 1500 ± OUTPUT_LIMIT_US 안으로 클램프한다(초기 ±100 µs, #243 보정 전 보수값).
//
// 배선(01-avionics-integration-final.md §2.2):
//   서보 1 신호선 → Teensy 핀 2
//   서보 GND ↔ Teensy GND (공통), 서보 5V → USB 5V(VUSB)
//   BNO085: VCC→3.3V, GND→GND, SDA→18, SCL→19 (나머지 핀 비움, 모듈 기본 I2C 0x4B)
//
// 출력 형식(기록용): D,<millis>,<roll_deg>,<servo_us>
//   사람용 메시지는 '#'로 시작한다.
//
// 안전:
//   EDF·ESC는 연결하지 않는다.
//   첫 명령 전에는 서보 펄스를 내지 않는다(attach는 처음 출력 시점에).
//   서보가 떨리거나 소리가 나면 게인을 낮추거나 USB를 뽑는다.

#include <Arduino.h>
#include <Wire.h>
#include <Servo.h>
#include "BNO080.h"

// --- 하드웨어 핀 ---
static constexpr uint8_t SERVO_PIN = 2;   // 서보 1 신호선 (01 문서 §2.2)
static constexpr uint8_t I2C_SDA = 18;    // BNO085 SDA/MISO/TX
static constexpr uint8_t I2C_SCL = 19;    // BNO085 SCL/SCK/RX

// --- 제어 상수 (추후 #243 서보 보정 이후 조정) ---
static constexpr float   NEUTRAL_US        = 1500.0f;  // 중립 펄스폭 µs
static constexpr float   P_GAIN_US_PER_DEG = 4.0f;     // 롤 1°당 µs (초기값, 작게 시작)
static constexpr float   D_GAIN_US_PER_DEGPERSEC = 2.0f; // 롤속도 1°/s당 µs (초기값)
static constexpr float   OUTPUT_LIMIT_US   = 100.0f;   // 중립에서 최대 편차 µs (보수값)
static constexpr uint16_t REPORT_PERIOD_MS = 50;       // IMU 리포트 주기 ms

// --- 상태 ---
BNO080 imu(255, 255, 255, 255);
Servo  servo1;
uint8_t foundAddr = 0;
bool   imuReady = false;
bool   servoAttached = false;

unsigned long prevMillis = 0;
float   prevRollDeg = 0.0f;
bool   hasPrevRoll = false;

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

void releaseServo(const char* reason) {
  if (servo1.attached()) {
    servo1.detach();
    digitalWrite(SERVO_PIN, LOW);
  }
  servoAttached = false;
  Serial.print("# OFF: ");
  Serial.println(reason);
}

float clampUs(float us) {
  float lo = NEUTRAL_US - OUTPUT_LIMIT_US;
  float hi = NEUTRAL_US + OUTPUT_LIMIT_US;
  if (us < lo) us = lo;
  if (us > hi) us = hi;
  return us;
}

void applyServo(float rollDeg, float rollRateDegPerS) {
  float outUs = NEUTRAL_US + P_GAIN_US_PER_DEG * rollDeg + D_GAIN_US_PER_DEGPERSEC * rollRateDegPerS;
  outUs = clampUs(outUs);

  if (!servoAttached) {
    servo1.attach(SERVO_PIN, 1000, 2000);
    servoAttached = true;
  }
  servo1.writeMicroseconds((int)outUs);

  Serial.print("D,");
  Serial.print(millis());
  Serial.print(',');
  Serial.print(rollDeg, 1);
  Serial.print(',');
  Serial.println((int)outUs);
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {}

  Wire.begin();
  delay(200);

  Serial.println("# COSMOS PHASE 1 롤 PD (모터·ESC 없음)");
  Serial.print("# 서보 핀: "); Serial.println(SERVO_PIN);
  Serial.print("# P 게인: "); Serial.print(P_GAIN_US_PER_DEG); Serial.println(" µs/deg");
  Serial.print("# D 게인: "); Serial.print(D_GAIN_US_PER_DEGPERSEC); Serial.println(" µs/(deg/s)");
  Serial.print("# 출력 제한: ±"); Serial.print(OUTPUT_LIMIT_US); Serial.println(" µs");
  Serial.println("# D,millis,roll_deg,servo_us");
  Serial.println("# 보드를 기울여 서보가 롤을 줄이는 쪽으로 움직이는지 확인한다");
}

void loop() {
  unsigned long now = millis();

  // IMU 초기화(스캔 + begin + enableRotationVector)
  if (!imuReady) {
    if (!foundAddr) {
      scanBus();
    }
    if (foundAddr && imu.begin(foundAddr)) {
      imu.enableRotationVector(REPORT_PERIOD_MS);
      imuReady = true;
      Serial.print("BNO085 OK at 0x"); Serial.println(foundAddr, HEX);
    } else {
      foundAddr = 0;
      Serial.println("BNO085 not ready, rescan in 2s");
      delay(2000);
    }
    return;
  }

  // IMU 데이터가 있을 때만 제어 수행
  if (imu.dataAvailable() && (now - prevMillis >= REPORT_PERIOD_MS)) {
    float rollDeg = imu.getRoll() * 180.0 / PI;

    float rollRateDegPerS = 0.0f;
    if (hasPrevRoll) {
      float dt = (now - prevMillis) / 1000.0f;
      if (dt > 0.0f) {
        rollRateDegPerS = (rollDeg - prevRollDeg) / dt;
      }
    }

    applyServo(rollDeg, rollRateDegPerS);

    prevRollDeg = rollDeg;
    hasPrevRoll = true;
    prevMillis = now;
  }
}
