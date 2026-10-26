/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>

namespace libcamera::ipa {

using AwbRatio = std::array<float, 2>;
using AwbIlluminantRatios = std::array<AwbRatio, 10>;
using AwbIlluminantGains = std::array<std::array<float, 3>, 10>;

/* Ratios are R/G and B/G, not correction gains. CCT coordinates come from
 * the selected factory calibration, independently of the unit payload tags. */
struct AwbCalibrationData {
	unsigned int count;
	std::array<float, 6> colourTemperatures;
	std::array<AwbRatio, 6> golden;
	std::array<AwbRatio, 6> unit;
};

bool awbCalibrationFactors(const AwbCalibrationData &data,
			   AwbIlluminantRatios *factors);
bool awbCalibratedMwbRatios(const AwbIlluminantGains &gains,
			    const AwbIlluminantRatios &factors,
			    AwbIlluminantRatios *ratios);
bool awbRatiosForColourTemperature(const AwbIlluminantRatios &ratios,
				   float kelvin, AwbRatio *result);

} /* namespace libcamera::ipa */
