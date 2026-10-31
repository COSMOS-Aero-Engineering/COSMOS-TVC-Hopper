// COSMOS PRJ-01 · rc_bench 판정 로직. Arduino 의존이 없어서 PC에서도 컴파일된다.
//
// 규칙 (안전 쪽으로 기운다):
//   - 킬 채널(CH5)을 한 번도 못 받았거나, 마지막 유효 펄스가 RC_TIMEOUT_MS 넘게 오래됐거나,
//     펄스폭이 KILL_BELOW_US 미만이면 KILL이다. 부팅 직후는 KILL에서 시작한다.
//   - KILL이면 스로틀 출력은 항상 0이다. KILL이 아니어도 CH1을 못 받았으면 0이다.
//   - 이 스케치는 모터를 구동하지 않는다. "스로틀 출력"은 나중에 DShot 스케치가 받을 값을
//     시리얼에 보고하는 숫자일 뿐이다.
#pragma once
#include <stdint.h>

constexpr uint16_t RC_MIN_VALID_US = 800;    // 이보다 짧거나 RC_MAX_VALID_US보다 긴 펄스는 노이즈로 보고 버린다
constexpr uint16_t RC_MAX_VALID_US = 2200;
constexpr uint32_t RC_TIMEOUT_MS   = 3000;   // 이 시간 동안 유효 펄스가 없으면 신호 없음 (#248)
constexpr uint16_t KILL_BELOW_US   = 1500;   // CH5가 이 값 미만이면 KILL. 실제 조종기로 정할 값이다(확인 필요)

enum class KillReason : uint8_t { NONE, NO_SIGNAL, STALE, LOW_PULSE };

struct RcSample {
  bool     seen;         // 유효 펄스를 한 번이라도 받았나
  uint16_t widthUs;      // 마지막 유효 펄스폭
  uint32_t lastValidMs;  // 그 펄스를 받은 millis()
};

// millis()가 2^32에서 한 바퀴 돌아도 뺄셈이 맞도록 부호 없는 뺄셈을 쓴다.
inline bool rcFresh(const RcSample& s, uint32_t nowMs) {
  return s.seen && (uint32_t)(nowMs - s.lastValidMs) < RC_TIMEOUT_MS;
}

inline KillReason evalKill(const RcSample& kill, uint32_t nowMs) {
  if (!kill.seen) return KillReason::NO_SIGNAL;
  if (!rcFresh(kill, nowMs)) return KillReason::STALE;
  if (kill.widthUs < KILL_BELOW_US) return KillReason::LOW_PULSE;
  return KillReason::NONE;
}

// 스로틀 출력(µs). 0 = 출력 없음.
inline uint16_t throttleOutUs(KillReason reason, const RcSample& ch1, uint32_t nowMs) {
  if (reason != KillReason::NONE) return 0;
  if (!rcFresh(ch1, nowMs)) return 0;
  return ch1.widthUs;
}

inline const char* killReasonText(KillReason r) {
  switch (r) {
    case KillReason::NO_SIGNAL: return "CH5 신호를 아직 못 받음";
    case KillReason::STALE:     return "CH5 신호 끊김(3초 넘게 유효 펄스 없음)";
    case KillReason::LOW_PULSE: return "CH5가 기준 아래(킬 스위치 내림)";
    default:                    return "";
  }
}
