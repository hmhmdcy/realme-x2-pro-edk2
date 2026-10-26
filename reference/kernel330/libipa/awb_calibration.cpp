/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "awb_calibration.h"

#include <algorithm>
#include <cmath>

namespace libcamera::ipa {
namespace {
bool positive(float value)
{
	return std::isfinite(value) && value > 0.0f;
}

unsigned int illuminant(float kelvin)
{
	if (kelvin >= 6000.0f) return 2;
	if (kelvin >= 4500.0f) return 3;
	if (kelvin >= 4000.0f) return 4;
	if (kelvin >= 3425.0f) return 6;
	if (kelvin >= 2575.0f) return 7;
	return 8;
}
} /* namespace */

bool awbCalibrationFactors(const AwbCalibrationData &data,
			   AwbIlluminantRatios *factors)
{
	if (!factors || !data.count || data.count > data.golden.size())
		return false;

	AwbIlluminantRatios unit{}, golden{};
	std::array<bool, 10> present{};
	for (unsigned int i = 0; i < data.count; ++i) {
		if (!positive(data.colourTemperatures[i]))
			return false;
		for (unsigned int c = 0; c < 2; ++c)
			if (!positive(data.unit[i][c]) || !positive(data.golden[i][c]))
				return false;
		unsigned int index = illuminant(data.colourTemperatures[i]);
		unit[index] = data.unit[i];
		golden[index] = data.golden[i];
		present[index] = true;
	}

	const auto original = present;
	unsigned int first = std::find(present.begin(), present.end(), true) - present.begin();
	for (unsigned int i = first + 1; i < present.size(); ++i) {
		if (!present[i]) {
			unit[i] = unit[i - 1];
			golden[i] = golden[i - 1];
		}
	}
	for (unsigned int i = first; i; --i) {
		unit[i - 1] = unit[i];
		golden[i - 1] = golden[i];
	}

	/* CW and TL84 share the middle fluorescent slots when only one exists. */
	if (original[4]) {
		unit[5] = unit[4]; golden[5] = golden[4];
		if (!original[6]) {
			unit[6] = unit[4]; golden[6] = golden[4];
		}
	} else if (original[6]) {
		unit[4] = unit[5] = unit[6];
		golden[4] = golden[5] = golden[6];
	}
	if (original[7] && !original[8]) {
		unit[8] = unit[7]; golden[8] = golden[7];
	} else if (!original[7] && original[8]) {
		unit[7] = unit[8]; golden[7] = golden[8];
	}
	if (!original[4] && !original[6] && data.count == 2) {
		for (unsigned int c = 0; c < 2; ++c) {
			float u = (unit[3][c] + unit[7][c]) * 0.5f;
			float g = (golden[3][c] + golden[7][c]) * 0.5f;
			for (unsigned int i : { 4u, 5u, 6u }) {
				unit[i][c] = u; golden[i][c] = g;
			}
		}
	}
	AwbIlluminantRatios result;
	for (unsigned int i = 0; i < result.size(); ++i) {
		for (unsigned int c = 0; c < 2; ++c) {
			result[i][c] = unit[i][c] / golden[i][c];
			if (!positive(result[i][c]))
				return false;
		}
	}
	*factors = result;
	return true;
}

bool awbCalibratedMwbRatios(const AwbIlluminantGains &gains,
			    const AwbIlluminantRatios &factors,
			    AwbIlluminantRatios *ratios)
{
	if (!ratios)
		return false;
	AwbIlluminantRatios result;
	for (unsigned int i = 0; i < gains.size(); ++i) {
		for (float gain : gains[i])
			if (!positive(gain))
				return false;
		for (unsigned int c = 0; c < 2; ++c) {
			if (!positive(factors[i][c]))
				return false;
			float ratio = gains[i][1] / gains[i][c ? 2 : 0];
			result[i][c] = ratio * factors[i][c];
			if (!positive(result[i][c]))
				return false;
		}
	}
	*ratios = result;
	return true;
}

bool awbRatiosForColourTemperature(const AwbIlluminantRatios &ratios,
				   float kelvin, AwbRatio *result)
{
	if (!result || !positive(kelvin))
		return false;
	for (const auto &point : ratios)
		if (!positive(point[0]) || !positive(point[1]))
			return false;
	static constexpr std::array<float, 8> temperatures{
		12000, 7500, 6500, 5000, 4000, 2850, 2300, 1500
	};
	static constexpr std::array<unsigned int, 8> points{ 0, 1, 2, 3, 5, 7, 8, 9 };
	if (kelvin >= temperatures.front()) {
		*result = ratios.front();
		return true;
	}
	for (unsigned int i = 1; i < temperatures.size(); ++i) {
		if (kelvin < temperatures[i])
			continue;
		float t = (kelvin - temperatures[i - 1]) /
			  (temperatures[i] - temperatures[i - 1]);
		float a = 1.0f - t, b = 1.0f - a;
		for (unsigned int c = 0; c < 2; ++c)
			(*result)[c] = ratios[points[i - 1]][c] * a + ratios[points[i]][c] * b;
		return true;
	}
	*result = ratios.back();
	return true;
}

} /* namespace libcamera::ipa */
