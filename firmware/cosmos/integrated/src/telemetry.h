#pragma once

#include "control.h"
#include <stddef.h>

namespace hopper {

constexpr char kCsvHeader[] =
    "t_ms,source,mode,phi,theta,psi,qw,qx,qy,qz,wx,wy,wz,servo1,servo2,servo3,servo4,"
    "throttle,batt_v,rpm,reward,fsm,reason,dry_run";
constexpr size_t kCsvCapacity = 320;
enum class Source { Sil, BoardInputs };

// Returns the byte count, or zero on formatting error. No allocation on the board.
size_t csvRow(char (&row)[kCsvCapacity], uint32_t now, Source source,
              const Inputs& in, const Result& result);

}  // namespace hopper
