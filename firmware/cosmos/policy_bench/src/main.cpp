#include <Arduino.h>
#include "actor.hpp"

namespace {
actor::Workspace workspace;
float obs[actor::kInputs] = {0.1f, -0.2f, 0.05f, 0, 0, 0, 1};
float action[actor::kOutputs];
constexpr unsigned kSamples = 256;
}

void setup() {
    Serial.begin(115200);
}

void loop() {
    if (!Serial) {
        delay(50);
        return;
    }
    uint32_t total_us = 0, max_us = 0;
    float checksum = 0;
    for (unsigned i = 0; i < kSamples; ++i) {
        obs[0] = (static_cast<int>(i) - 128) * 0.002f;
        const uint32_t start = micros();
        actor::predict(obs, action, workspace);
        const uint32_t duration = micros() - start;
        total_us += duration;
        if (duration > max_us) max_us = duration;
        for (float value : action) checksum += value;
    }
    Serial.printf("model=%s normalization=%s n=%u mean_us=%.2f max_us=%lu "
                  "parameter_bytes=%u workspace_bytes=%u checksum=%.6f\n",
                  actor::kModelHash, actor::kNormalization, kSamples,
                  static_cast<double>(total_us) / kSamples, static_cast<unsigned long>(max_us),
                  static_cast<unsigned>(actor::kParameterBytes),
                  static_cast<unsigned>(sizeof(workspace)), static_cast<double>(checksum));
    delay(1000);
}
