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

bool valid(const FloatingColourCorrectionData &data)
{
	for (float value : data.matrix)
		if (!std::isfinite(value) || value < -16 || value > 16) return false;
	/* Bound integer conversion in the shared original interpolation arithmetic.
	 * Quantization checks the target's narrower hardware range separately. */
	for (float value : data.offsets)
		if (!std::isfinite(value) || value < -65536 || value > 65536) return false;
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
	FloatingColourCorrectionData floating{ data.matrix, {} };
	for (unsigned int i = 0; i < data.offsets.size(); ++i)
		floating.offsets[i] = float(data.offsets[i]);
	QuantizedColourCorrection quantized;
	std::array<float, 9> effective;
	if (!quantizeColourCorrection(floating, qfactor, 11, &quantized, &effective))
		return false;
	ColourCorrectionParameters output;
	constexpr std::array<unsigned int, 3> order{ 1, 2, 0 };
	for (unsigned int i = 0; i < order.size(); ++i) {
		unsigned int row = order[i];
		output.a[i] = uint16_t(quantized.matrix[row * 3 + 1]) & 0xfff;
		output.b[i] = uint16_t(quantized.matrix[row * 3 + 2]) & 0xfff;
		output.c[i] = uint16_t(quantized.matrix[row * 3]) & 0xfff;
		output.k[i] = uint16_t(quantized.offsets[row]) & 0x7ff;
	}
	output.qfactor = qfactor;
	*result = output;
	if (effectiveMatrix) *effectiveMatrix = effective;
	return true;
}

bool interpolateFloatingColourCorrection(const FloatingColourCorrectionData &first,
					 const FloatingColourCorrectionData &second, float weight,
					 FloatingColourCorrectionData *result)
{
	if (!result || !valid(first) || !valid(second) || !std::isfinite(weight) || weight < 0 || weight > 1)
		return false;
	if (weight == 0) { *result = first; return true; }
	if (weight == 1) { *result = second; return true; }
	FloatingColourCorrectionData output;
	for (unsigned int i = 0; i < output.matrix.size(); ++i)
		output.matrix[i] = interpolateTuningFloat(first.matrix[i], second.matrix[i], weight);
	for (unsigned int i = 0; i < output.offsets.size(); ++i)
		output.offsets[i] = interpolateTuningFloat(first.offsets[i], second.offsets[i], weight);
	*result = output;
	return true;
}

bool quantizeColourCorrection(const FloatingColourCorrectionData &data,
			     unsigned int qfactor, unsigned int offsetBits,
			     QuantizedColourCorrection *result,
			     std::array<float, 9> *effectiveMatrix)
{
	if (!result || !valid(data) || qfactor > 3 || (offsetBits != 11 && offsetBits != 13))
		return false;
	const float scale = float(1u << (7 + qfactor));
	const long limit = 1l << (offsetBits - 1);
	QuantizedColourCorrection output;
	std::array<float, 9> effective;
	for (unsigned int i = 0; i < data.matrix.size(); ++i) {
		long value = std::lround(data.matrix[i] * scale);
		if (value < -2048 || value > 2047) return false;
		output.matrix[i] = int16_t(value);
		effective[i] = float(value) / scale;
	}
	for (unsigned int i = 0; i < data.offsets.size(); ++i) {
		long value = std::lround(data.offsets[i]);
		if (value < -limit || value >= limit) return false;
		output.offsets[i] = int16_t(value);
	}
	output.qfactor = qfactor;
	*result = output;
	if (effectiveMatrix) *effectiveMatrix = effective;
	return true;
}

} /* namespace libcamera::ipa */
