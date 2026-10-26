/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include "gamma_segments.h"
#include "tuning_interpolation.h"

namespace libcamera::ipa {
/* Channel order and common-channel expansion belong to the profile reader.
 * This function operates on one normalized channel at a time. */
template<std::size_t Segments>
bool interpolateGammaSamples(const GammaSamples<Segments> &first,
                             const GammaSamples<Segments> &second, float weight,
                             GammaSamples<Segments> *result)
{
 if (!result || !std::isfinite(weight) || weight < 0.0f || weight > 1.0f)
  return false;
 for (std::size_t i = 0; i <= Segments; ++i)
  if (!std::isfinite(first[i]) || first[i] < 0.0f || first[i] > 1024.0f ||
      !std::isfinite(second[i]) || second[i] < 0.0f || second[i] > 1024.0f)
   return false;
 GammaSamples<Segments> output;
 for (std::size_t i = 0; i <= Segments; ++i)
  output[i] = weight == 0.0f ? first[i] :
              weight == 1.0f ? second[i] :
              interpolateTuningFloat(first[i], second[i], weight);
 *result = output;
 return true;
}
} /* namespace libcamera::ipa */
