/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/awb_colour_temperature.h"
#include <cstdio>
#include <cstdint>
#include <cstring>
using namespace libcamera::ipa;
int main(int argc, char **argv)
{
	if (argc != 3) return 2;
	FILE *input = std::fopen(argv[1], "rb"), *output = std::fopen(argv[2], "wb");
	if (!input || !output) return 3;
	AwbColourTemperatureModel model;
	uint32_t mode;
	while (std::fread(&mode, sizeof(mode), 1, input) == 1) {
		if (mode == 1) {
			AwbIlluminantRatios points, factors, expected, calibrated;
			if (std::fread(points.data(), sizeof(points), 1, input) != 1 ||
			    std::fread(factors.data(), sizeof(factors), 1, input) != 1 ||
			    std::fread(expected.data(), sizeof(expected), 1, input) != 1 ||
			    !awbCalibratedReferenceRatios(points, factors, &calibrated) ||
			    std::memcmp(calibrated.data(), expected.data(), sizeof(expected)) ||
			    !model.configure(calibrated)) return 4;
		} else if (mode == 2) {
			AwbRatio ratio;
			AwbColourTemperatureEstimate result;
			if (std::fread(ratio.data(), sizeof(ratio), 1, input) != 1 || !model.estimate(ratio, &result)) return 5;
			if (std::fwrite(&result.kelvin, sizeof(float), 1, output) != 1 ||
			    std::fwrite(&result.signedDistance, sizeof(float), 1, output) != 1 ||
			    std::fwrite(&result.illuminant, sizeof(uint32_t), 1, output) != 1) return 6;
		} else return 7;
	}
	std::fclose(input); return std::fclose(output) ? 8 : 0;
}
