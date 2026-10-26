/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/ltm13_static.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
int main()
{
	static_assert(sizeof(Ltm13StaticInput) == 684 && sizeof(Ltm13StaticResult) == 636);
	assert(!prepareLtm13Static({}, nullptr));
	Ltm13StaticInput input;
	while (std::fread(&input, sizeof input, 1, stdin) == 1) {
		auto saved = input;
		Ltm13StaticResult output;
		std::memset(&output, 0xa5, sizeof output); auto before = output;
		uint32_t valid = prepareLtm13Static(input, &output);
		assert(!std::memcmp(&input, &saved, sizeof input));
		if (!valid) assert(!std::memcmp(&output, &before, sizeof output));
		assert(std::fwrite(&valid, 4, 1, stdout) == 1 && std::fwrite(&output, sizeof output, 1, stdout) == 1);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
