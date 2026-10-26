/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/colour_correction.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
extern "C" {
#include "camss-icp-a5-colour.h"
}
using namespace libcamera::ipa;
static void invalid()
{
	FloatingColourCorrectionData a{ { 1, 0, 0, 0, 1, 0, 0, 0, 1 }, {} };
	QuantizedColourCorrection result, before;
	std::memset(&result, 0xa7, sizeof(result)); before = result;
	std::array<float, 9> effective; effective.fill(77);
	auto reject = [&](unsigned q, unsigned bits) {
		assert(!quantizeColourCorrection(a, q, bits, &result, &effective));
		assert(!std::memcmp(&result, &before, sizeof(result)));
		for (float v : effective) assert(v == 77);
	};
	reject(4, 13); reject(0, 12);
	for (float value : { -4096.5f, 4095.5f, std::numeric_limits<float>::infinity(),
			     std::numeric_limits<float>::quiet_NaN() }) {
		a.offsets[0] = value; reject(0, 13);
	}
	a.offsets[0] = 1024; reject(0, 11);
	assert(quantizeColourCorrection(a, 0, 13, &result));
	a.offsets[0] = -1025; assert(!quantizeColourCorrection(a, 0, 11, &result));
	assert(quantizeColourCorrection(a, 0, 13, &result));
	a.offsets[0] = 0;
	std::memset(&result, 0xa7, sizeof(result)); before = result;
	for (float value : { -16.01f, 16.0f, std::numeric_limits<float>::infinity(),
			     std::numeric_limits<float>::quiet_NaN() }) {
		a.matrix[0] = value; reject(0, 13);
	}
	a.matrix[0] = 1;
	FloatingColourCorrectionData output, old;
	std::memset(&output, 0xa7, sizeof(output)); old = output;
	for (float weight : { -0.1f, 1.1f, std::numeric_limits<float>::quiet_NaN() }) {
		assert(!interpolateFloatingColourCorrection(a, a, weight, &output));
		assert(!std::memcmp(&output, &old, sizeof(old)));
	}
	assert(!quantizeColourCorrection(a, 0, 13, nullptr));
	assert(!interpolateFloatingColourCorrection(a, a, .5, nullptr));
}
int main(int argc, char **argv)
{
	static_assert(sizeof(FloatingColourCorrectionData) == 48);
	static_assert(sizeof(QuantizedColourCorrection) == 28);
	static_assert(sizeof(camss_a5_ipe_cc) == 28);
	assert(argc == 3);
	FILE *input = std::fopen(argv[1], "rb"), *output = std::fopen(argv[2], "wb");
	assert(input && output);
	FloatingColourCorrectionData a, b, result;
	while (std::fread(&a, sizeof(a), 1, input) == 1) {
		float weight; uint32_t q;
		assert(std::fread(&b, sizeof(b), 1, input) == 1);
		assert(std::fread(&weight, 4, 1, input) == 1 && std::fread(&q, 4, 1, input) == 1);
		assert(interpolateFloatingColourCorrection(a, b, weight, &result));
		QuantizedColourCorrection quantized;
		std::array<float, 9> effective;
		assert(quantizeColourCorrection(result, q, 13, &quantized, &effective));
		camss_a5_ipe_cc packet;
		std::memcpy(&packet, &quantized, sizeof(packet));
		unsigned char command[44];
		assert(!camss_a5_ipe_cc_encode(command, sizeof(command), &packet));
		assert(std::fwrite(&result, sizeof(result), 1, output) == 1);
		assert(std::fwrite(&quantized, sizeof(quantized), 1, output) == 1);
		assert(std::fwrite(effective.data(), sizeof(effective), 1, output) == 1);
		assert(std::fwrite(command, sizeof(command), 1, output) == 1);
	}
	assert(std::feof(input)); std::fclose(input); assert(!std::fclose(output)); invalid();
}
