/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc_input.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record { TmcAecExposurePair pair; uint32_t version, initial; };
static_assert(sizeof(Record) == 40 && sizeof(TmcHdrTriggers) == 12);
int main()
{
	Record input;
	while (std::fread(&input, sizeof(input), 1, stdin) == 1) {
		auto saved = input; TmcHdrTriggers output; std::memset(&output, 0xa5, sizeof(output));
		uint32_t status = calculateTargetTmcHdrTriggers(input.pair, &output);
		uint32_t version = bindTargetIpeTmcVersion(input.version, input.initial);
		assert(!std::memcmp(&input, &saved, sizeof(input)));
		if (!status) { unsigned char b[12]; std::memset(b, 0xa5, 12); assert(!std::memcmp(b, &output, 12)); }
		assert(std::fwrite(&status, 4, 1, stdout) == 1 && std::fwrite(&output, sizeof(output), 1, stdout) == 1);
		assert(std::fwrite(&version, 4, 1, stdout) == 1);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
