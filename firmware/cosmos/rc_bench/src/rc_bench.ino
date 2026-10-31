// COSMOS PRJ-01 · RC 수신기 벤치 스케치 (브링업 P3, #248)
//
// RC 수신기(FS-iA6B)의 PWM 5채널 펄스폭을 인터럽트로 읽어 시리얼에 한 줄로 출력한다.
// 킬 채널(CH5)이 내려가면 KILL을 출력하고 스로틀 출력을 0으로 보고한다.
// 판정 로직은 rc_logic.h에 있다.
//
// *** 이 스케치는 모터·ESC·서보를 구동하지 않는다. EDF·ESC는 연결하지 않는다. ***
//
// 배선 (01-avionics-integration-final.md §2.2, §2.3):
//   수신기 CHn 신호(5 V) → 레벨시프터 HV → LV(3.3 V) → Teensy 핀. 5 V 신호를 Teensy에 직접 연결하지 않는다.
//   CH1 스로틀=18, CH2 롤=19, CH3 피치=23, CH4 요=1, CH5 킬=9
//   레벨시프터 LV = Teensy 3V3, HV = 수신기 5 V, GND 공통.
//   핀 18·19는 IMU 연결 방식(#245)에 따라 바뀔 수 있다. 바뀌면 아래 RC_PINS만 고친다.
//   (imu_test_i2c는 18·19를 I2C에 쓴다. 그 스케치와 이 배선을 같이 두지 않는다.)
//
// 출력 형식: '#'으로 시작하는 줄은 사람용 메시지, 'D,'로 시작하는 줄은 기록용 데이터
//   D,<millis>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<OK|KILL>,<throttle_out_us>
//   채널 값은 µs. 신호가 RC_TIMEOUT_MS 넘게 없는 채널은 0으로 찍는다.
//   throttle_out_us는 KILL이면 0, 아니면 CH1 값.
//
// 안전 장치:
//   - 부팅 직후와 CH5 신호가 없을 때는 KILL이다. CH5 선이 빠지거나 수신기 전원이 꺼져도 KILL이다.
//   - CH5만 킬 판정에 쓴다. CH2~CH4 선을 안 꽂은 벤치(CH1·CH5만 배선)에서도 동작한다. 안 꽂은 채널은 0으로 보인다.
//   - 유효 범위 밖의 펄스(RC_MIN_VALID_US~RC_MAX_VALID_US)는 버린다.

#include "rc_logic.h"

constexpr uint8_t  RC_COUNT        = 5;
constexpr uint8_t  RC_PINS[RC_COUNT] = {18, 19, 23, 1, 9};   // CH1~CH5
constexpr uint8_t  KILL_CH         = 4;                       // CH5의 인덱스
constexpr uint8_t  THROTTLE_CH     = 0;                       // CH1의 인덱스
constexpr uint32_t PRINT_PERIOD_MS = 100;

// ISR이 쓰고 loop가 읽는다. loop는 noInterrupts() 안에서 한 번에 복사한다.
volatile uint32_t riseUs[RC_COUNT];
volatile bool     risen[RC_COUNT];
volatile bool     seenV[RC_COUNT];
volatile uint16_t widthV[RC_COUNT];
volatile uint32_t lastValidMsV[RC_COUNT];

void rcEdge(uint8_t i) {
  uint32_t now = micros();
  if (digitalReadFast(RC_PINS[i])) {
    riseUs[i] = now;
    risen[i]  = true;
  } else if (risen[i]) {
    risen[i] = false;
    uint32_t w = now - riseUs[i];
    if (w >= RC_MIN_VALID_US && w <= RC_MAX_VALID_US) {
      widthV[i]       = (uint16_t)w;
      lastValidMsV[i] = millis();
      seenV[i]        = true;
    }
  }
}

void isr0() { rcEdge(0); }
void isr1() { rcEdge(1); }
void isr2() { rcEdge(2); }
void isr3() { rcEdge(3); }
void isr4() { rcEdge(4); }

KillReason lastReason = KillReason::NO_SIGNAL;
uint32_t   lastPrintMs = 0;

void setup() {
  Serial.begin(115200);
  void (*const isrs[RC_COUNT])() = {isr0, isr1, isr2, isr3, isr4};
  for (uint8_t i = 0; i < RC_COUNT; i++) {
    // 플로팅 입력이 노이즈 펄스를 만들지 않도록 내부 풀다운을 쓴다. 신호가 없으면 KILL로 끝난다.
    pinMode(RC_PINS[i], INPUT_PULLDOWN);
    attachInterrupt(digitalPinToInterrupt(RC_PINS[i]), isrs[i], CHANGE);
  }
  Serial.println("# rc_bench: 모터 출력 없음. 부팅 상태는 KILL");
  Serial.println("# D,<millis>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<OK|KILL>,<throttle_out_us>");
}

void loop() {
  uint32_t nowMs = millis();
  if ((uint32_t)(nowMs - lastPrintMs) < PRINT_PERIOD_MS) return;
  lastPrintMs = nowMs;

  RcSample s[RC_COUNT];
  noInterrupts();
  nowMs = millis();   // 복사 시각과 같은 시점으로 판정한다
  for (uint8_t i = 0; i < RC_COUNT; i++) {
    s[i].seen        = seenV[i];
    s[i].widthUs     = widthV[i];
    s[i].lastValidMs = lastValidMsV[i];
  }
  interrupts();

  KillReason reason = evalKill(s[KILL_CH], nowMs);
  uint16_t   thrOut = throttleOutUs(reason, s[THROTTLE_CH], nowMs);

  if (reason != lastReason) {
    if (reason == KillReason::NONE) {
      Serial.println("# OK: 킬 해제");
    } else {
      Serial.print("# KILL: ");
      Serial.println(killReasonText(reason));
    }
    lastReason = reason;
  }

  Serial.print("D,");
  Serial.print(nowMs);
  for (uint8_t i = 0; i < RC_COUNT; i++) {
    Serial.print(',');
    Serial.print(rcFresh(s[i], nowMs) ? s[i].widthUs : 0);
  }
  Serial.print(',');
  Serial.print(reason == KillReason::NONE ? "OK" : "KILL");
  Serial.print(',');
  Serial.println(thrOut);
}
