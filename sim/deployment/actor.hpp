#pragma once

#include <cmath>
#include <cstddef>
#include <actor_data.h>

namespace actor {

template <std::size_t Inputs, std::size_t Outputs>
inline void linear(const float (&input)[Inputs], const float (&weights)[Outputs][Inputs],
                   const float (&bias)[Outputs], float (&output)[Outputs]) {
    for (std::size_t row = 0; row < Outputs; ++row) {
        float sum = bias[row];
        for (std::size_t col = 0; col < Inputs; ++col) {
            sum += weights[row][col] * input[col];
        }
        output[row] = sum;
    }
}

struct Workspace {
    float input[kInputs];
    float hidden1[kHidden1];
    float hidden2[kHidden2];
};

inline void predict(const float (&obs)[kInputs], float (&action)[kOutputs], Workspace &work) {
    for (std::size_t i = 0; i < kInputs; ++i) {
        work.input[i] = normalize(i, obs[i]);
    }
    linear(work.input, w1, b1, work.hidden1);
    for (float &value : work.hidden1) value = std::tanh(value);
    linear(work.hidden1, w2, b2, work.hidden2);
    for (float &value : work.hidden2) value = std::tanh(value);
    linear(work.hidden2, w3, b3, action);
    for (float &value : action) {
        if (value < -1.0f) value = -1.0f;
        if (value > 1.0f) value = 1.0f;
    }
}

constexpr std::size_t kParameterBytes =
    sizeof(w1) + sizeof(b1) + sizeof(w2) + sizeof(b2) + sizeof(w3) + sizeof(b3);

}  // namespace actor
