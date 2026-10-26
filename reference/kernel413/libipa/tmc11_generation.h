/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include "../../kernel412/libipa/tmc11_ltm.h"
#include <array>
#include <cstdint>

namespace libcamera::ipa {
struct Tmc11Region {
	float gtmPercentage, ltmPercentage, darkBoostRatio;
	std::array<float,5> toneTargets, toneAnchors;
	float toneBrightAdjustment, toneDarkAdjustment, stretchBright, stretchDark;
	float suppressStart, suppressEnd, boostStart, boostEnd, averageStart, averageEnd;
	std::array<float,5> histogramKernel;
	float histogramClipSlope, histogramEnhanceClamp;
	std::array<float,5> histogramEnhanceRatio;
	float contrastBrightClip, contrastDarkAdjustment, contrastHEBright, contrastHEDark;
	std::array<float,5> reserve;
};
struct Tmc11GenerationResult {
	Tmc11PchipCurve pchip;
	Tmc11LtmContrast ltm;
	float darkGain, gtmPercentage;
	std::array<float,1024> processedHistogram, contrastCurve;
};
/* Region interpolation and runtime version selection are caller decisions.
 * Statistics are explicit: nullptr reproduces the target's absent-histogram
 * path, and is different from a present histogram containing all zero bins.
 * Gamma and logarithmic bin weights are caller-owned calibration tables.
 * Failure preserves output; all inputs remain immutable. */
bool generateTmc11Curve(const Tmc11Region &region, float drcGain, float darkGain,
		       const std::array<float,257> &gamma10,
		       const std::array<float,1024> &histogramLogWeights,
		       const std::array<uint32_t,1024> *histogram,
		       Tmc11GenerationResult *output);
} /* namespace libcamera::ipa */
