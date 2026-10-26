/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ltm_adrc.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace libcamera::ipa {
namespace {
template<std::size_t N>
bool valid(const std::array<float, N> &input, float minimum, float maximum)
{
	return std::all_of(input.begin(), input.end(), [=](float value) {
		return std::isfinite(value) && value >= minimum && value <= maximum;
	});
}

float interpolate(float a, float b, float ratio)
{
	/* The target interpolates integer and fractional parts separately. Float
 * lerp and a fused double expression do not preserve its rounding. */
	int ai = int(a), bi = int(b);
	double af = double(a - float(ai)) * 1000000.0;
	double bf = double(b - float(bi)) * 1000000.0;
	volatile double fractionalStep = double(ratio) * (bf - af);
	float fraction = float(af + fractionalStep) / 1000000.0f;
	volatile double integerStep = double(ratio) * float(bi - ai);
	float integer = float(double(ai) + integerStep);
	return fraction + integer;
}
} /* namespace */

bool calculateLtm13Adrc(const Ltm13AdrcSamples &in, Ltm13AdrcCurves *output)
{
	if (!output || !valid(in.equivalent12, 0, 4095) ||
	    !valid(in.sampledGainQ10, 0, std::numeric_limits<float>::max()) ||
	    in.sampledGainQ10[0] < 1024 ||
	    !valid(in.forwardGamma10, 0, 1024))
		return false;
	float drcGain = in.sampledGainQ10[0] / 1024.0f;
	float curveGain = 1;
	if (drcGain > 2047.0f / 1024.0f)
		curveGain = std::clamp((drcGain - 1.0f) / (2047.0f / 1024.0f), 1.0f, 3.6f);
	std::array<float, 65> forward, indices;
	for (std::size_t i = 0; i < 65; ++i) {
		forward[i] = in.forwardGamma10[i] * 4.0f;
		indices[i] = std::clamp(((in.sampledGainQ10[i] / 1024.0f) *
			in.equivalent12[i]) * 64.0f / 4095.0f, 0.0f, 64.0f);
	}
	Ltm13AdrcCurves result{};
	for (std::size_t i = 1; i < 65; ++i) {
		unsigned int x1 = unsigned(indices[i]);
		unsigned int x2 = x1 + 1;
		float right = x2 >= 64 ? 4096.0f : forward[x2];
		float ratio = (indices[i] - float(x1)) / float(x2 - x1);
		float equivalent = std::clamp(interpolate(forward[x1], right, ratio), 0.0f, 4095.0f);
		result.scale[i] = std::clamp((1024.0f * (equivalent / float(64 * i) - 1.0f)) /
					     curveGain, 0.0f, 2047.0f);
	}
	result.scale[0] = result.scale[1];
	result.scale[64] = result.scale[63];
	float maximum = result.scale[64];
	for (int i = 64; i >= 0; --i) {
		if (result.scale[i] < maximum)
			result.scale[i] = maximum;
		else
			maximum = result.scale[i];
	}
	unsigned int lastMaximum = 0;
	for (unsigned int i = 0; i < 64 / 3; ++i)
		if (result.scale[i] == maximum && i > lastMaximum)
			lastMaximum = i;
	lastMaximum = std::max(lastMaximum, 1U);
	for (unsigned int pass = 0; pass < 3; ++pass)
		for (unsigned int i = lastMaximum + 1; i < 64; ++i)
			result.scale[i] = (result.scale[i - 1] + result.scale[i] + result.scale[i + 1]) / 3.0f;
	for (std::size_t i = 0; i < 65; ++i)
		result.curve[i] = float(64 * i) * curveGain;
	int flat = int(std::floor(64.0f / (drcGain * 3.0f)));
	int span = 64 - flat;
	for (int i = 0; i <= span; ++i)
		result.curve[i + flat] *= span ? float(span - i) / float(span) : 0.0f;
	for (unsigned int pass = 0; pass < 4; ++pass)
		for (unsigned int i = 1; i < 64; ++i)
			result.curve[i] = (result.curve[i - 1] + result.curve[i] + result.curve[i + 1]) / 3.0f;
	*output = result;
	return true;
}

bool blendLtm13Adrc(const Ltm13AdrcCurves &adrc, float mix,
		    const std::array<int32_t, 65> &reserveCurve,
		    const std::array<int16_t, 65> &baseScale,
		    Ltm13AdrcBlend *output)
{
	if (!output || !std::isfinite(mix) || mix < 0 || mix > 1 ||
	    !valid(adrc.scale, 0, 2047) || !valid(adrc.curve, 0, 16384) ||
	    std::any_of(reserveCurve.begin(), reserveCurve.end(), [](int32_t value) {
		return value < 0 || value > 16383;
	    }))
		return false;
	Ltm13AdrcBlend result{};
	float ratio = mix > 0 ? 3.0f : 1.0f;
	for (std::size_t i = 0; i < 65; ++i) {
		result.curve[i] = int32_t(std::round(interpolate(adrc.curve[i] * ratio,
							float(reserveCurve[i]), mix)));
		result.scale[i] = int16_t(std::max(float(baseScale[i]) * mix, adrc.scale[i] / ratio));
	}
	*output = result;
	return true;
}

bool encodeLtm13AdrcTables(const Ltm13AdrcBlend &input, Ltm13AdrcTables *output)
{
	if (!output || std::any_of(input.curve.begin(), input.curve.end(),
				 [](int32_t value) { return value < 0; }))
		return false;
	Ltm13AdrcTables result{};
	for (std::size_t family = 0; family < 2; ++family) {
		std::array<int, 65> nodes;
		for (std::size_t i = 0; i < 65; ++i)
			nodes[i] = family ? std::min(int(input.scale[i]), 2047) :
					  std::min(int(input.curve[i]), 4095);
		for (std::size_t i = 0; i < 64; ++i) {
			int delta = nodes[i + 1] - nodes[i];
			uint32_t base = uint32_t(nodes[i]) & 4095;
			uint32_t difference = uint32_t(delta) & 4095;
			if (nodes[i] < 0)
				base |= 2048;
			/* The source tests delta >> 15 != 0: this also covers large
			 * positive differences of signed int16 nodes, not just negatives. */
			if (delta < 0 || delta >= 32768)
				difference |= 2048;
			(family ? result.scale : result.curve)[i] = base | (difference << 12);
		}
	}
	*output = result;
	return true;
}
} /* namespace libcamera::ipa */
