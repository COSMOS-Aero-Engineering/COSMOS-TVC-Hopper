// COSMOS PRJ-01 · 서보 단독 구동 스케치 (서보 보정 #243, 베인 응답 실측 #202 공용)
//
// 시리얼 명령으로 서보 하나에 펄스폭(µs)을 낸다. 지금 가진 서보는 SG90이고, MG90S에도 같이 쓴다.
// Servo 라이브러리는 Teensy 코어에 들어 있는 PJRC 판이다(lib_deps 없음).
//
// *** 첫 시험은 반드시 혼(horn)을 끼우지 않은 서보로. 혼이 없으면 기계 끝에 부딪혀 다칠 일이 없다 ***
// *** EDF·ESC는 연결하지 않는다. 이 스케치는 서보 신호만 낸다 ***
//
// 배선 (01-avionics-integration-final.md §2.2 핀맵):
//        서보 1 신호선 → Teensy 핀 2
//        서보 2 신호선 → Teensy 핀 3   (서보 3·4는 핀 4·5. 이 스케치는 1-2만 쓴다)
//        서보 GND ↔ Teensy GND (공통)
//        서보 5V는 Teensy USB 5V(VUSB) 또는 UBEC 5V에서 준다. Teensy 3.3V 핀은 서보 전원으로 쓰지 않는다.
//        서보를 둘 이상 동시에 돌리거나 베인 부하를 달 때는 UBEC를 쓴다. 서보가 움직일 때 Teensy가
//        재부팅하면 UBEC로 바꾸고 이슈에 적는다. USB 전류만으로 충분한지는 확인하지 못했다.
//        배선은 USB를 뽑은 상태에서 바꾼다.
//
// 명령 (시리얼 모니터에서 한 줄 입력 후 Enter):
//   <µs>           지금 선택된 서보(처음엔 1번)에 펄스폭을 낸다.   예: 1500
//   <번호> <µs>    서보 번호(1-2)를 고르고 펄스폭을 낸다.         예: 2 1600
//   빈 줄/off/stop 모든 서보의 펄스 출력을 끈다(비상정지: 그냥 Enter만 쳐도 멈춘다)
//   ?              지금 선택된 서보의 상태를 출력한다
//
// 안전 장치:
//   - 켠 직후에는 어떤 핀에도 펄스를 내지 않는다. 그 서보에 첫 명령이 들어올 때 비로소 출력을 시작한다.
//   - 펄스폭은 SERVO_MIN_US ~ SERVO_MAX_US 안으로 제한한다. 범위 밖 입력은 가장 가까운 한계값으로
//     바꾸고 '# CLAMP'를 출력한다. 시작값은 1000-2000 µs이고, 기계 끝을 확인한 뒤 조정한다.
//     Servo 라이브러리 기본 범위(544-2400 µs)는 서보를 기계 끝까지 보낼 수 있어서 쓰지 않는다.
//   - 숫자가 아닌 입력, 서보 번호 밖(1-2 아님), 너무 긴 줄은 거부한다. 출력은 바뀌지 않는다.
//   - 끄면 핀을 LOW로 내린다. Teensy 4.x Servo::detach()는 펄스를 멈추기만 하고 핀 레벨은 건드리지 않아서
//     펄스 도중에 끄면 핀이 HIGH로 남을 수 있다.
//
// 출력 형식: '#'으로 시작하는 줄은 사람용 메시지, 'D,'로 시작하는 줄은 기록용 데이터
//   D,<millis>,<servo>,<us>      us=0은 펄스를 내지 않는다는 뜻

#include <Arduino.h>
#include <Servo.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>

constexpr uint8_t  SERVO_COUNT         = 2;
constexpr uint8_t  SERVO_PIN[SERVO_COUNT] = {2, 3};  // 서보 1 = 핀 2, 서보 2 = 핀 3 (01 문서 §2.2)
constexpr int      SERVO_MIN_US        = 1000;       // 하한 (기계 끝 확인 후 조정)
constexpr int      SERVO_MAX_US        = 2000;       // 상한 (기계 끝 확인 후 조정)

Servo servos[SERVO_COUNT];
int   servoUs[SERVO_COUNT]  = {0, 0};   // 마지막으로 낸 펄스폭. 0 = 출력 없음
uint8_t currentServo = 1;                // 사람이 쓰는 번호(1-2)

char   lineBuf[32];
size_t lineLen = 0;
bool   lineOverflow = false;

