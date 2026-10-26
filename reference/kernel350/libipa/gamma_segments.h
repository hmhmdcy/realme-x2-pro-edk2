/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace libcamera::ipa {
/* The number of segments is part of the engine's contract. IFE uses 64,
 * IPE uses 256; neither table is a 256-entry direct output-value map. */
template<std::size_t Segments>
using GammaSamples = std::array<float, Segments + 1>;
template<std::size_t Segments>
using GammaSegments = std::array<uint32_t, Segments>;

template<std::size_t Segments>
bool encodeGammaSegments(const GammaSamples<Segments> &samples,
                         GammaSegments<Segments> *segments)
{
 static_assert(Segments > 0);
 if (!segments)
  return false;
 for (float value : samples)
  if (!std::isfinite(value) || value < 0.0f || value > 1024.0f)
   return false;
 GammaSegments<Segments> result;
 for (std::size_t i = 0; i < Segments; ++i) {
  int base = std::min(static_cast<int>(std::round(samples[i])), 1023);
  int next = std::min(static_cast<int>(std::round(samples[i + 1])),
                      i + 1 == Segments ? 1024 : 1023);
  int delta = std::clamp(next - base, -512, 511);
  result[i] = static_cast<uint32_t>(base) |
              ((static_cast<uint32_t>(delta) & 1023) << 10);
 }
 *segments = result;
 return true;
}
} /* namespace libcamera::ipa */
