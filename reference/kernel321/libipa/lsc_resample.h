/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include "lens_shading.h"

namespace libcamera::ipa {

struct LscGrid {
	uint16_t cellWidth, cellHeight;
	uint16_t xStart, yStart;
	uint8_t subdivision;
};

/* Coordinates use the source calibration's Bayer-channel sample lattice.
 * sourceSpanX/Y are the distances between its first and last mesh nodes.
 * (firstX,firstY) is the source coordinate of the input frame's first quad;
 * stepX/Y map adjacent input quads to source coordinates. Negative steps
 * express sensor flips. The caller must establish the actual mode mapping;
 * an output size alone cannot identify binning, cropping or sample centres.
 */
struct LscMapping {
	double sourceSpanX, sourceSpanY;
	double firstX, firstY;
	double stepX, stepY;
};

bool lscGridForSize(uint32_t width, uint32_t height, LscGrid *grid);
bool lscResample(const LscMesh &source, const LscGrid &grid,
		 const LscMapping &mapping, LscMesh *result);

} /* namespace libcamera::ipa */