void printStatus() {
  Serial.print("D,");
  Serial.print(millis());                  Serial.print(',');
  Serial.print(currentServo);              Serial.print(',');
  Serial.println(servoUs[currentServo - 1]);
}

void releaseAll(const char* reason) {
  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    if (servos[i].attached()) {
      servos[i].detach();
      digitalWrite(SERVO_PIN[i], LOW);
    }
    servoUs[i] = 0;
  }
  Serial.print("# OFF: ");
  Serial.println(reason);
  printStatus();
}

// 줄 전체가 정수일 때만 true. 앞뒤 공백은 호출한 쪽에서 이미 걷어냈다.
bool parseInt(const char* s, long& out) {
  if (*s == '\0') return false;
  char* end = nullptr;
  errno = 0;
  long v = strtol(s, &end, 10);
  if (end == s || *end != '\0') return false;
  if (errno == ERANGE) return false;
  out = v;
  return true;
}

void setPulse(uint8_t servoNo, long requestedUs) {
  long us = requestedUs;
  if (us < SERVO_MIN_US) us = SERVO_MIN_US;
  if (us > SERVO_MAX_US) us = SERVO_MAX_US;

  if (us != requestedUs) {
    Serial.print("# CLAMP: ");
    Serial.print(requestedUs);
    Serial.print(" -> ");
    Serial.print(us);
    Serial.print(" us (허용 ");
    Serial.print(SERVO_MIN_US);
    Serial.print("-");
    Serial.print(SERVO_MAX_US);
    Serial.println(")");
  }

  Servo& s = servos[servoNo - 1];
  if (!s.attached()) {
    // attach 범위를 같이 줘서 라이브러리도 한 번 더 제한한다.
    // Teensy 4.x는 attach 직후 1500 µs를 기본값으로 잡으므로 바로 아래 write로 덮어쓴다.
    s.attach(SERVO_PIN[servoNo - 1], SERVO_MIN_US, SERVO_MAX_US);
  }
  s.writeMicroseconds((int)us);
  servoUs[servoNo - 1] = (int)us;
  currentServo = servoNo;

  Serial.print("# servo ");
  Serial.print(servoNo);
  Serial.print(" -> ");
  Serial.print(us);
  Serial.println(" us");
  printStatus();
}

void handleLine(char* line) {
  while (*line == ' ') line++;
  size_t n = strlen(line);
  while (n > 0 && line[n - 1] == ' ') line[--n] = '\0';

  if (n == 0 || strcmp(line, "off") == 0 || strcmp(line, "stop") == 0) {
    releaseAll("user");
    return;
  }
  if (strcmp(line, "?") == 0) {
    printStatus();
    return;
  }

  // 토큰은 하나(<µs>) 또는 둘(<번호> <µs>)이다.
  char* second = strchr(line, ' ');
  if (second != nullptr) {
    *second++ = '\0';
    while (*second == ' ') second++;
  }

  long first;
  if (!parseInt(line, first)) {
    Serial.print("# REJECT: 모르는 명령 '");
    Serial.print(line);
    Serial.println("'");
    return;
  }

  if (second == nullptr) {
    setPulse(currentServo, first);
    return;
  }

  long us;
  if (!parseInt(second, us)) {
    Serial.print("# REJECT: 펄스폭이 숫자가 아님 '");
    Serial.print(second);
    Serial.println("'");
    return;
  }
  if (first < 1 || first > SERVO_COUNT) {
    Serial.print("# REJECT: 서보 번호는 1-");
    Serial.print(SERVO_COUNT);
    Serial.print("만 허용 (받은 값 ");
    Serial.print(first);
    Serial.println(")");
    return;
  }
  setPulse((uint8_t)first, us);
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

  Serial.println("# COSMOS servo bench");
  Serial.println("# 혼을 끼우지 않은 서보로 시작. EDF·ESC 연결 금지. 명령: <us> / <번호> <us> / 빈 줄=끔 / ?");
  Serial.print("# 서보 1 = 핀 ");
  Serial.print(SERVO_PIN[0]);
  Serial.print(", 서보 2 = 핀 ");
  Serial.println(SERVO_PIN[1]);
  Serial.print("# 펄스폭 범위 ");
  Serial.print(SERVO_MIN_US);
  Serial.print("-");
  Serial.print(SERVO_MAX_US);
  Serial.println(" us. 첫 명령 전에는 펄스를 내지 않는다");
  Serial.println("# D,millis,servo,us  (us=0: 출력 없음)");
}

void loop() {
  pollSerial();
}
