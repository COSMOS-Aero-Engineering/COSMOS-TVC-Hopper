#include "control.h"
#include <cmath>

namespace hopper {
namespace {
float clip(float x, float low, float high) {
  return x < low ? low : (x > high ? high : x);
}

bool fresh(Stamp stamp, uint32_t now, uint32_t limit) {
  return stamp.seen && now - stamp.ms < limit;
}

bool validRc(const RcSample& s, uint32_t now) {
  return rcFresh(s, now) && now - s.lastValidMs < kRcTimeoutMs &&
         s.widthUs >= RC_MIN_VALID_US && s.widthUs <= RC_MAX_VALID_US;
}

Reason checkInputs(uint32_t now, const Inputs& in, Observation& obs) {
  if (!validRc(in.kill, now)) return Reason::Rc;
  if (evalKill(in.kill, now) != KillReason::NONE) return Reason::Kill;
  if (!validRc(in.throttle, now)) return Reason::Rc;
  if (!readAttitude(now, in.attitude, obs)) return Reason::Attitude;
  if (!readRates(now, in.rates, obs)) return Reason::Gyro;
  return Reason::Ok;
}
}  // namespace

bool readRates(uint32_t now, const Rates& r, Observation& obs) {
  if (!fresh(r.stamp, now, kImuTimeoutMs) ||
      !std::isfinite(r.x) || !std::isfinite(r.y) || !std::isfinite(r.z)) return false;
  obs.wx = r.x;
  obs.wy = r.y;
  obs.wz = r.z;
  return true;
}

bool readAttitude(uint32_t now, const Attitude& q, Observation& obs) {
  if (!fresh(q.stamp, now, kImuTimeoutMs)) return false;
  // Reject missing, corrupt or unnormalized rotations before using them for PD.
  const float norm2 = q.w*q.w + q.x*q.x + q.y*q.y + q.z*q.z;
  if (!std::isfinite(norm2) || std::fabs(norm2 - 1.0f) > 0.02f) return false;
  obs.roll = std::atan2(2 * (q.w*q.x + q.y*q.z), norm2 - 2 * (q.x*q.x + q.y*q.y));
  obs.pitch = std::asin(clip(2 * (q.w*q.y - q.z*q.x) / norm2, -1, 1));
  obs.yaw = std::atan2(2 * (q.w*q.z + q.x*q.y), norm2 - 2 * (q.y*q.y + q.z*q.z));
  return true;
}

Action levelPd(const Observation& obs, float pilotThrottle) {
  // sim/sim_stage1/pd_gate.py: tau_x=(F1+F3)*l, tau_y=-(F2+F4)*l.
  const float roll = clip(-8 * obs.roll - 2 * obs.wx, -1, 1);
  const float pitch = clip(8 * obs.pitch + 2 * obs.wy, -1, 1);
  return {{roll, pitch, roll, pitch}, pilotThrottle};
}

Result Controller::stop(State state, Reason reason) {
  result_ = {state, reason, {}};  // Neutral vanes and zero throttle on this tick.
  return result_;
}

Result Controller::step(uint32_t now, const Inputs& in, Command command) {
  const uint32_t elapsed = now - lastTick_;
  lastTick_ = now;
  if (command == Command::Disarm) return stop(State::Disarmed, Reason::Disarm);
  if (result_.state == State::Failsafe) return result_;  // Explicit disarm clears the latch.

  Observation obs{};
  Reason fault = checkInputs(now, in, obs);
  if (fault != Reason::Ok)
    return stop(result_.state == State::Active ? State::Failsafe : State::Disarmed, fault);

  if (result_.state == State::Disarmed) {
    if (command != Command::Arm) return stop(State::Disarmed, Reason::Ok);
    if (in.throttle.widthUs > 1050) return stop(State::Disarmed, Reason::HighThrottle);
    return stop(State::Active, Reason::Ok);  // Start this run at zero.
  }
  if (elapsed >= kImuTimeoutMs) return stop(State::Failsafe, Reason::LoopGap);

  const float pilotThrottle = clip((static_cast<float>(in.throttle.widthUs) - 1000) / 1000, 0, 1);
  obs.previousThrottle = result_.applied.throttle;
  Action action = policy_(obs, pilotThrottle);
  if (!std::isfinite(action.throttle)) return stop(State::Failsafe, Reason::Policy);
  for (float& vane : action.vanes) {
    if (!std::isfinite(vane)) return stop(State::Failsafe, Reason::Policy);
    vane = clip(vane, -1, 1);
  }
  const float target = clip(action.throttle, 0, pilotThrottle);
  const float delta = kThrottleSlew * (elapsed / 1000.0f);
  action.throttle = clip(target, obs.previousThrottle - delta, obs.previousThrottle + delta);
  result_ = {State::Active, Reason::Ok, action};
  return result_;
}

}  // namespace hopper
