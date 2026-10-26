/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <optional>
#include <linux/qcom-camss-config.h>
namespace libcamera {
class ValueNode;
namespace ipa::camss {
/* An absent/disabled override retains the output format's transfer curve. */
int configureGammaProfile(const ValueNode &tuning,
                          std::optional<camss_params_ife_gamma> *parameters);
} /* namespace ipa::camss */
} /* namespace libcamera */
