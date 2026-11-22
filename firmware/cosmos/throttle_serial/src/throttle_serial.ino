// COSMOS PRJ-01 · DShot 벤치 테스트 펌웨어 (실험 C, 실험 A·TC-0 공용)
//
// 시리얼 명령으로 ESC 하나에 DShot600 스로틀을 낸다. dshot.h/.cpp는
// firmware/reference/SingleRotorUAV/src/ 복사본(Teensy 4.x eFlexPWM+DMA 드라이버).
//
// *** 첫 시험은 반드시 EDF 팬(로터)을 분리하거나, 추력 스탠드에 볼트로 고정한 상태에서만 ***
//
// 배선:  ESC 신호선 → Teensy 핀 8 (dshot.cpp에 하드코딩)
//        ESC 신호 GND ↔ Teensy G (없으면 DShot 신호가 안 읽힌다)
//        ESC 전원은 배터리 → 킬스위치 → ESC 직결. 빵판·Teensy로 보내지 않는다.
//        ESC의 BEC 5V선은 Teensy에 연결하지 않는다.
//
// 명령 (시리얼 모니터에서 한 줄 입력 후 Enter):
//   arm        출력 허가. 목표 스로틀이 0일 때만 받는다.
//   0~N        목표 스로틀 %(전체 범위 기준). ARMED일 때만, 상한 N 이하만 받는다.
//   limit P    상한을 P %로 바꾼다(실험 A용, #237). ARMED일 때만 받는다.
//              올리는 폭은 한 번에 LIMIT_STEP_PCT %p 이하, 최대 HARD_LIMIT_PCT %.
//              낮추는 것은 언제든 받고, 목표가 새 상한보다 높으면 목표도 내린다.
//   빈 줄/stop  즉시 0 + DISARM (비상정지: 그냥 Enter만 쳐도 멈춘다)
//   ?          현재 상태 출력
//
// 안전 장치:
//   - 기본 상한: DShot 600 (01-avionics-integration-final.md §2.5-6, 추력곡선 확인 전 TC-0 단계 값)
//     limit 명령으로 올린 상한은 stop, 워치독, 재 arm 때 이 기본값으로 돌아간다.
//   - 상승 램프: 초당 RAMP_UP_PCT_PER_S %. 내릴 때는 즉시.
//   - 워치독: ARMED이고 출력 중일 때 WATCHDOG_MS 동안 유효한 명령이 없으면 즉시 정지 + DISARM.
//     같은 숫자를 다시 보내면 연장된다.
//   - DShot 프레임은 명령 처리와 상관없이 1 kHz로 끊김 없이 나간다(시리얼 파싱이 루프를 막지 않음).
//
// 출력 형식: '#'으로 시작하는 줄은 사람용 메시지, 'D,'로 시작하는 줄은 기록용 데이터
//   D,<millis>,<state>,<target_pct>,<output_pct>,<dshot>

#include "dshot.h"

constexpr uint8_t  ESC_PORT           = DSHOT_PORT_1;
constexpr uint16_t DSHOT_MIN_THROTTLE = 48;     // 0~47은 DShot 명령어 영역
constexpr uint16_t DSHOT_FULL         = 2047;
constexpr uint16_t DSHOT_CAP          = 600;    // 기본 상한. limit 명령 없이는 이 값이다.
constexpr float    LIMIT_STEP_PCT     = 10.0f;  // limit으로 한 번에 올릴 수 있는 폭(%p). 부장 승인 값(#237)
constexpr float    HARD_LIMIT_PCT     = 100.0f; // limit으로 올릴 수 있는 최대 %. 부장 승인 값(#237)
constexpr uint32_t OUTPUT_PERIOD_US   = 1000;
constexpr uint32_t WATCHDOG_MS        = 3000;
constexpr float    RAMP_UP_PCT_PER_S  = 20.0f;
constexpr uint32_t STATUS_PERIOD_MS   = 200;

