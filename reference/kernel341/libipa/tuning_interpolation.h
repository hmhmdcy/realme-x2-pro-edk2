/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <cstdint>
namespace libcamera::ipa {
/* Keep the pinned tuning utility's separate integer/fractional rounding.
 * Callers validate finite int32-representable inputs and a weight in [0,1]. */
inline float interpolateTuningFloat(float first, float second, float weight)
{
 int32_t a=first,b=second;
 double af=double(first-float(a))*1000000.0;
 double bf=double(second-float(b))*1000000.0;
 float fraction=float(af+double(weight)*(bf-af))/1000000.0f;
 float integer=float(double(a)+double(weight)*float(b-a));
 return fraction+integer;
}
} /* namespace libcamera::ipa */
