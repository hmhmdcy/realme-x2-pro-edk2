/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <cstdio>
#include <cstdint>
#include "libipa/awb_calibration.h"
using namespace libcamera::ipa;
int main(int argc, char **argv)
{
	if (argc != 3) return 2;
	FILE *in = std::fopen(argv[1], "rb"), *out = std::fopen(argv[2], "wb");
	if (!in || !out) return 3;
	uint32_t kind;
	while (std::fread(&kind, sizeof(kind), 1, in) == 1) {
		if (kind == 1) {
			AwbCalibrationData data{}; AwbIlluminantRatios factors{};
			if (std::fread(&data.count, 4, 1, in) != 1 ||
			    std::fread(data.colourTemperatures.data(), 4, 6, in) != 6 ||
			    std::fread(data.golden.data(), 4, 12, in) != 12 ||
			    std::fread(data.unit.data(), 4, 12, in) != 12) return 4;
			if (!awbCalibrationFactors(data, &factors)) return 5;
			if (std::fwrite(factors.data(), 4, 20, out) != 20) return 6;
		} else if (kind == 2) {
			AwbIlluminantRatios ratios{}; AwbRatio result{}; float kelvin;
			if (std::fread(ratios.data(), 4, 20, in) != 20 || std::fread(&kelvin, 4, 1, in) != 1) return 7;
			if (!awbRatiosForColourTemperature(ratios, kelvin, &result)) return 8;
			if (std::fwrite(result.data(), 4, 2, out) != 2) return 9;
		} else if (kind == 3) {
			AwbIlluminantGains gains{}; AwbIlluminantRatios factors{}, ratios{};
			if (std::fread(gains.data(), 4, 30, in) != 30 || std::fread(factors.data(), 4, 20, in) != 20) return 11;
			if (!awbCalibratedMwbRatios(gains, factors, &ratios)) return 12;
			if (std::fwrite(ratios.data(), 4, 20, out) != 20) return 13;
		} else return 10;
	}
	int result = std::ferror(in) || std::ferror(out);
	std::fclose(in); std::fclose(out);
	return result;
}