DShot motors(1);

enum class State : uint8_t { DISARMED, ARMED };

State    state           = State::DISARMED;
uint16_t capDshot        = DSHOT_CAP;  // 현재 상한(DShot 값). stopAndDisarm()이 기본값으로 되돌린다.
float    targetPct       = 0.0f;
float    outputPct       = 0.0f;
uint32_t lastCommandMs   = 0;
uint32_t lastOutputUs    = 0;
uint32_t lastStatusMs    = 0;

char   lineBuf[32];
size_t lineLen = 0;
bool   lineOverflow = false;

uint16_t pctToDshot(float pct) {
  if (pct <= 0.0f) return 0;
  float v = DSHOT_MIN_THROTTLE + (DSHOT_FULL - DSHOT_MIN_THROTTLE) * (pct / 100.0f);
  if (v > capDshot) v = capDshot;
  return (uint16_t)(v + 0.5f);
}

float dshotToPct(uint16_t d) {
  return 100.0f * (d - DSHOT_MIN_THROTTLE) / float(DSHOT_FULL - DSHOT_MIN_THROTTLE);
}

float capPct() {
  return dshotToPct(capDshot);
}

uint16_t pctToCapDshot(float pct) {
  return (uint16_t)(DSHOT_MIN_THROTTLE + (DSHOT_FULL - DSHOT_MIN_THROTTLE) * (pct / 100.0f) + 0.5f);
}

const char* stateName() { return state == State::ARMED ? "ARMED" : "DISARMED"; }

void stopAndDisarm(const char* reason) {
  targetPct = 0.0f;
  outputPct = 0.0f;
  state = State::DISARMED;
  capDshot = DSHOT_CAP;  // limit으로 올린 상한을 기본값으로 되돌린다(#237).
  motors.write(ESC_PORT, 0, DSHOT_TLM_NONE);
  Serial.print("# STOP: ");
  Serial.println(reason);
}

void printStatus() {
  Serial.print("D,");
  Serial.print(millis());       Serial.print(',');
  Serial.print(stateName());    Serial.print(',');
  Serial.print(targetPct, 1);   Serial.print(',');
  Serial.print(outputPct, 1);   Serial.print(',');
  Serial.println(pctToDshot(outputPct));
}

bool parsePct(const char* s, float& out) {
  char* end = nullptr;
  float v = strtof(s, &end);
  if (end == s) return false;
  while (*end == ' ') end++;
  if (*end != '\0') return false;
  out = v;
  return true;
}

