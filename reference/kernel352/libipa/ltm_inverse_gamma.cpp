/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ltm_inverse_gamma.h"
#include <algorithm>
#include <cstdlib>
#include <limits>

namespace libcamera::ipa {
namespace {
int floorDivide32(int value)
{
 return value >= 0 ? value / 32 : -((-value + 31) / 32);
}

uint32_t packSegment(int base, int next)
{
 uint32_t delta = uint32_t(next - base) & 0x3fff;
 /* Preserve the LTM packer's explicit negative sign bit, including
  * negative differences outside the ordinary signed 14-bit range. */
 if (next < base)
  delta |= 0x2000;
 return uint32_t(base & 0x3fff) |
        (delta << 14);
}
} /* namespace */

bool encodeLtm13InverseGamma(const IfeGammaBaseNodes &input,
                             Ltm13InverseGammaTable *output)
{
 if (!output || std::any_of(input.begin(), input.end(),
                           [](uint16_t value) { return value > 1023; }))
  return false;

 /* Reconstruct the quantized forward mapping once. Searching this mapping
  * preserves the original earliest-index rule even for flat/nonmonotonic
  * input; an analytic inverse or binary search would change those cases. */
 std::array<int, 4096> forward;
 for (unsigned int segment = 0; segment < input.size(); ++segment) {
  int base = input[segment] * 16;
  int next = segment + 1 == input.size() ? 16383 : input[segment + 1] * 16;
  uint32_t encodedDelta = packSegment(base, next) >> 14;
  int delta = encodedDelta >= 8192 ? int(encodedDelta) - 16384 : int(encodedDelta);
  for (unsigned int offset = 0; offset < 64; ++offset)
   forward[segment * 64 + offset] = base * 2 + floorDivide32(delta * int(offset) + 16);
 }

 std::array<int, 65> inverse;
 for (unsigned int node = 0; node < inverse.size(); ++node) {
  int target = std::min(int(node) * 512, 32760);
  int bestError = std::numeric_limits<int>::max();
  unsigned int bestIndex = 0;
  for (unsigned int i = 0; i < forward.size(); ++i) {
   int error = std::abs(forward[i] - target);
   if (error < bestError) {
    bestError = error;
    bestIndex = i;
   }
  }
  inverse[node] = int(bestIndex) * 4;
 }

 Ltm13InverseGammaTable result;
 for (unsigned int i = 0; i < result.segments.size(); ++i)
  result.segments[i] = packSegment(inverse[i], inverse[i + 1]);
 *output = result;
 return true;
}
} /* namespace libcamera::ipa */
