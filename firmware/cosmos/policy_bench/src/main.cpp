#include <Arduino.h>
#include "actor.hpp"

static_assert(actor::kInputs == 8, "obs initializer below assumes the 8 Stage 1 observations (#347)");

namespace {
actor::Workspace workspace;
float obs[actor::kInputs] = {0.1f, -0.2f, 0.05f, 1.0f, 0, 0, 0, 1};  // phi, theta, sin_psi, cos_psi, wx, wy, wz, throttle
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
    Serial.printf("model=%s normalization=%s action_layout=%s parity_episodes=%u parity_max_abs=%.3g "
                  "n=%u mean_us=%.2f max_us=%lu "
                  "parameter_bytes=%u workspace_bytes=%u checksum=%.6f checksum_pc=%.6f\n",
                  actor::kModelHash, actor::kNormalization, actor::kActionLayout, actor::kParityEpisodes,
                  static_cast<double>(actor::kParityMaxAbs), kSamples,
                  static_cast<double>(total_us) / kSamples, static_cast<unsigned long>(max_us),
                  static_cast<unsigned>(actor::kParameterBytes),
                  static_cast<unsigned>(sizeof(workspace)), static_cast<double>(checksum),
                  static_cast<double>(actor::kBenchChecksumPc));
    delay(1000);
}
