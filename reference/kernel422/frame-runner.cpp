/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/ltm13_frame.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record {
	uint32_t adrcPresent;
	Ltm13FrameInput input;
	Ltm13FaceSmoothingState history;
	Tmc11GenerationResult adrc;
	std::array<float, 1024> axis;
};
static_assert(sizeof(Record) == 14592);
int main()
{
	Record record;
	while (std::fread(&record, sizeof record, 1, stdin) == 1) {
		auto saved = record;
		Ltm13Program program; Ltm13FaceSmoothingState next;
		std::memset(&program, 0xa5, sizeof program); std::memset(&next, 0xa5, sizeof next);
		auto oldProgram = program; auto oldNext = next;
		uint32_t valid = record.adrcPresent <= 2 && prepareLtm13Frame(record.input, record.history,
			record.adrcPresent ? &record.adrc : nullptr, record.adrcPresent == 2 ? nullptr : &record.axis,
			&program, &next);
		assert(!std::memcmp(&record, &saved, sizeof record));
		if (!valid) assert(!std::memcmp(&program, &oldProgram, sizeof program) && !std::memcmp(&next, &oldNext, sizeof next));
		assert(std::fwrite(&valid, 4, 1, stdout) == 1 && std::fwrite(&program, sizeof program, 1, stdout) == 1 &&
		       std::fwrite(&next, sizeof next, 1, stdout) == 1);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
