/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc_runtime.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record { uint32_t present; TargetAdrcMetadata property, cache; };
static_assert(sizeof(Record) == 8476);
int main()
{
	Record input;
	while (std::fread(&input, sizeof(input), 1, stdin) == 1) {
		auto saved = input; auto output = input.cache;
		uint32_t status = input.present <= 1 && updateTargetAdrcMetadata(input.present ? &input.property : nullptr, &output);
		assert(!std::memcmp(&input, &saved, sizeof(input)));
		if (!status) assert(output == saved.cache);
		assert(std::fwrite(&status, 4, 1, stdout) == 1 && std::fwrite(output.data(), output.size(), 1, stdout) == 1);
	}
	TargetAdrcMetadata cache{}; auto saved = cache;
	assert(!updateTargetAdrcMetadata(&cache, &cache) && cache == saved);
	assert(!updateTargetAdrcMetadata(nullptr, nullptr));
	return std::ferror(stdin) || std::ferror(stdout);
}
