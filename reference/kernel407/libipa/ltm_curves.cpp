/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ltm_curves.h"
#include <algorithm>
#include <cmath>

namespace libcamera::ipa {
namespace {
bool valid(float value)
{
	/* Bound the public helper before multiplication and integer conversion. */
	return std::isfinite(value) && std::abs(value) <= 1048576.0f;
}

template<std::size_t N>
bool valid(const std::array<float, N> &values)
{
	return std::all_of(values.begin(), values.end(), [](float v) { return valid(v); });
}

float attenuationFor(const Ltm13CurveInput &in)
{
	float change = std::abs(in.exposureIndex - in.previousExposureIndex);
	change = std::min(change, in.attenuationEnd);
	change = std::max(change, in.attenuationStart);
	if (in.attenuationEnd == in.attenuationStart)
		return 1.0f;
	return std::clamp((in.attenuationEnd - change) /
			  (in.attenuationEnd - in.attenuationStart), 0.0f, 1.0f);
}

uint32_t segment(int base, int next, bool lce)
{
	int delta = next - base;
	uint32_t lo = uint32_t(base) & 0xfff;
	uint32_t hi = uint32_t(delta) & 0xfff;
	/* LTM's shifted difference test also forces the sign bit for positive
	 * deltas >=32768. LCE only masks differences after its earlier clamp. */
	if (base < 0)
		lo |= 0x800;
	if (!lce && (delta < 0 || delta >= 32768))
		hi |= 0x800;
	return lo | (hi << 12);
}

template<std::size_t N>
bool encode(const std::array<float, N> &input, std::array<uint32_t, N - 1> &output,
	    bool clampLce)
{
	std::array<int, N> nodes;
	for (std::size_t i = 0; i < N; ++i) {
		if (!valid(input[i]))
			return false;
		float value = std::round(input[i]);
		if (clampLce)
			value = std::clamp(value, -2048.0f, 2047.0f);
		/* The factory casts LTM nodes to int16_t before the upper clamp.
		 * Reject overflow at this typed boundary instead of relying on casts. */
		if (value < -32768.0f || value > 32767.0f)
			return false;
		nodes[i] = std::min(int(value), 2047);
	}
	for (std::size_t i = 0; i < N - 1; ++i)
		output[i] = segment(nodes[i], nodes[i + 1], clampLce);
	return true;
}
} /* namespace */

static bool calculateCurves(const Ltm13CurveInput &in, Ltm13Curves *output,
			    bool withAttenuation)
{
	const std::array<float, 14> controls = {
		in.strength, in.lceStrength, in.attenuationStart, in.attenuationEnd,
		in.darkBoost, in.brightSuppress, in.darkRange, in.brightRange,
		in.darkMaximum, in.brightMaximum, in.darkGamma, in.brightGamma,
		in.exposureIndex, in.previousExposureIndex,
	};
	if (!output || in.manualCurve > 1 || !valid(controls) ||
	    !valid(in.scale) || !valid(in.lcePositive) || !valid(in.lceNegative))
		return false;

	Ltm13Curves result{in.scale, in.lcePositive, in.lceNegative};
	if (in.manualCurve) {
		/* The zero plateau separates the dark and bright treatment regions.
		 * Preserve the factory behaviour when the first value is nonnegative,
		 * or when a negative curve contains no separating zero. */
		std::size_t dark = in.scale[0] >= 0 ? 65 : 0;
		std::size_t bright = dark;
		bool plateau = false;
		for (std::size_t i = 0; i < 65; ++i) {
			if (!plateau && in.scale[i] == 0) {
				dark = i;
				plateau = true;
			} else if (plateau && in.scale[i] != 0) {
				bright = i;
				break;
			}
		}
		for (std::size_t i = 0; i < 65; ++i) {
			if (i < dark)
				result.scale[i] *= in.darkBoost;
			else if (i >= bright)
				result.scale[i] *= in.brightSuppress;
		}
	} else {
		float darkRange = std::clamp(in.darkRange, 0.01f, 1.0f) * 64.0f;
		float brightRange = std::clamp(in.brightRange, 0.01f, 1.0f) * 64.0f;
		float darkMax = std::clamp(in.darkMaximum, 0.0f, 8.0f) * 1024.0f;
		float brightMax = std::clamp(in.brightMaximum, 0.0f, 4.0f) * 1024.0f;
		float darkGamma = std::clamp(in.darkGamma, 1.0f, 5.0f);
		float brightGamma = std::clamp(in.brightGamma, 1.0f, 5.0f);
		for (std::size_t i = 0; i < 65; ++i) {
			float x = float(i);
			float value = 0;
			if (x <= darkRange)
				value = darkMax * std::pow((darkRange - x) / darkRange, darkGamma);
			else if (x >= 65.0f - brightRange)
				value = -brightMax * std::pow((brightRange - (65.0f - x)) / brightRange, brightGamma);
			result.scale[i] = std::clamp(value, -0.9f * brightMax, 0.9f * darkMax);
		}
	}

	float attenuation = withAttenuation ? attenuationFor(in) : 1.0f;
	for (float &value : result.scale) {
		value *= in.strength;
		value *= attenuation;
	}
	for (float &value : result.lcePositive) {
		value *= in.lceStrength;
		value *= attenuation;
	}
	for (float &value : result.lceNegative) {
		value *= in.lceStrength;
		value *= attenuation;
	}
	if (!valid(result.scale) || !valid(result.lcePositive) || !valid(result.lceNegative))
		return false;
	*output = result;
	return true;
}

bool calculateLtm13Curves(const Ltm13CurveInput &input, Ltm13Curves *output)
{
	return calculateCurves(input, output, true);
}

bool prepareLtm13Curves(const Ltm13CurveInput &input, Ltm13Curves *output)
{
	return calculateCurves(input, output, false);
}

bool attenuateLtm13Curves(const Ltm13CurveInput &input, const Ltm13Curves &curves,
			 Ltm13Curves *output)
{
	const std::array<float, 4> controls = {input.exposureIndex, input.previousExposureIndex,
		input.attenuationStart, input.attenuationEnd};
	if (!output || !valid(controls) || !valid(curves.scale) ||
	    !valid(curves.lcePositive) || !valid(curves.lceNegative))
		return false;
	Ltm13Curves result = curves;
	float attenuation = attenuationFor(input);
	for (float &value : result.scale)
		value *= attenuation;
	for (float &value : result.lcePositive)
		value *= attenuation;
	for (float &value : result.lceNegative)
		value *= attenuation;
	*output = result;
	return true;
}

bool encodeLtm13SignedTables(const Ltm13Curves &input, Ltm13SignedTables *output)
{
	if (!output)
		return false;
	Ltm13SignedTables result;
	if (!encode(input.scale, result.scale, false) ||
	    !encode(input.lcePositive, result.lcePositive, true) ||
	    !encode(input.lceNegative, result.lceNegative, true))
		return false;
	*output = result;
	return true;
}
} /* namespace libcamera::ipa */
