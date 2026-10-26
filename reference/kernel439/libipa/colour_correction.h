/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>

namespace libcamera::ipa {

struct ColourCorrectionData {
	std::array<float, 9> matrix; /* RGB, row-major, before gamma. */
	std::array<int32_t, 3> offsets;
};

/* CC13 keeps offsets floating point throughout its interpolation tree. */
struct FloatingColourCorrectionData {
	std::array<float, 9> matrix;
	std::array<float, 3> offsets;
};

/* Signed RGB, row-major. Register ordering belongs to the block encoder. */
struct QuantizedColourCorrection {
	std::array<int16_t, 9> matrix;
	std::array<int16_t, 3> offsets;
	uint32_t qfactor;
};

/* Common CAMSS block fields, output/input order G,B,R. Coefficients are
 * 12-bit two's complement. Titan175 offsets are 11-bit two's complement. */
struct ColourCorrectionParameters {
	std::array<uint16_t, 3> a, b, c, k;
	uint16_t qfactor;
};

bool interpolateColourCorrection(const ColourCorrectionData &first,
				 const ColourCorrectionData &second, float weight,
				 ColourCorrectionData *result);
bool encodeColourCorrection(const ColourCorrectionData &data, unsigned int qfactor,
			    ColourCorrectionParameters *result,
			    std::array<float, 9> *effectiveMatrix = nullptr);
bool interpolateFloatingColourCorrection(const FloatingColourCorrectionData &first,
					 const FloatingColourCorrectionData &second, float weight,
					 FloatingColourCorrectionData *result);
/* IFE offsets are signed 11-bit; IPE offsets are signed 13-bit. */
bool quantizeColourCorrection(const FloatingColourCorrectionData &data,
			     unsigned int qfactor, unsigned int offsetBits,
			     QuantizedColourCorrection *result,
			     std::array<float, 9> *effectiveMatrix = nullptr);

} /* namespace libcamera::ipa */
