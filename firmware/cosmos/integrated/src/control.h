#pragma once

#include "../../rc_bench/src/rc_logic.h"

namespace hopper {

// Dry-run timing assumptions, in ms. Both sensor reports are requested at 100 Hz.
constexpr uint32_t kPeriodMs = 10;
constexpr uint32_t kImuTimeoutMs = 50;
constexpr uint32_t kRcTimeoutMs = 100;
constexpr float kThrottleSlew = 0.25f;  // sim/sim_stage1/params.yaml, 1/s (#184)

struct Stamp {
  bool seen;
  uint32_t ms;
};

struct Attitude {
  Stamp stamp;
  float w, x, y, z;  // Unit quaternion, body to world
};

struct Rates {
  Stamp stamp;
  float x, y, z;  // Body rates, rad/s
};

struct Inputs {
  Attitude attitude;
  Rates rates;
  RcSample throttle, kill;
};

struct Observation {
  float roll, pitch, yaw;
  float wx, wy, wz;
  float previousThrottle;
};

struct Action {
  float vanes[4];  // Normalized, FWD/LEFT/AFT/RIGHT
  float throttle;  // [0,1]
};

using Policy = Action (*)(const Observation&, float pilotThrottle);
Action levelPd(const Observation& obs, float pilotThrottle);

enum class Command { None, Arm, Disarm };
enum class State { Disarmed, Active, Failsafe };
enum class Reason { Ok, Disarm, Kill, Rc, Attitude, Gyro, LoopGap, HighThrottle, Policy };

struct Result {
  State state;
  Reason reason;
  Action applied;
};

bool readAttitude(uint32_t now, const Attitude& q, Observation& obs);
bool readRates(uint32_t now, const Rates& rates, Observation& obs);

class Controller {
 public:
  explicit Controller(Policy policy = levelPd) : policy_(policy) {}
  Result step(uint32_t now, const Inputs& input, Command command);

 private:
  Result stop(State state, Reason reason);
  Policy policy_;
  Result result_{State::Disarmed, Reason::Ok, {}};
  uint32_t lastTick_ = 0;
};

}  // namespace hopper
