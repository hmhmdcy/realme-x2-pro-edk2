/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/gtm_tmc11.h"
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record {
	Tmc11PchipCurve curve;
	Tmc11LtmContrast controls;
	std::array<float, 65> normalized;
	std::array<uint32_t, 65> domain;
	std::array<float, 1024> axis, histogram;
	uint32_t swap;
};
static_assert(sizeof(Record) == 8804);
int main()
{
	Record input;
	while (fread(&input, sizeof input, 1, stdin) == 1) {
		std::array<uint64_t, 64> result;
		memset(result.data(), 0xa7, sizeof result);
		uint32_t ok = calculateTmc11Gtm(input.curve, input.controls, input.normalized,
					      input.domain, input.axis, input.histogram,
					      input.swap, &result);
		if (fwrite(&ok, sizeof ok, 1, stdout) != 1 || fwrite(result.data(), sizeof result, 1, stdout) != 1)
			return 2;
	}
	return ferror(stdin) || ferror(stdout);
}
