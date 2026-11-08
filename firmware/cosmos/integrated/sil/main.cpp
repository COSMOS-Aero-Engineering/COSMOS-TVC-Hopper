// Each line is one input snapshot. Timestamps of -1 mean "never received".
#include "../src/telemetry.h"
#include <iostream>
#include <sstream>
#include <string>

namespace {
using namespace hopper;

bool stamp(int64_t raw, Stamp& out) {
  if (raw < -1 || raw > UINT32_MAX) return false;
  out = {raw >= 0, static_cast<uint32_t>(raw)};
  return true;
}

bool parse(const std::string& line, uint32_t& now, Inputs& in, Command& command) {
  std::istringstream stream(line);
  int64_t tick, attMs, gyroMs, thrMs, killMs;
  int thrUs, killUs;
  std::string op, extra;
  auto& q = in.attitude;
  auto& g = in.rates;
  if (!(stream >> tick >> attMs >> q.w >> q.x >> q.y >> q.z >> gyroMs >> g.x >> g.y >> g.z
               >> thrMs >> thrUs >> killMs >> killUs >> op) || stream >> extra) return false;
  Stamp thr{}, kill{};
  if (tick < 0 || tick > UINT32_MAX || !stamp(attMs, q.stamp) || !stamp(gyroMs, g.stamp) ||
      !stamp(thrMs, thr) || !stamp(killMs, kill) ||
      thrUs < 0 || thrUs > UINT16_MAX || killUs < 0 || killUs > UINT16_MAX) return false;
  if (op == "arm") command = Command::Arm;
  else if (op == "disarm") command = Command::Disarm;
  else if (op == "-") command = Command::None;
  else return false;
  now = static_cast<uint32_t>(tick);
  in.throttle = {thr.seen, static_cast<uint16_t>(thrUs), thr.ms};
  in.kill = {kill.seen, static_cast<uint16_t>(killUs), kill.ms};
  return true;
}
}  // namespace

int main() {
  Controller controller;
  std::cout << kCsvHeader << std::endl;
  std::string line;
  unsigned lineNumber = 0;
  while (std::getline(std::cin, line)) {
    Inputs in{};
    Command command{};
    uint32_t now;
    ++lineNumber;
    if (!parse(line, now, in, command)) {
      std::cerr << "Invalid input snapshot on line " << lineNumber << '\n';
      return 2;
    }
    Result result = controller.step(now, in, command);
    char row[kCsvCapacity];
    if (!csvRow(row, now, Source::Sil, in, result)) return 1;
    std::cout << row << std::endl;
  }
  return std::cin.bad() ? 1 : 0;
}
