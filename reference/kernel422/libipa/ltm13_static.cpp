/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ltm13_static.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace libcamera::ipa {
namespace {
bool integer(float input, int32_t *output, bool round)
{
	if (!std::isfinite(input)) return false;
	float value = round ? std::round(input) : std::trunc(input);
	if (double(value) < std::numeric_limits<int32_t>::min() ||
	    double(value) > std::numeric_limits<int32_t>::max()) return false;
	*output = int32_t(value); return true;
}
uint32_t segment(int32_t base, int32_t next)
{
	base = std::min(base, 4095); next = std::min(next, 4095);
	int64_t difference = int64_t(next) - base;
	uint32_t delta = uint32_t(difference) & 4095;
	if (difference < 0 || difference >= 32768) delta |= 2048;
	return (uint32_t(base) & 4095) | (delta << 12);
}
uint32_t contribution(uint32_t coefficient, uint32_t exponent)
{
	/* AArch64 variable shifts mask the count. Use unsigned arithmetic to
	 * preserve zero exponents without C++ negative-shift undefined behaviour. */
	return coefficient << ((exponent - 1) & 31);
}
} /* namespace */
bool prepareLtm13Static(const Ltm13StaticInput &in, Ltm13StaticResult *output)
{
	if (!output) return false;
	Ltm13StaticResult result{};
	for (unsigned i = 0; i < 4; ++i) {
		int32_t value;
		if (!integer(in.rgb2y[i] * 64, &value, true)) return false;
		result.rgb2y[i] = std::clamp(value, 0, i == 3 ? 64 : 63);
	}
	int32_t y;
	if (!integer(in.yRatioMaximum, &y, false)) return false;
	result.yRatioMaximum = std::clamp(y, 0, 1023);
	result.reverseGamma = bool(in.reverseGamma);
	result.localAdaptation = bool(in.localAdaptation);
	result.maskFilter = bool(in.maskFilter);
	result.dataCollection = bool(in.dataCollection);
	result.imageProcessing = bool(in.imageProcessing);
	for (unsigned i = 0; i < 24; ++i)
		if (in.weights[i] < 0 || in.weights[i] > 255) return false;
	for (unsigned i = 0; i < 12; ++i) {
		unsigned at = (i - i % 2) * 2 + 1 - i % 2;
		result.weights[i] = uint32_t(in.weights[at]) | (uint32_t(in.weights[at + 2]) << 8);
	}
	for (unsigned i = 0; i < 6; ++i)
		result.maskKernel[i] = std::clamp(in.maskKernel[i], i ? 0 : 1, int(6 - i));
	/* The retained target adds a fixed four for the sixth tap, even when
	 * its emitted exponent is zero. Follow actual instructions, rather than
	 * evaluating the reference source's undefined negative shift. */
	uint32_t sum = contribution(1, result.maskKernel[0]) +
		contribution(4, result.maskKernel[1]) + contribution(4, result.maskKernel[2]) +
		contribution(4, result.maskKernel[3]) + contribution(8, result.maskKernel[4]) + 4;
	sum &= 65535;
	if (!sum) return false;
	for (int shift = 16; shift >= 0; --shift) {
		uint32_t scale = ((1U << shift) / sum) & 65535;
		result.maskScale = std::min(scale, 4094U); result.maskShift = shift;
		if (scale < 4095) break;
	}
	result.lceThreshold = std::min(in.lceThreshold, 1023U);
	std::array<int32_t, 65> la;
	for (unsigned i = 0; i < 65; ++i) {
		if (!integer(in.laCurve[i], &la[i], true) || la[i] < 0 || in.maskCurve[i] < 0)
			return false;
	}
	for (unsigned i = 0; i < 64; ++i) {
		result.mask[i] = segment(in.maskCurve[i], in.maskCurve[i + 1]);
		result.la[i] = segment(la[i], la[i + 1]);
	}
	*output = result; return true;
}
} /* namespace libcamera::ipa */
