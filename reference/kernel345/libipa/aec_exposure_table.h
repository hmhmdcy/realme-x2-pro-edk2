/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <cstdint>
#include <vector>

namespace libcamera::ipa {
enum class AecExposurePriority : uint32_t { Gain=0, Time=1, Maximum=2 };
struct AecExposureKnee {
 float gain;
 uint64_t exposureTimeNs;
 AecExposurePriority priority;
 float index;
};
struct AecExposureAllocation {
 float gain;
 uint64_t exposureTimeNs;
 float index;
};

/* Exposure indices use the factory logarithmic domain, not EV or physical lux.
 * This lookup consumes an already selected table. FPS/EV knee construction,
 * sensor limits and anti-banding are separate caller responsibilities. */
class AecExposureTable {
public:
 bool configure(const std::vector<AecExposureKnee> &knees);
 bool allocate(float index,AecExposureAllocation *allocation) const;
 /* Reproduce the OEM float knee construction; this is not a final sensor
  * time clamp. The caller must still apply the actual line/frame limits. */
 bool frameTimeKnee(uint64_t maximumExposureTimeNs,AecExposureKnee *knee) const;
private:
 std::vector<AecExposureKnee> knees_;
};
} /* namespace libcamera::ipa */
