/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gamma_curve.h"
#include <algorithm>
#include <cmath>

namespace libcamera::ipa {
bool encodeGammaCurve(const GammaCurve &curve, GammaLut *lut)
{
 if (!lut)
  return false;
 for (float sample : curve)
  if (!std::isfinite(sample) || sample < 0.0f || sample > 1024.0f)
   return false;

 GammaLut result;
 for (unsigned int i = 0; i < result.size(); ++i) {
  int base = std::min(static_cast<int>(std::round(curve[i])), 1023);
  int next = std::min(static_cast<int>(std::round(curve[i + 1])),
                      i + 1 == result.size() ? 1024 : 1023);
  int delta = std::clamp(next - base, -512, 511);
  result[i] = static_cast<uint32_t>(base) |
              ((static_cast<uint32_t>(delta) & 0x3ff) << 10);
 }
 *lut = result;
 return true;
}
} /* namespace libcamera::ipa */
