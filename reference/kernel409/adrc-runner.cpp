/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/ltm_adrc.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record {
	Ltm13AdrcSamples input;
	float mix;
	std::array<int32_t, 65> curve;
	std::array<int16_t, 65> scale;
};
static_assert(sizeof(Record) == 1176);
static_assert(sizeof(Ltm13AdrcCurves) == 520);
int main()
{
	assert(!calculateLtm13Adrc({}, nullptr));
	Record record;
	while (std::fread(&record, sizeof record, 1, stdin) == 1) {
		auto saved = record;
		Ltm13AdrcCurves generated, before;
		Ltm13AdrcBlend blended;
		std::memset(&generated, 0xa5, sizeof generated);
		before = generated;
		std::memset(&blended, 0xa5, sizeof blended);
		auto oldBlend = blended;
		uint32_t ok = calculateLtm13Adrc(record.input, &generated);
		if (!ok)
			assert(!std::memcmp(&before, &generated, sizeof before));
		uint32_t mixed = ok && blendLtm13Adrc(generated, record.mix, record.curve, record.scale, &blended);
		if (!mixed)
			assert(!std::memcmp(&oldBlend, &blended, sizeof blended));
		assert(!std::memcmp(&saved, &record, sizeof record));
		assert(std::fwrite(&ok, 4, 1, stdout) == 1);
		assert(std::fwrite(&generated, sizeof generated, 1, stdout) == 1);
		assert(std::fwrite(&mixed, 4, 1, stdout) == 1);
		assert(std::fwrite(blended.curve.data(), 4, 65, stdout) == 65);
		assert(std::fwrite(blended.scale.data(), 2, 65, stdout) == 65);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
