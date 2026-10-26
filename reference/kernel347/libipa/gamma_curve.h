/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>

namespace libcamera::ipa {
using GammaCurve = std::array<float, 65>;
using GammaLut = std::array<uint32_t, 64>;

/* Input/output are in the native 10-bit Gamma16 domain. The 65th sample
 * supplies the final slope. This encoder does not upload or activate a LUT. */
bool encodeGammaCurve(const GammaCurve &curve, GammaLut *lut);
} /* namespace libcamera::ipa */
