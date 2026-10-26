/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "aec_antibanding.h"

#include <cstdint>
#include <cstdio>

using namespace libcamera::ipa;

template<typename T> bool read(FILE *file, T *value)
{
	return std::fread(value, sizeof(*value), 1, file) == 1;
}

template<typename T> bool write(FILE *file, T value)
{
	return std::fwrite(&value, sizeof(value), 1, file) == 1;
}

int main(int argc, char **argv)
{
	if (argc != 3)
		return 2;
	FILE *input = std::fopen(argv[1], "rb"), *output = std::fopen(argv[2], "wb");
	if (!input || !output)
		return 3;
	uint32_t count;
	if (!read(input, &count))
		return 4;
	for (uint32_t i = 0; i < count; ++i) {
		AecAntibandingConfiguration configuration{};
		AecExposureAllocation exposure{}, result{123, 456, 789};
		uint32_t enabled, method;
		if (!read(input, &enabled) || !read(input, &configuration.periodNs) ||
		    !read(input, &configuration.minimumPeriodFraction) ||
		    !read(input, &configuration.minimumGain) ||
		    !read(input, &configuration.minimumExposureTimeNs) ||
		    !read(input, &configuration.maximumExposureTimeNs) ||
		    !read(input, &configuration.minimumPreviewVerticalBlankingNs) ||
		    !read(input, &method) || !read(input, &exposure.gain) ||
		    !read(input, &exposure.exposureTimeNs) || !read(input, &exposure.index))
			return 5;
		configuration.enabled = enabled;
		configuration.fpsMethod = static_cast<AecAntibandingFpsMethod>(method);
		bool valid = aecApplyAntibanding(configuration, exposure, &result);
		if (!valid) {
			if (result.gain != 123 || result.exposureTimeNs != 456 || result.index != 789)
				return 6;
			result = {};
		}
		if (!write(output, uint32_t(valid)) || !write(output, result.gain) ||
		    !write(output, result.exposureTimeNs) || !write(output, result.index))
			return 7;
	}
	if (std::fgetc(input) != EOF)
		return 8;
	std::fclose(input);
	return std::fclose(output) ? 9 : 0;
}
