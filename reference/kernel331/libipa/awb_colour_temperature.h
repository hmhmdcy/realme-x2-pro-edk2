/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include "awb_calibration.h"

namespace libcamera::ipa {

bool awbCalibratedReferenceRatios(const AwbIlluminantRatios &points,
				const AwbIlluminantRatios &factors,
				AwbIlluminantRatios *result);

/* This reference-point locus is distinct from the forward MWB gain table. */
struct AwbColourTemperatureEstimate {
	float kelvin;
	float signedDistance;
	unsigned int illuminant;
};

class AwbColourTemperatureModel {
public:
	bool configure(const AwbIlluminantRatios &points);
	bool estimate(const AwbRatio &ratio, AwbColourTemperatureEstimate *result) const;

private:
	using Line = std::array<float, 3>;
	AwbIlluminantRatios points_{};
	std::array<Line, 8> locus_{}, boundaries_{};
	std::array<float, 8> lengthsSquared_{};
	bool configured_ = false;
};

} /* namespace libcamera::ipa */
