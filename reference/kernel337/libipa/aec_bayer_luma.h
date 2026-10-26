/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>
#include <vector>

namespace libcamera::ipa {

/* Channel order matches the common Bayer grid statistics: R,B,GR,GB. */
struct AecBayerRegion {
 std::array<uint32_t,4> sums;
 std::array<uint16_t,4> counts;
};
struct AecBayerLumaConfiguration {
 uint32_t pixelsPerChannel;
 std::array<uint32_t,4> highThreshold;
 unsigned int inputBits;
 std::array<float,3> weights; /* R,G,B, including optional colour compensation. */
 float normalization; /* Explicit upstream normalization;1 for current SDR. */
};
struct AecLumaCell {float luma,saturatedFraction;};

bool aecLumaWeights(const std::array<float,3> &tuning,
                    const std::array<float,3> &referenceGains,
                    const std::array<float,3> &currentGains,
                    bool compensate,std::array<float,3> *weights);

/* RGB Bayer input without an explicit saturated-sums extension. Missing
 * pixels are accounted for using each channel's saturation threshold. */
bool aecBayerRegionLuma(const AecBayerLumaConfiguration &configuration,
                        const AecBayerRegion &region,AecLumaCell *result);

/* All valid regions, sampling stride1. Original geometry requires dimensions
 * divisible by16; an incompatible grid must be reconfigured at the source. */
bool aecLegacyLumaGrid(const std::vector<AecLumaCell> &regions,
                       unsigned int columns,unsigned int rows,
                       std::array<AecLumaCell,256> *result);

} /* namespace libcamera::ipa */
