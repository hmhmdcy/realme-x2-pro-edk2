/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <optional>
#include "libcamera/internal/yaml_parser.h"
#include "../libipa/awb_calibration.h"

namespace libcamera::ipa::camss {

class WhiteBalanceReference {
public:
	int gains(int32_t kelvin, double *red, double *blue) const;
	static int configure(const ValueNode &tuning,
			     std::optional<WhiteBalanceReference> *reference);
private:
	AwbIlluminantRatios ratios_;
};

} /* namespace libcamera::ipa::camss */
