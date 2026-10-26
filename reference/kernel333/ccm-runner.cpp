/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/colour_correction.h"
#include <cstdio>
#include <cstdint>
using namespace libcamera::ipa;
int main(int argc, char **argv)
{
	if (argc != 3) return 2;
	FILE *input = std::fopen(argv[1], "rb"), *output = std::fopen(argv[2], "wb");
	if (!input || !output) return 3;
	uint32_t mode;
	while (std::fread(&mode, sizeof(mode), 1, input) == 1) {
		uint32_t qfactor; float weight;
		ColourCorrectionData a, b;
		if (std::fread(&qfactor, sizeof(qfactor), 1, input) != 1 ||
		    std::fread(&a, sizeof(a), 1, input) != 1) return 4;
		if (mode == 2) {
			if (std::fread(&b, sizeof(b), 1, input) != 1 ||
			    std::fread(&weight, sizeof(weight), 1, input) != 1 ||
			    !interpolateColourCorrection(a, b, weight, &a) ||
			    std::fwrite(&a, sizeof(a), 1, output) != 1) return 5;
		} else if (mode != 1) return 6;
		ColourCorrectionParameters result;
		if (!encodeColourCorrection(a, qfactor, &result)) return 7;
		for (unsigned int i = 0; i < 3; ++i) {
			uint16_t row[] = { result.a[i], result.b[i], result.c[i] };
			if (std::fwrite(row, sizeof(row), 1, output) != 1) return 8;
		}
		if (std::fwrite(result.k.data(), sizeof(result.k), 1, output) != 1 ||
		    std::fwrite(&result.qfactor, sizeof(result.qfactor), 1, output) != 1) return 9;
	}
	std::fclose(input); return std::fclose(output) ? 10 : 0;
}
