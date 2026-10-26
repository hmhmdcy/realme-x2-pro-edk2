/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/ltm_adrc.h"
#include "../kernel407/libipa/ltm_curves.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
static_assert(sizeof(Ltm13AdrcBlend) == 392);
int main()
{
	assert(!encodeLtm13AdrcTables({}, nullptr));
	Ltm13AdrcBlend input;
	while (std::fread(&input, sizeof input, 1, stdin) == 1) {
		Ltm13AdrcBlend saved;
		std::memcpy(&saved, &input, sizeof input);
		Ltm13Curves curves{};
		for (unsigned int i = 0; i < 65; ++i)
			curves.scale[i] = float(input.scale[i]);
		Ltm13SignedTables legacy{};
		uint32_t oldOk = encodeLtm13SignedTables(curves, &legacy);
		Ltm13AdrcTables tables;
		std::memset(&tables, 0xa5, sizeof tables);
		auto before = tables;
		uint32_t ok = encodeLtm13AdrcTables(input, &tables);
		if (!ok)
			assert(!std::memcmp(&before, &tables, sizeof tables));
		assert(!std::memcmp(&input, &saved, sizeof input));
		assert(std::fwrite(&oldOk, 4, 1, stdout) == 1);
		assert(std::fwrite(legacy.scale.data(), 4, 64, stdout) == 64);
		assert(std::fwrite(&ok, 4, 1, stdout) == 1);
		assert(std::fwrite(&tables, sizeof tables, 1, stdout) == 1);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
