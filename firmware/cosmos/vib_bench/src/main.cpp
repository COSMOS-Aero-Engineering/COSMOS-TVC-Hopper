// COSMOS PRJ-01 · TC-0 진동 측정용 IMU 로그 스케치 (#370)
// BNO085의 선형 가속도(m/s^2)와 각속도(rad/s)를 읽어 CSV 한 줄씩 낸다. 모터·서보·ESC는 쓰지 않는다.
// 측정 방법과 표는 docs/execution/tc0-vibration-limit.md (#253) 에 있다.
//
// 배선(3.3V만, 5V 금지):  Teensy 3V→VCC_3V3, G→GND, 19→SCL/SCK/RX, 18→SDA/MISO/TX  (imu_test_i2c와 같다)
//
// 출력 형식: '#'으로 시작하는 줄은 사람용 메시지, 'V,'로 시작하는 줄은 기록용 데이터
//   V,<millis>,<ax>,<ay>,<az>,<gx>,<gy>,<gz>
//   a* = 선형 가속도 m/s^2, g* = 각속도 rad/s. 가속도나 각속도 중 하나라도 새 값이 오면 한 줄을 낸다.
//   두 보고는 서로 다른 시각에 오므로 한 줄의 다른 쪽 값은 직전 값일 수 있다. 계산할 때는 값이
//   바뀐 줄만 쓰거나 같은 값이 이어지는 줄을 하나로 센다.
//
// 보고 주기: REPORT_PERIOD_MS(ms). 시작할 때 '# period_ms=<값>'을 낸다. BNO085가 허용하는 가장 짧은 주기는
//   이 스케치에서 확인하지 못했다(데이터시트 확인 필요). 시리얼 명령 'period <ms>'로 바꿔 가며 5초마다 찍히는
//   '# rows_per_s=<값>'이 따라오는지 보고 실제로 나오는 속도를 찾는다.
//
// 명령 (시리얼 모니터에서 한 줄 입력 후 Enter):
//   period <ms>   보고 주기를 바꾼다(1-1000). 바꾼 값을 '# period_ms='로 다시 낸다.
#include <Arduino.h>
#include <Wire.h>
#include <stdlib.h>
#include <string.h>
#include "BNO080.h"

static constexpr uint16_t REPORT_PERIOD_MS = 10;       // 시작 주기(보수값). 'period' 명령으로 바꾼다.
static constexpr uint32_t RATE_PERIOD_MS   = 5000;     // 초당 줄 수를 알리는 간격

BNO080 imu(255, 255, 255, 255);
uint8_t  foundAddr = 0;
uint16_t periodMs  = REPORT_PERIOD_MS;

float    lastA[3] = {0, 0, 0};
float    lastG[3] = {0, 0, 0};
bool     haveLast = false;
uint32_t rowCount = 0;
uint32_t rateStartMs = 0;

char   lineBuf[24];
size_t lineLen = 0;

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

void enableReports(uint16_t p) {
  imu.enableLinearAccelerometer(p);
  imu.enableGyro(p);
  periodMs = p;
  rowCount = 0;
  rateStartMs = millis();
  Serial.print("# period_ms=");
  Serial.println(p);
}

void handleLine(char* line) {
  if (strncmp(line, "period ", 7) == 0) {
    char* end = nullptr;
    long v = strtol(line + 7, &end, 10);
    if (end == line + 7 || *end != '\0' || v < 1 || v > 1000) {
      Serial.println("# REJECT: period <ms> 는 1-1000만 허용");
      return;
    }
    enableReports((uint16_t)v);
    return;
  }
  if (line[0] != '\0') {
    Serial.print("# REJECT: 모르는 명령 '");
    Serial.print(line);
    Serial.println("'");
  }
}

void pollSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      lineBuf[lineLen] = '\0';
      handleLine(lineBuf);
      lineLen = 0;
      continue;
    }
    if (lineLen < sizeof(lineBuf) - 1) lineBuf[lineLen++] = c;
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {}
  Wire.begin();
  Wire.setClock(400000);  // BNO085는 400 kHz I2C를 지원한다. 100 kHz에서는 짧은 주기를 따라가지 못할 수 있다.
  delay(200);
}

void loop() {
  pollSerial();

  if (!foundAddr) {
    scanBus();
    if (foundAddr && imu.begin(foundAddr)) {
      Serial.print("# BNO085 OK at 0x"); Serial.println(foundAddr, HEX);
      Serial.println("# V,millis,ax,ay,az,gx,gy,gz  (a: m/s^2, g: rad/s)");
      enableReports(periodMs);
    } else {
      foundAddr = 0;
      Serial.println("# BNO085 not ready, rescan in 2s");
      delay(2000);
    }
    return;
  }

  if (imu.dataAvailable()) {
    float a[3], g[3];
    uint8_t acc;
    imu.getLinAccel(a[0], a[1], a[2], acc);
    imu.getGyro(g[0], g[1], g[2], acc);
    bool changed = !haveLast;
    for (uint8_t i = 0; i < 3; i++) {
      if (a[i] != lastA[i] || g[i] != lastG[i]) changed = true;
    }
    if (changed) {
      Serial.print("V,");
      Serial.print(millis());
      for (uint8_t i = 0; i < 3; i++) { Serial.print(','); Serial.print(a[i], 4); }
      for (uint8_t i = 0; i < 3; i++) { Serial.print(','); Serial.print(g[i], 4); }
      Serial.println();
      for (uint8_t i = 0; i < 3; i++) { lastA[i] = a[i]; lastG[i] = g[i]; }
      haveLast = true;
      rowCount++;
    }
  }

  const uint32_t now = millis();
  if (now - rateStartMs >= RATE_PERIOD_MS) {
    Serial.print("# rows_per_s=");
    Serial.println(rowCount * 1000.0f / (now - rateStartMs), 1);
    rowCount = 0;
    rateStartMs = now;
  }
}
