/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/ltm_face_smoothing.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record {
	uint32_t mode;
	Ltm13CurveInput input;
	Ltm13FaceSmoothingControl control;
	Ltm13FaceSmoothingState state;
};
static_assert(sizeof(Record) == 876);
static_assert(sizeof(Ltm13FaceSmoothingState) == 404);
int main()
{
	Record record;
	while (std::fread(&record, sizeof record, 1, stdin) == 1) {
		auto saved = record;
		Ltm13Curves output, oldOutput;
		Ltm13FaceSmoothingState next, oldNext;
		Ltm13SignedTables tables, oldTables;
		std::memset(&output, 0xa5, sizeof output);
		std::memset(&next, 0xa5, sizeof next);
		std::memset(&tables, 0xa5, sizeof tables);
		oldOutput = output;
		oldNext = next;
		oldTables = tables;
		uint32_t ok = 0;
		if (record.mode == 1) {
			ok = calculateLtm13FaceCurves(record.input, record.control, record.state, &output, &next);
		} else if (record.mode == 0) {
			Ltm13Curves curves;
			std::memcpy(&curves, &record.input, sizeof curves);
			ok = applyLtm13FaceSmoothing(curves, record.control, record.state, &output, &next);
		}
		if (!ok)
			assert(!std::memcmp(&output, &oldOutput, sizeof output) && !std::memcmp(&next, &oldNext, sizeof next));
		uint32_t packed = ok && encodeLtm13SignedTables(output, &tables);
		if (!packed)
			assert(!std::memcmp(&tables, &oldTables, sizeof tables));
		assert(!std::memcmp(&record, &saved, sizeof record));
		assert(std::fwrite(&ok, 4, 1, stdout) == 1);
		assert(std::fwrite(&output, sizeof output, 1, stdout) == 1);
		assert(std::fwrite(&next, sizeof next, 1, stdout) == 1);
		assert(std::fwrite(&packed, 4, 1, stdout) == 1);
		assert(std::fwrite(&tables, sizeof tables, 1, stdout) == 1);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
