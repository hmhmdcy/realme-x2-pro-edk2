/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/ltm_curves.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <limits>
using namespace libcamera::ipa;
static_assert(sizeof(Ltm13CurveInput) == 456);
static_assert(sizeof(Ltm13Curves) == 396);
static_assert(sizeof(Ltm13SignedTables) == 384);
int main()
{
	Ltm13CurveInput input;
	Ltm13Curves untouched;
	Ltm13SignedTables tables;
	std::memset(&untouched, 0xa5, sizeof untouched);
	assert(!calculateLtm13Curves({}, nullptr));
	assert(!encodeLtm13SignedTables({}, nullptr));
	for (float bad : {std::numeric_limits<float>::quiet_NaN(),
			  std::numeric_limits<float>::infinity(),
			  -std::numeric_limits<float>::infinity(), 2097152.0f}) {
		for (unsigned int family = 0; family < 3; ++family) {
			Ltm13Curves curves{};
			if (!family)
				curves.scale[64] = bad;
			else if (family == 1)
				curves.lcePositive[16] = bad;
			else
				curves.lceNegative[16] = bad;
			std::memset(&tables, 0xa5, sizeof tables);
			auto saved = tables;
			assert(!encodeLtm13SignedTables(curves, &tables));
			assert(!std::memcmp(&tables, &saved, sizeof tables));
		}
	}
	for (float bad : {-32769.0f, 32768.0f}) {
		Ltm13Curves curves{};
		curves.scale[0] = bad;
		std::memset(&tables, 0xa5, sizeof tables);
		auto saved = tables;
		assert(!encodeLtm13SignedTables(curves, &tables));
		assert(!std::memcmp(&tables, &saved, sizeof tables));
	}
	while (std::fread(&input, sizeof input, 1, stdin) == 1) {
		auto saved = input;
		auto result = untouched;
		std::memset(&tables, 0xa5, sizeof tables);
		uint32_t ok = calculateLtm13Curves(input, &result);
		if (!ok)
			assert(!std::memcmp(&result, &untouched, sizeof result));
		auto previousTables = tables;
		uint32_t packed = ok && encodeLtm13SignedTables(result, &tables);
		if (!packed)
			assert(!std::memcmp(&tables, &previousTables, sizeof tables));
		assert(!std::memcmp(&input, &saved, sizeof input));
		assert(std::fwrite(&ok, 4, 1, stdout) == 1);
		assert(std::fwrite(&packed, 4, 1, stdout) == 1);
		assert(std::fwrite(&result, sizeof result, 1, stdout) == 1);
		assert(std::fwrite(&tables, sizeof tables, 1, stdout) == 1);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
