/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>

namespace libcamera::ipa {

/* Interpolated Chromatix values, before OEM temporal smoothing and ADRC.
 * The generator is userspace math; the kernel accepts quantized requests. */
struct Ltm13CurveInput {
	std::array<float, 65> scale;
	std::array<float, 17> lcePositive;
	std::array<float, 17> lceNegative;
	float strength;
	float lceStrength;
	float attenuationStart;
	float attenuationEnd;
	float darkBoost;
	float brightSuppress;
	float darkRange;
	float brightRange;
	float darkMaximum;
	float brightMaximum;
	float darkGamma;
	float brightGamma;
	float exposureIndex;
	float previousExposureIndex;
	uint32_t manualCurve;
};

struct Ltm13Curves {
	std::array<float, 65> scale;
	std::array<float, 17> lcePositive;
	std::array<float, 17> lceNegative;
};

struct Ltm13SignedTables {
	std::array<uint32_t, 64> scale;
	std::array<uint32_t, 16> lcePositive;
	std::array<uint32_t, 16> lceNegative;
};

/* These functions do not modify output when validation fails. No temporal state
 * is changed, and the input curves are retained for the next interpolation. */
bool calculateLtm13Curves(const Ltm13CurveInput &input, Ltm13Curves *output);
bool encodeLtm13SignedTables(const Ltm13Curves &input, Ltm13SignedTables *output);

/* Separate phases allow the target's temporal treatment between strength
 * calculation and exposure attenuation. The original combined API retains
 * its behaviour when no temporal treatment is requested. */
bool prepareLtm13Curves(const Ltm13CurveInput &input, Ltm13Curves *output);
bool attenuateLtm13Curves(const Ltm13CurveInput &input, const Ltm13Curves &curves,
			 Ltm13Curves *output);

} /* namespace libcamera::ipa */
