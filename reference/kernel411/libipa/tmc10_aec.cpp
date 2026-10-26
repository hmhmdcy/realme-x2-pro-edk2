/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "tmc10_aec.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>

namespace libcamera::ipa {
namespace {
bool interpolate(float a, float b, float ratio, float *output)
{
	/* Preserve the target's separate integer/fraction rounding. */
	if (double(a) < std::numeric_limits<int32_t>::min() ||
	    double(a) > std::numeric_limits<int32_t>::max() ||
	    double(b) < std::numeric_limits<int32_t>::min() ||
	    double(b) > std::numeric_limits<int32_t>::max())
		return false;
	int32_t ai = int32_t(a), bi = int32_t(b);
	int64_t difference = int64_t(bi) - ai;
	if (difference < std::numeric_limits<int32_t>::min() ||
	    difference > std::numeric_limits<int32_t>::max())
		return false;
	double af = double(a - float(ai)) * 1000000.0;
	double bf = double(b - float(bi)) * 1000000.0;
	volatile double fractionalStep = double(ratio) * (bf - af);
	float fraction = float(af + fractionalStep) / 1000000.0f;
	volatile double integerStep = double(ratio) * float(difference);
	float integer = float(double(ai) + integerStep);
	*output = fraction + integer;
	return std::isfinite(*output);
}
} /* namespace */

bool interpolateTmc10Aec(const Tmc10AecRegion *regions, uint32_t count,
			Tmc10AecControl control, float luxIndex, float realGain,
			Tmc10AecResult *output)
{
	if (!regions || !count || !output || !std::isfinite(luxIndex) || !std::isfinite(realGain) ||
	    (control != Tmc10AecControl::LuxIndex && control != Tmc10AecControl::RealGain))
		return false;
	unsigned int axis = control == Tmc10AecControl::LuxIndex ? 0 : 2;
	for (uint32_t i = 0; i < count; ++i) {
		const auto &r = regions[i];
		if (!std::all_of(r.trigger.begin(), r.trigger.end(), [](float v) { return std::isfinite(v); }) ||
		    !std::all_of(r.data.begin(), r.data.end(), [](float v) { return std::isfinite(v); }) ||
		    r.trigger[axis] > r.trigger[axis + 1])
			return false;
	}
	float trigger = axis ? realGain : luxIndex;
	Tmc10AecResult result{};
	result.startIndex = result.endIndex = count - 1;
	for (uint32_t i = 0; i < count; ++i) {
		if (trigger <= regions[i].trigger[axis + 1]) {
			result.startIndex = result.endIndex = i;
			break;
		}
		if (i + 1 < count && trigger < regions[i + 1].trigger[axis]) {
			result.startIndex = i;
			result.endIndex = i + 1;
			double left = regions[i].trigger[axis + 1];
			double right = regions[i + 1].trigger[axis];
			result.ratio = float((double(trigger) - left) / (right - left));
			break;
		}
	}
	result.data = regions[result.startIndex].data;
	if (result.startIndex != result.endIndex && result.ratio >= 1) {
		result.data = regions[result.endIndex].data;
	} else if (result.startIndex != result.endIndex && result.ratio > 0) {
		for (unsigned int i = 0; i < result.data.size(); ++i)
			if (!interpolate(regions[result.startIndex].data[i], regions[result.endIndex].data[i],
					 result.ratio, &result.data[i]))
				return false;
	}
	*output = result;
	return true;
}
} /* namespace libcamera::ipa */
