/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc_runtime.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
static_assert(sizeof(Tmc11PolicyInput) == 88 && sizeof(Tmc11PolicyResult) == 56);
int main()
{
	Tmc11PolicyInput input;
	while (std::fread(&input, sizeof(input), 1, stdin) == 1) {
		auto saved = input; Tmc11PolicyResult output; std::memset(&output, 0xa5, sizeof(output));
		uint32_t status = evaluateTmc11Policy(input, &output);
		assert(!std::memcmp(&input, &saved, sizeof(input)));
		if (!status) {
			unsigned char bytes[sizeof(output)]; std::memset(bytes, 0xa5, sizeof(bytes));
			assert(!std::memcmp(bytes, &output, sizeof(output)));
		}
		assert(std::fwrite(&status, 4, 1, stdout) == 1 && std::fwrite(&output, sizeof(output), 1, stdout) == 1);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
