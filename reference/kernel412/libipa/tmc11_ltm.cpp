/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "tmc11_ltm.h"
#include <algorithm>
#include <cmath>

namespace libcamera::ipa {
namespace {
float mul(float a, float b)
{
	volatile float value = a * b;
	return value;
}
template<std::size_t N>
bool finite(const std::array<float, N> &values)
{
	return std::all_of(values.begin(), values.end(), [](float v) { return std::isfinite(v); });
}
template<std::size_t N>
bool nonnegative(const std::array<float, N> &values)
{
	return finite(values) && std::all_of(values.begin(), values.end(), [](float v) { return v >= 0; });
}
} /* namespace */

bool normalizeTmc11LtmInput(const std::array<float, 65> &in,
			   std::array<float, 65> *output)
{
	if (!output || !nonnegative(in) || in[64] != 4095 ||
	    std::any_of(in.begin(), in.end(), [](float v) { return v > 4095; }))
		return false;
	std::array<float, 65> result;
	for (unsigned i = 0; i < 64; ++i)
		result[i] = (in[i] + 1) / 4095.0f;
	/* The target clips only node63; node64 is its fixed initialized endpoint. */
	result[63] = std::min(result[63], 1.0f);
	result[64] = 1;
	*output = result;
	return true;
}

bool sampleTmc11Pchip(const Tmc11PchipCurve &curve,
		     const std::array<float, 65> &in,
		     Tmc11PchipResult *output)
{
	if (!output || !finite(curve.x) || !finite(curve.y) || !finite(curve.coefficient) ||
	    !nonnegative(in) || curve.x[1] <= 0)
		return false;
	float linear = curve.y[1] / curve.x[1];
	if (!std::isfinite(linear) || linear < 0)
		return false;
	Tmc11PchipResult result;
	for (unsigned i = 0; i < 65; ++i) {
		float y;
		if (in[i] <= curve.x[1]) {
			y = mul(in[i], linear);
		} else {
			unsigned section = in[i] <= curve.x[2] ? 0 : (in[i] <= curve.x[3] ? 3 : 6);
			unsigned knee = section / 3 + 1;
			float dx = in[i] - curve.x[knee];
			float inner = curve.coefficient[section + 1] + mul(dx, curve.coefficient[section + 2]);
			float middle = curve.coefficient[section] + mul(dx, inner);
			y = curve.y[knee] + mul(dx, middle);
		}
		y = std::clamp(y, 0.0f, 1.0f);
		float denominator = in[i] == 0 ? 1 : in[i];
		float value = y / denominator;
		/* The target checks the lower bound first, even when linear < 1.
		 * std::clamp requires ordered bounds and cannot express that case. */
		result.gain[i] = value <= 1 ? 1 : (value > linear ? linear : value);
	}
	result.gain[0] = result.gain[1];
	result.ltmMix = std::clamp(2 - linear, 0.0f, 1.0f);
	if (!finite(result.gain))
		return false;
	*output = result;
	return true;
}

bool applyTmc11LtmContrast(const Tmc11LtmContrast &p,
			  const std::array<float, 65> &in,
			  const std::array<float, 65> &gain,
			  const std::array<float, 1024> &axis,
			  const std::array<float, 1024> &hist,
			  std::array<float, 65> *output)
{
	std::array<float, 3> controls = {p.percentage, p.bright, p.dark};
	if (!output || !nonnegative(in) || !nonnegative(gain) || !finite(axis) || !finite(hist) ||
	    !finite(controls) || std::any_of(controls.begin(), controls.end(), [](float v) { return v < 0 || v > 1; }) ||
	    axis[0] < 0 || axis[1023] > 1 ||
	    std::adjacent_find(axis.begin(), axis.end(), [](float a, float b) { return a >= b; }) != axis.end())
		return false;
	std::array<float, 65> result;
	unsigned hi = 1;
	for (unsigned i = 0; i < 65; ++i) {
		/* The retained target always reads the contrast curve, including when
		 * both blend strengths are zero. Preserve its advancing histogram index. */
		while (hi < 1024 && in[i] > axis[hi])
			++hi;
		float yHist = 1;
		if (hi < 1024) {
			float left = mul(axis[hi] - in[i], hist[hi - 1]);
			float right = mul(in[i] - axis[hi - 1], hist[hi]);
			yHist = (left + right) / (axis[hi] - axis[hi - 1]);
		}
		float y = mul(gain[i], in[i]);
		if (yHist > y)
			y = mul(y, 1 - p.bright) + mul(yHist, p.bright);
		else if (yHist < y)
			y = mul(y, 1 - p.dark) + mul(yHist, p.dark);
		y = std::clamp(y, 0.0f, 1.0f);
		float value = mul(std::pow(y / in[i], p.percentage), 1024);
		/* Unlike the pinned helper source, the actual target applies Q10/3-bit clipping. */
		result[i] = std::clamp(value, 0.0f, 8191.0f);
	}
	if (!finite(result))
		return false;
	*output = result;
	return true;
}
} /* namespace libcamera::ipa */
