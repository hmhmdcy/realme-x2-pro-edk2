/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "colour_correction.h"
#include "tuning_interpolation.h"
#include <cmath>

namespace libcamera::ipa {
namespace {
bool valid(const ColourCorrectionData &data)
{
	for (float value : data.matrix)
		if (!std::isfinite(value) || value < -16 || value > 16) return false;
	for (int32_t value : data.offsets)
		if (value < -4096 || value > 4095) return false;
	return true;
}

} /* namespace */

bool interpolateColourCorrection(const ColourCorrectionData &first,
				 const ColourCorrectionData &second, float weight,
				 ColourCorrectionData *result)
{
	if (!result || !valid(first) || !valid(second) || !std::isfinite(weight) || weight < 0 || weight > 1)
		return false;
	if (weight == 0) { *result = first; return true; }
	if (weight == 1) { *result = second; return true; }
	ColourCorrectionData output;
	for (unsigned int i = 0; i < output.matrix.size(); ++i)
		output.matrix[i] = interpolateTuningFloat(first.matrix[i], second.matrix[i], weight);
	for (unsigned int i = 0; i < output.offsets.size(); ++i)
		output.offsets[i] = int32_t(interpolateTuningFloat(float(first.offsets[i]), float(second.offsets[i]), weight));
	*result = output;
	return true;
}

bool encodeColourCorrection(const ColourCorrectionData &data, unsigned int qfactor,
			    ColourCorrectionParameters *result,
			    std::array<float, 9> *effectiveMatrix)
{
	if (!result || !valid(data) || qfactor > 3) return false;
	const float scale = float(1u << (7 + qfactor));
	std::array<uint16_t, 9> encoded;
	std::array<float, 9> effective;
	for (unsigned int i = 0; i < data.matrix.size(); ++i) {
		long value = std::lround(data.matrix[i] * scale);
		if (value < -2048 || value > 2047) return false;
		encoded[i] = uint16_t(value) & 0xfff;
		effective[i] = float(value) / scale;
	}
	ColourCorrectionParameters output;
	constexpr std::array<unsigned int, 3> order{ 1, 2, 0 };
	for (unsigned int i = 0; i < order.size(); ++i) {
		unsigned int row = order[i];
		output.a[i] = encoded[row * 3 + 1];
		output.b[i] = encoded[row * 3 + 2];
		output.c[i] = encoded[row * 3];
		if (data.offsets[row] < -1024 || data.offsets[row] > 1023) return false;
		output.k[i] = uint16_t(data.offsets[row]) & 0x7ff;
	}
	output.qfactor = qfactor;
	*result = output;
	if (effectiveMatrix) *effectiveMatrix = effective;
	return true;
}

} /* namespace libcamera::ipa */
