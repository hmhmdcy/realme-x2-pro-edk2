/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gtm_tmc11.h"
#include <algorithm>
#include <cmath>

namespace libcamera::ipa {
namespace {
float mul(float a, float b)
{
	volatile float result = a * b;
	return result;
}
template<std::size_t N>
bool finite(const std::array<float, N> &values)
{
	return std::all_of(values.begin(), values.end(), [](float v) { return std::isfinite(v); });
}
} /* namespace */

bool calculateTmc11Gtm(const Tmc11PchipCurve &curve,
		      const Tmc11LtmContrast &p,
		      const std::array<float, 65> &in,
		      const std::array<uint32_t, 65> &domain,
		      const std::array<float, 1024> &axis,
		      const std::array<float, 1024> &hist,
		      bool swapWords,
		      std::array<uint64_t, 64> *output)
{
	std::array<float, 3> controls = {p.percentage, p.bright, p.dark};
	if (!output || !finite(in) || !finite(axis) || !finite(hist) || !finite(controls) ||
	    std::any_of(controls.begin(), controls.end(), [](float v) { return v < 0 || v > 1; }) ||
	    in[0] <= 0 || in[64] > 1 || domain[64] > 16383 ||
	    std::adjacent_find(in.begin(), in.end(), [](float a, float b) { return a > b; }) != in.end() ||
	    std::adjacent_find(domain.begin(), domain.end(), [](uint32_t a, uint32_t b) { return a >= b; }) != domain.end() ||
	    axis[0] < 0 || axis[1023] > 1 ||
	    std::adjacent_find(axis.begin(), axis.end(), [](float a, float b) { return a >= b; }) != axis.end())
		return false;
	Tmc11PchipResult sampled;
	if (!sampleTmc11Pchip(curve, in, &sampled))
		return false;
	std::array<int64_t, 65> base;
	unsigned hi = 1;
	for (unsigned i = 0; i < 65; ++i) {
		while (hi < 1024 && in[i] > axis[hi])
			++hi;
		float yHist = 1;
		if (hi < 1024) {
			float left = mul(axis[hi] - in[i], hist[hi - 1]);
			float right = mul(in[i] - axis[hi - 1], hist[hi]);
			yHist = (left + right) / (axis[hi] - axis[hi - 1]);
		}
		float y = mul(sampled.gain[i], in[i]);
		if (yHist > y)
			y = mul(y, 1 - p.bright) + mul(yHist, p.bright);
		else if (yHist < y)
			y = mul(y, 1 - p.dark) + mul(yHist, p.dark);
		y = std::clamp(y, 0.0f, 1.0f);
		float value = mul(std::pow(y / in[i], p.percentage), 4096);
		if (!std::isfinite(value))
			return false;
		base[i] = static_cast<int64_t>(std::round(std::clamp(value, 0.0f, 262143.0f)));
	}
	std::array<uint64_t, 64> result;
	for (unsigned i = 0; i < 64; ++i) {
		int64_t delta = domain[i + 1] - domain[i];
		int64_t scaled = (base[i + 1] - base[i]) * 256;
		int64_t slope = (scaled + (scaled < 0 ? -delta / 2 : delta / 2)) / delta;
		slope = std::clamp(slope, -(INT64_C(1) << 25), (INT64_C(1) << 25) - 1);
		uint64_t value = (static_cast<uint64_t>(base[i]) & 0x3ffff) |
				((static_cast<uint64_t>(slope) & 0x3ffffff) << 32);
		result[i] = swapWords ? (value << 32) | (value >> 32) : value;
	}
	*output = result;
	return true;
}
} /* namespace libcamera::ipa */
