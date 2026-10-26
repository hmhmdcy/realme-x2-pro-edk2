/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>

namespace libcamera::ipa {
using IfeGammaBaseNodes = std::array<uint16_t, 64>;
/* LTM has 14-bit bases and signed 14-bit differences. This is not an IFE
 * Gamma table, despite both engines having 64 segments. */
struct Ltm13InverseGammaTable {
 std::array<uint32_t, 64> segments;
};

bool encodeLtm13InverseGamma(const IfeGammaBaseNodes &input,
                             Ltm13InverseGammaTable *output);
} /* namespace libcamera::ipa */
