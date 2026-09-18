// COSMOS PRJ-01 · DShot 스로틀 시리얼 테스트 스케치
// 시리얼 모니터에 0~100 숫자를 입력하면 그 %만큼 스로틀을 낸다.
//
// 이 폴더의 dshot.h / dshot.cpp는 firmware/reference/SingleRotorUAV/src/에서
// 그대로 복사해온 것이다 — Teensy 4.x 전용 DMA 기반 드라이버라 새로 만들 필요가 없다.
//
// *** 반드시 프로펠러/EDF 팬을 분리한 상태에서만 테스트할 것 ***
//
// 배선: ESC 신호선 → Teensy 핀 8 (DSHOT_PORT_1 이 dshot.cpp에 핀 8로 하드코딩되어 있음)
//       ESC/모터 접지 ↔ Teensy 접지 공통 연결 필수
//       ESC의 BEC 5V 출력은 Teensy에 연결하지 않는다 (배터리로 직접 전원 공급)

#include "dshot.h"

DShot motors(1); // 이 스케치에서는 출력 1개만 사용 (DSHOT_PORT_1)

const unsigned long FAILSAFE_MS = 2000; // 이 시간 안에 새 입력이 없으면 자동으로 0%
unsigned long lastCommandTime = 0;
int currentThrottlePct = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {}

  motors.setup();
  motors.setConfig(DSHOT_PORT_1, DSHOT_CMD_3D_MODE_OFF);
  motors.armMotors(); // 약 50ms 소요 — ESC에 정지 신호를 반복 전송해서 시동을 건다

  Serial.println("=== DShot 준비 완료 ===");
  Serial.println("*** 프로펠러/EDF 팬이 분리되어 있는지 다시 한 번 확인! ***");
  Serial.println("시리얼 모니터에 0~100 숫자를 입력하면 그 %로 스로틀이 걸립니다.");
  Serial.println("2초 동안 새 입력이 없으면 안전을 위해 자동으로 0%로 내려갑니다.");

  lastCommandTime = millis();
}

void loop() {
  if (Serial.available()) {
    int pct = Serial.parseInt();
    if (pct >= 0 && pct <= 100) {
      currentThrottlePct = pct;
      lastCommandTime = millis();
      Serial.print("Throttle -> ");
      Serial.print(pct);
      Serial.println("%");
    }
  }

  // failsafe: 일정 시간 새 명령이 없으면 자동으로 0%
  if (millis() - lastCommandTime > FAILSAFE_MS) {
    currentThrottlePct = 0;
  }

  // DShot 값 인코딩: 0=정지, 48~2047=실제 스로틀 (0~47은 명령어로 예약됨)
  // control.cpp의 실제 사용 예시(motors.write(index, 47 + throttle, 1))를 참고해 계산
  uint16_t dshotValue = (currentThrottlePct == 0) ? 0
                        : map(currentThrottlePct, 1, 100, 48, 2047);

  motors.write(DSHOT_PORT_1, dshotValue, DSHOT_TLM_NONE);

  delay(2); // DShot 갱신 주기 (너무 빠르게 반복 호출하지 않도록)
}
