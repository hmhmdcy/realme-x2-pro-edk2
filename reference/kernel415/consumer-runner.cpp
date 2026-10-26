/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc_runtime.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
static_assert(sizeof(TmcLtmInput) == 28 && sizeof(TmcLtmDecision) == 12);
int main()
{
	TmcLtmInput input;
	while (std::fread(&input, sizeof(input), 1, stdin) == 1) {
		auto saved = input; TmcLtmDecision output; std::memset(&output, 0xa5, sizeof(output));
		uint32_t status = selectTargetTmcLtmSource(input, &output);
		assert(!std::memcmp(&input, &saved, sizeof(input)));
		if (!status) { unsigned char b[12]; std::memset(b, 0xa5, 12); assert(!std::memcmp(b, &output, 12)); }
		assert(std::fwrite(&status, 4, 1, stdout) == 1 && std::fwrite(&output, sizeof(output), 1, stdout) == 1);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
