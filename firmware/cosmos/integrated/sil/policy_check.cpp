// Exercise the replacement policy boundary without loading a learned model.
#include "../src/control.h"
#include <cmath>
#include <limits>

using namespace hopper;
namespace {
float desiredThrottle = 2;
float vane = 1.5f;
float observedThrottle = -1;
Action policy(const Observation& obs, float) {
  observedThrottle = obs.previousThrottle;
  return {{vane, -2, 0, 0}, desiredThrottle};
}
Inputs frame(uint32_t now, uint16_t throttle) {
  return {{{true, now}, 1, 0, 0, 0}, {{true, now}, 0, 0, 0},
          {true, throttle, now}, {true, 1800, now}};
}
}  // namespace

int main() {
  Controller controller(policy);
  controller.step(0, frame(0, 1000), Command::Arm);
  for (uint32_t t = 10; t <= 200; t += 10) {
    auto out = controller.step(t, frame(t, 1020), Command::None);
    if (out.state != State::Active || out.applied.vanes[0] != 1 || out.applied.vanes[1] != -1)
      return 1;
  }
  if (std::fabs(observedThrottle - 0.02f) > 1e-6f) return 1;
  desiredThrottle = -1;
  auto out = controller.step(210, frame(210, 1020), Command::None);
  if (std::fabs(out.applied.throttle - 0.0175f) > 1e-6f) return 1;
  vane = std::numeric_limits<float>::quiet_NaN();
  out = controller.step(220, frame(220, 1020), Command::None);
  if (out.reason != Reason::Policy || out.state != State::Failsafe || out.applied.throttle != 0)
    return 1;

  controller.step(230, frame(230, 1000), Command::Disarm);
  controller.step(240, frame(240, 1000), Command::Arm);
  Inputs bad = frame(250, 2000);
  bad.rates.z = std::numeric_limits<float>::infinity();
  out = controller.step(250, bad, Command::None);
  return out.state == State::Failsafe && out.reason == Reason::Gyro ? 0 : 1;
}
