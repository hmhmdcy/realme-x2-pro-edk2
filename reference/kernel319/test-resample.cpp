/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/lsc_resample.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <limits>
using namespace libcamera::ipa;

int main()
{
	LscMesh mesh, output;
	for (unsigned int c = 0; c < LscChannels; ++c)
		for (unsigned int y = 0; y < LscHeight; ++y)
			for (unsigned int x = 0; x < LscWidth; ++x)
				mesh[c][y * LscWidth + x] = 2 + c * .2 + x * .03 + y * .02;
	LscGrid grid = { 100, 100, 0, 0, 0 };
	LscMapping mapping = { 1600, 1200, 0, 0, 1, 1 };
	assert(lscResample(mesh, grid, mapping, &output) && output == mesh);
	mapping = { 1600, 1200, 200, 100, .5, .5 };
	assert(lscResample(mesh, grid, mapping, &output));
	for (unsigned int c = 0; c < LscChannels; ++c)
		for (unsigned int y = 0; y < LscHeight; ++y)
			for (unsigned int x = 0; x < LscWidth; ++x) {
				double expected = 2 + c * .2 + (2 + x * .5) * .03 + (1 + y * .5) * .02;
				assert(std::abs(output[c][y * LscWidth + x] - expected) < 1e-6);
			}
	mapping = { 1600, 1200, 1600, 1200, -1, -1 };
	assert(lscResample(mesh, grid, mapping, &output));
	for (unsigned int c = 0; c < LscChannels; ++c)
		for (unsigned int p = 0; p < LscPoints; ++p)
			assert(output[c][p] == mesh[c][LscPoints - 1 - p]);
	for (auto size : { std::array<unsigned, 2>{4608,3456}, {4608,2592},
		{2304,1728}, {1928,1088}, {1632,1224}, {2104,1560} }) {
		assert(lscGridForSize(size[0], size[1], &grid));
		assert(grid.xStart + size[0] / 2 <= grid.cellWidth * 16U);
		assert(grid.yStart + size[1] / 2 <= grid.cellHeight * 12U);
	}
	auto saved = output;
	mapping.firstX = -100000;
	assert(!lscResample(mesh, grid, mapping, &output) && output == saved);
	mapping = { 1600, 1200, 0, 0, 1, 1 };
	mesh[LscB][220] = std::numeric_limits<float>::quiet_NaN();
	assert(!lscResample(mesh, grid, mapping, &output) && output == saved);
	assert(!lscGridForSize(1, 1, &grid));
	assert(!lscGridForSize(0xffffffffU, 1560, &grid));
	std::puts("LSC_RESAMPLE identity, affine crop, binning, flips, six modes and failure preservation passed");
}
