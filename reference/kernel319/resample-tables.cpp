/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/lsc_resample.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
using namespace libcamera::ipa;

int main(int argc, char **argv)
{
	if (argc != 11)
		return 2;
	unsigned int size[2];
	for (unsigned int i = 0; i < 2; ++i) {
		char *end;
		unsigned long value = std::strtoul(argv[3 + i], &end, 10);
		if (*end || !value || value > std::numeric_limits<uint32_t>::max())
			return 2;
		size[i] = value;
	}
	LscMapping mapping;
	double *fields[] = { &mapping.sourceSpanX, &mapping.sourceSpanY,
		&mapping.firstX, &mapping.firstY, &mapping.stepX, &mapping.stepY };
	for (unsigned int i = 0; i < 6; ++i) {
		char *end;
		*fields[i] = std::strtod(argv[5 + i], &end);
		if (*end)
			return 2;
	}
	LscGrid grid;
	if (!lscGridForSize(size[0], size[1], &grid))
		return 3;
	FILE *in = std::fopen(argv[1], "rb"), *out = std::fopen(argv[2], "wb");
	if (!in || !out)
		return 4;
	LscMesh input, result;
	LscPackedMesh packed;
	unsigned int count = 0;
	for (;;) {
		size_t n = std::fread(&input, 1, sizeof(input), in);
		if (!n && !std::ferror(in))
			break;
		if (n != sizeof(input) || !lscResample(input, grid, mapping, &result) ||
		    !lscPackTitan17x(result, &packed) ||
		    std::fwrite(&result, 1, sizeof(result), out) != sizeof(result) ||
		    std::fwrite(&packed, 1, sizeof(packed), out) != sizeof(packed))
			return 5;
		count++;
	}
	if (std::fclose(in) || std::fclose(out))
		return 6;
	std::printf("RESAMPLED tables=%u cell=%ux%u start=%u,%u subdivision=%u\n",
		count, grid.cellWidth, grid.cellHeight, grid.xStart, grid.yStart, grid.subdivision);
}
