// Input-only Teensy adapter. Generated commands go exclusively to USB CSV.
#include <Arduino.h>
#include "../../imu_test/src/BNO080.h"
#include "telemetry.h"

namespace {
using namespace hopper;

BNO080 imu(10, 22, 21, 20);  // CS, WAKE, INT, RST: imu_test SPI wiring
bool imuReady;
Inputs input{};
Controller controller;
uint32_t lastTick;

struct PulseInput {
  uint8_t pin;
  uint32_t rise;
  bool high;
  RcSample sample;
};

// rc_bench CH1 and CH5. SPI leaves the CH1 pin free (the I2C bench does not).
volatile PulseInput throttle{18, 0, false, {}}, kill{9, 0, false, {}};

void edge(volatile PulseInput& channel) {
  const uint32_t us = micros();
  if (digitalReadFast(channel.pin)) {
    channel.rise = us;
    channel.high = true;
  } else if (channel.high) {
    channel.high = false;
    uint32_t width = us - channel.rise;
    if (width >= RC_MIN_VALID_US && width <= RC_MAX_VALID_US) {
      channel.sample.widthUs = static_cast<uint16_t>(width);
      channel.sample.lastValidMs = millis();
      channel.sample.seen = true;
    }
  }
}
void throttleEdge() { edge(throttle); }
void killEdge() { edge(kill); }

RcSample snapshot(volatile RcSample& s, uint32_t now) {
  if (now - s.lastValidMs >= kRcTimeoutMs) s.seen = false;
  return {s.seen, s.widthUs, s.lastValidMs};
}

void pollImu() {
  if (!imuReady) return;
  const uint16_t id = imu.getReadings();
  const Stamp received{true, millis()};
  if (id == SENSOR_REPORTID_GAME_ROTATION_VECTOR) {
    input.attitude = {received, imu.getQuatReal(), imu.getQuatI(), imu.getQuatJ(), imu.getQuatK()};
  } else if (id == SENSOR_REPORTID_GYROSCOPE) {
    input.rates = {received, imu.getGyroX(), imu.getGyroY(), imu.getGyroZ()};
  }
}

Command readCommand() {
  Command command = Command::None;
  // '+' requests dry-run arm, '!' disarms. Stop takes priority within a tick.
  for (int n = Serial.available(); n > 0; --n) {
    int c = Serial.read();
    if (c == '!') command = Command::Disarm;
    if (c == '+' && command == Command::None) command = Command::Arm;
  }
  return command;
}
}  // namespace

void setup() {
  Serial.begin(115200);
  pinMode(throttle.pin, INPUT_PULLDOWN);
  pinMode(kill.pin, INPUT_PULLDOWN);
  attachInterrupt(digitalPinToInterrupt(throttle.pin), throttleEdge, CHANGE);
  attachInterrupt(digitalPinToInterrupt(kill.pin), killEdge, CHANGE);
  imuReady = imu.beginSPI();
  if (imuReady) {
    imu.enableGameRotationVector(kPeriodMs);
    imu.enableGyro(kPeriodMs);
  }
}

void loop() {
  pollImu();
  if (millis() - lastTick < kPeriodMs) return;
  noInterrupts();
  uint32_t now = millis();
  input.throttle = snapshot(throttle.sample, now);
  input.kill = snapshot(kill.sample, now);
  interrupts();
  lastTick = now;
  if (now - input.attitude.stamp.ms >= kImuTimeoutMs) input.attitude.stamp.seen = false;
  if (now - input.rates.stamp.ms >= kImuTimeoutMs) input.rates.stamp.seen = false;
  const bool connected = static_cast<bool>(Serial);
  const Result result = controller.step(now, input, connected ? readCommand() : Command::Disarm);

  static bool headerSent = false;
  if (!connected) {
    headerSent = false;
    return;
  }
  if (!headerSent) {
    Serial.println(kCsvHeader);
    headerSent = true;
  }
  char row[kCsvCapacity];
  size_t len = csvRow(row, now, Source::BoardInputs, input, result);
  if (len && Serial.availableForWrite() >= static_cast<int>(len + 2)) Serial.println(row);
}
