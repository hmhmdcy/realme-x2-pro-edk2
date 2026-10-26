/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <optional>
#include "libcamera/internal/yaml_parser.h"
#include "../libipa/awb_calibration.h"
#include "../libipa/awb_colour_temperature.h"

namespace libcamera::ipa::camss {

class WhiteBalanceReference {
public:
	int gains(int32_t kelvin, double *red, double *blue) const;
	std::optional<int32_t> temperature(double red, double blue) const;
	static int configure(const ValueNode &tuning,
			     std::optional<WhiteBalanceReference> *reference);
private:
	AwbIlluminantRatios ratios_;
	std::optional<AwbColourTemperatureModel> inverse_;
};

} /* namespace libcamera::ipa::camss */
