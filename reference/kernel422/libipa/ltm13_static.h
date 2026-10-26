/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>

namespace libcamera::ipa {
/* Selected reserve and interpolated LA values. No tuning coefficients live in
 * the implementation. Geometry and per-frame temporal/ADRC curves are separate. */
struct Ltm13StaticInput {
	std::array<float, 4> rgb2y;
	float yRatioMaximum;
	uint32_t reverseGamma, localAdaptation, maskFilter, dataCollection, imageProcessing;
	std::array<int32_t, 24> weights;
	std::array<int32_t, 6> maskKernel;
	std::array<int32_t, 65> maskCurve;
	std::array<float, 65> laCurve;
	uint32_t lceThreshold;
};
struct Ltm13StaticResult {
	std::array<uint32_t, 4> rgb2y;
	uint32_t yRatioMaximum;
	uint32_t reverseGamma, localAdaptation, maskFilter, dataCollection, imageProcessing;
	std::array<uint32_t, 6> maskKernel;
	uint32_t maskScale, maskShift, lceThreshold;
	std::array<uint32_t, 12> weights;
	std::array<uint32_t, 64> mask, la;
};
/* Target LTM13 arithmetic, without commands or device addresses. Invalid
 * nonfinite/overflowing input preserves output. The inverse-Gamma primitive
 * and strength/temporal/ADRC primitives are reused independently. */
bool prepareLtm13Static(const Ltm13StaticInput &input, Ltm13StaticResult *output);
} /* namespace libcamera::ipa */
