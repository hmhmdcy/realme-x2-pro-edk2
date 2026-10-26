/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>

namespace libcamera::ipa {
struct Tmc10Parameters {
	float drcGain, drcGainDark;
	float gtmPercentage, ltmPercentage;
	float kneeOutMid, darkBoostRatio, coreReserve1;
};
struct Tmc10Curve {
	std::array<float, 4> x, y;
	std::array<float, 6> coefficient;
	float darkGain, ltmPercentage, gtmPercentage, ltmMix;
};

/* These helpers implement version10 numeric policy, without selecting a
 * version, enabling a disabled tuning root, or reading trigger trees. */
bool calculateTmc10Curve(const Tmc10Parameters &input, Tmc10Curve *output);
/* The normalization endpoint must be positive, including at percentage0.
 * Nonfinite results from degenerate curves preserve the caller's output. */
bool sampleTmc10LtmGain(const Tmc10Curve &curve,
		       const std::array<float, 65> &equivalent,
		       std::array<float, 65> *gainQ10);
} /* namespace libcamera::ipa */