void handleLine(char* line) {
  while (*line == ' ') line++;
  size_t n = strlen(line);
  while (n > 0 && line[n - 1] == ' ') line[--n] = '\0';

  if (n == 0 || strcmp(line, "stop") == 0) {
    stopAndDisarm("user");
    return;
  }
  if (strcmp(line, "?") == 0) {
    Serial.print("# 상한 ");
    Serial.print(capPct(), 1);
    Serial.println("%");
    printStatus();
    return;
  }
  if (strncmp(line, "limit", 5) == 0 && (line[5] == ' ' || line[5] == '\0')) {
    if (state != State::ARMED) {
      Serial.println("# REJECT: 먼저 arm");
      return;
    }
    float want;
    if (line[5] == '\0' || !parsePct(line + 6, want)) {
      Serial.println("# REJECT: 형식은 limit <퍼센트>");
      return;
    }
    const float now = capPct();
    if (want <= 0.0f || want > HARD_LIMIT_PCT) {
      Serial.print("# REJECT: 상한은 0 초과 ");
      Serial.print(HARD_LIMIT_PCT, 1);
      Serial.println("% 이하만");
      return;
    }
    if (want > now + LIMIT_STEP_PCT) {
      Serial.print("# REJECT: 한 번에 ");
      Serial.print(LIMIT_STEP_PCT, 1);
      Serial.print("%p까지만 올린다. 지금 상한 ");
      Serial.print(now, 1);
      Serial.println("%");
      return;
    }
    capDshot = pctToCapDshot(want);
    if (targetPct > capPct()) targetPct = capPct();  // 낮출 때 목표도 같이 내린다.
    Serial.print("# LIMIT ");
    Serial.print(capPct(), 1);
    Serial.println("% (stop, 워치독, 재 arm 때 기본값으로 복귀)");
    return;
  }
  if (strcmp(line, "arm") == 0) {
    if (targetPct > 0.0f || outputPct > 0.0f) {
      Serial.println("# REJECT: arm은 스로틀 0일 때만");
      return;
    }
    capDshot = DSHOT_CAP;  // 재 arm 때는 항상 기본 상한에서 시작한다.
    state = State::ARMED;
    lastCommandMs = millis();
    Serial.print("# ARMED. 상한 ");
    Serial.print(capPct(), 1);
    Serial.println("%. 빈 줄 Enter = 비상정지");
    return;
  }

  float pct;
  if (!parsePct(line, pct)) {
    Serial.print("# REJECT: 모르는 명령 '");
    Serial.print(line);
    Serial.println("'");
    return;
  }
  if (state != State::ARMED) {
    Serial.println("# REJECT: 먼저 arm");
    return;
  }
  if (pct < 0.0f || pct > capPct()) {
    Serial.print("# REJECT: 0~");
    Serial.print(capPct(), 1);
    Serial.println("% 범위만 허용");
    return;
  }
  targetPct = pct;
  lastCommandMs = millis();
  Serial.print("# TARGET ");
  Serial.print(targetPct, 1);
  Serial.print("% (DShot ");
  Serial.print(pctToDshot(targetPct));
  Serial.println(")");
}

void pollSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (lineOverflow) {
        Serial.println("# REJECT: 줄이 너무 김");
      } else {
        lineBuf[lineLen] = '\0';
        handleLine(lineBuf);
      }
      lineLen = 0;
      lineOverflow = false;
      continue;
    }
    if (lineLen < sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = c;
    } else {
      lineOverflow = true;
    }
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {}

  motors.setup();
  motors.setConfig(ESC_PORT, DSHOT_CMD_3D_MODE_OFF);
  motors.armMotors();  // ESC 쪽 시동 절차(정지 프레임 반복). 출력 허가(arm 명령)와는 별개.

  Serial.println("# COSMOS DShot bench test");
  Serial.println("# 팬 분리 또는 스탠드 고정 확인. 명령: arm / 0~cap / limit <퍼센트> / 빈 줄=정지 / ?");
  Serial.print("# 상한 DShot ");
  Serial.print(DSHOT_CAP);
  Serial.print(" = ");
  Serial.print(capPct(), 1);
  Serial.println("%");
  Serial.println("# D,millis,state,target_pct,output_pct,dshot");

  lastOutputUs = micros();
}

void loop() {
  pollSerial();

  const uint32_t nowMs = millis();
  if (state == State::ARMED && targetPct > 0.0f && nowMs - lastCommandMs > WATCHDOG_MS) {
    stopAndDisarm("watchdog");
  }

  const uint32_t nowUs = micros();
  if (nowUs - lastOutputUs >= OUTPUT_PERIOD_US) {
    const float dt = (nowUs - lastOutputUs) * 1e-6f;
    lastOutputUs = nowUs;

    if (state != State::ARMED) {
      outputPct = 0.0f;
    } else if (targetPct < outputPct) {
      outputPct = targetPct;
    } else {
      outputPct = min(targetPct, outputPct + RAMP_UP_PCT_PER_S * dt);
    }
    motors.write(ESC_PORT, pctToDshot(outputPct), DSHOT_TLM_NONE);
  }

  if ((state == State::ARMED || outputPct > 0.0f) && nowMs - lastStatusMs >= STATUS_PERIOD_MS) {
    lastStatusMs = nowMs;
    printStatus();
  }
}
