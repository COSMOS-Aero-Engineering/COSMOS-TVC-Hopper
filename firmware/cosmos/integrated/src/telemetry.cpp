#include "telemetry.h"
#include <cstdio>

namespace hopper {
namespace {
const char* stateName(State state) {
  switch (state) {
    case State::Disarmed: return "DISARMED";
    case State::Active: return "ACTIVE";
    case State::Failsafe: return "FAILSAFE";
  }
  return "UNKNOWN";
}

const char* reasonName(Reason reason) {
  switch (reason) {
    case Reason::Ok: return "OK";
    case Reason::Disarm: return "DISARM";
    case Reason::Kill: return "KILL";
    case Reason::Rc: return "RC_INVALID";
    case Reason::Attitude: return "ATTITUDE_INVALID";
    case Reason::Gyro: return "GYRO_INVALID";
    case Reason::LoopGap: return "LOOP_GAP";
    case Reason::HighThrottle: return "ARM_THROTTLE_HIGH";
    case Reason::Policy: return "POLICY_INVALID";
  }
  return "UNKNOWN";
}
}  // namespace

size_t csvRow(char (&row)[kCsvCapacity], uint32_t now, Source source,
              const Inputs& in, const Result& result) {
  const Attitude& q = in.attitude;
  const Rates& g = in.rates;
  Observation obs{};
  char pose[128] = ",,,,,,";
  if (readAttitude(now, q, obs)) {
    snprintf(pose, sizeof(pose), "%.7g,%.7g,%.7g,%.7g,%.7g,%.7g,%.7g",
             obs.roll, obs.pitch, obs.yaw, q.w, q.x, q.y, q.z);
  }
  char rates[60] = ",,";
  if (readRates(now, g, obs)) {
    snprintf(rates, sizeof(rates), "%.7g,%.7g,%.7g", g.x, g.y, g.z);
  }
  const Action& a = result.applied;
  int len = snprintf(row, sizeof(row),
                     "%lu,%s,PID,%s,%s,%.7g,%.7g,%.7g,%.7g,%.7g,,,,%s,%s,1",
                     static_cast<unsigned long>(now), source == Source::Sil ? "SIM" : "DRY_RUN",
                     pose, rates, a.vanes[0], a.vanes[1], a.vanes[2], a.vanes[3],
                     a.throttle, stateName(result.state), reasonName(result.reason));
  return len > 0 && static_cast<size_t>(len) < sizeof(row) ? static_cast<size_t>(len) : 0;
}
}  // namespace hopper
