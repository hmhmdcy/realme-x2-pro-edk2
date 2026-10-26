/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gamma_profile.h"
#include <array>
#include <cerrno>
#include "libcamera/internal/yaml_parser.h"
#include "../libipa/gamma_curve.h"

namespace libcamera::ipa::camss {
int configureGammaProfile(const ValueNode &tuning,
                          std::optional<camss_params_ife_gamma> *parameters)
{
 if (!parameters)
  return -EINVAL;
 parameters->reset();
 if (tuning.isEmpty())
  return 0;
 if (!tuning.isDictionary())
  return -EINVAL;
 if (!tuning["enabled"].isEmpty()) {
  auto enabled = tuning["enabled"].get<bool>();
  if (!enabled)
   return -EINVAL;
  if (!*enabled)
   return 0;
 }
 if (tuning["mode"].get<std::string>("static") != "static")
  return -EINVAL;
 const auto &curves = tuning["curves"];
 if (!curves.isList() || curves.size() != 3)
  return -EINVAL;
 camss_params_ife_gamma result{};
 result.header = {CAMSS_PARAMS_IFE_GAMMA, V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,
                  sizeof(result)};
 for (unsigned int ch = 0; ch < 3; ++ch) {
  const auto &values = curves[ch];
  if (!values.isList() || values.size() != 65)
   return -EINVAL;
  GammaCurve curve;
  for (unsigned int i = 0; i < curve.size(); ++i) {
   auto sample = values[i].get<float>();
   if (!sample)
    return -EINVAL;
   curve[i] = *sample;
  }
  GammaLut packed;
  if (!encodeGammaCurve(curve, &packed))
   return -EINVAL;
  for (unsigned int i = 0; i < packed.size(); ++i) {
   result.segments[ch][i].base = packed[i] & 1023;
   unsigned int delta = (packed[i] >> 10) & 1023;
   result.segments[ch][i].delta = delta >= 512 ? int(delta) - 1024 : int(delta);
  }
 }
 *parameters = result;
 return 0;
}
} /* namespace libcamera::ipa::camss */
