/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>

namespace libcamera::ipa {
struct Tmc11PchipCurve {
	std::array<float, 5> x, y;
	std::array<float, 9> coefficient;
};
struct Tmc11PchipResult {
	std::array<float, 65> gain;
	float ltmMix;
};
struct Tmc11LtmContrast {
	float percentage, bright, dark;
};
/* These are model2 numerical primitives. The caller supplies already
 * selected/generated TMC11 knees and histogram contrast data; no version,
 * tuning root, or histogram is selected or generated here. Failure leaves
 * output intact. Axis and curve tables remain caller-owned calibration. */
bool normalizeTmc11LtmInput(const std::array<float, 65> &equivalent12,
			   std::array<float, 65> *normalized);
bool sampleTmc11Pchip(const Tmc11PchipCurve &curve,
		     const std::array<float, 65> &normalized,
		     Tmc11PchipResult *output);
bool applyTmc11LtmContrast(const Tmc11LtmContrast &parameters,
			  const std::array<float, 65> &normalized,
			  const std::array<float, 65> &linearGain,
			  const std::array<float, 1024> &axis,
			  const std::array<float, 1024> &contrastCurve,
			  std::array<float, 65> *gainQ10);
} /* namespace libcamera::ipa */
