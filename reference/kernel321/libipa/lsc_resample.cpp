/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "lsc_resample.h"

#include <algorithm>
#include <cmath>

namespace libcamera::ipa {

static bool validGrid(const LscGrid &g)
{
	if (g.subdivision > 3)
		return false;
	unsigned int scale = 1U << g.subdivision;
	return g.cellWidth >= 18 && g.cellWidth <= 2048 &&
	       g.cellHeight >= 9 && g.cellHeight <= 1024 &&
	       !(g.cellWidth % scale) && !(g.cellHeight % scale) &&
	       g.cellWidth / scale >= 9 && g.cellHeight / scale >= 9 &&
	       g.xStart < (LscWidth - 1) * g.cellWidth &&
	       g.yStart < (LscHeight - 1) * g.cellHeight;
}

bool lscGridForSize(uint32_t width, uint32_t height, LscGrid *grid)
{
	/* A Bayer-quad mesh requires complete quads. Bounds are the hardware's
	 * largest grid span, checked before performing any dimension arithmetic.
	 */
	if (!grid || !width || !height || width % 2 || height % 2 ||
	    width > 2 * (LscWidth - 1) * 2048 ||
	    height > 2 * (LscHeight - 1) * 1024)
		return false;
	unsigned int qw = width / 2, qh = height / 2;
	for (int level = 3; level >= 0; --level) {
		unsigned int scale = 1U << level;
		unsigned int w = ((qw + 16 * scale - 1) / (16 * scale)) * scale;
		unsigned int h = ((qh + 12 * scale - 1) / (12 * scale)) * scale;
		unsigned int overX = w * 16 - qw, overY = h * 12 - qh;
		LscGrid candidate = { static_cast<uint16_t>(w), static_cast<uint16_t>(h),
			static_cast<uint16_t>((overX + 1) / 2),
			static_cast<uint16_t>((overY + 1) / 2), static_cast<uint8_t>(level) };
		if (!validGrid(candidate))
			continue;
		/* Prefer a complete first interpolation segment. This is the
		 * source algorithm's placement policy, beyond UAPI validation.
		 */
		if (overX >= w || overY >= h || w - candidate.xStart < 18 ||
		    w / scale - candidate.xStart % (w / scale) < 9)
			continue;
		*grid = candidate;
		return true;
	}
	return false;
}

/* One border cell with the same edge slope. At a corner continue the
 * diagonal slope; this is the source LSC34 boundary convention.
 */
static double extended(const std::array<float, LscPoints> &m, int x, int y)
{
	int bx = std::clamp(x, 0, 16), by = std::clamp(y, 0, 12);
	double edge = m[by * LscWidth + bx];
	if (bx == x && by == y)
		return edge;
	int nx = bx + (x < 0 ? 1 : x > 16 ? -1 : 0);
	int ny = by + (y < 0 ? 1 : y > 12 ? -1 : 0);
	return 2 * edge - m[ny * LscWidth + nx];
}

static std::array<double, 4> cubicWeights(double t)
{
	double t2 = t * t, t3 = t2 * t;
	return { (-t3 + 2 * t2 - t) / 2,
		 (3 * t3 - 5 * t2 + 2) / 2,
		 (-3 * t3 + 4 * t2 + t) / 2,
		 (t3 - t2) / 2 };
}

static double sample(const std::array<float, LscPoints> &m,
		     double x, double y, bool outer)
{
	int ix = std::min(static_cast<int>(std::floor(x)), 16);
	int iy = std::min(static_cast<int>(std::floor(y)), 12);
	double tx = x - ix, ty = y - iy;
	if (outer || ix < 0 || iy < 0 || ix >= 16 || iy >= 12) {
		double a = extended(m, ix, iy) * (1 - tx) + extended(m, ix + 1, iy) * tx;
		double b = extended(m, ix, iy + 1) * (1 - tx) + extended(m, ix + 1, iy + 1) * tx;
		return a * (1 - ty) + b * ty;
	}
	auto wx = cubicWeights(tx), wy = cubicWeights(ty);
	double value = 0;
	for (int row = 0; row < 4; ++row)
		for (int col = 0; col < 4; ++col)
			value += extended(m, ix + col - 1, iy + row - 1) * wx[col] * wy[row];
	return value;
}

bool lscResample(const LscMesh &source, const LscGrid &grid,
		 const LscMapping &mapping, LscMesh *result)
{
	if (!result || !validGrid(grid) || !std::isfinite(mapping.sourceSpanX) ||
	    !std::isfinite(mapping.sourceSpanY) || mapping.sourceSpanX <= 0 ||
	    mapping.sourceSpanY <= 0 || !std::isfinite(mapping.firstX) ||
	    !std::isfinite(mapping.firstY) || !std::isfinite(mapping.stepX) ||
	    !std::isfinite(mapping.stepY) || !mapping.stepX || !mapping.stepY)
		return false;
	for (const auto &channel : source)
		for (float gain : channel)
			if (!std::isfinite(gain) || gain <= 0)
				return false;

	LscMesh output;
	for (unsigned int y = 0; y < LscHeight; ++y) {
		for (unsigned int x = 0; x < LscWidth; ++x) {
			double sx = (mapping.firstX + (static_cast<double>(x * grid.cellWidth) -
				grid.xStart) * mapping.stepX) / mapping.sourceSpanX * 16;
			double sy = (mapping.firstY + (static_cast<double>(y * grid.cellHeight) -
				grid.yStart) * mapping.stepY) / mapping.sourceSpanY * 12;
			/* The reference algorithm extends one mesh cell. Reject a
			 * mapping that would invent calibration farther outside it.
			 */
			if (!std::isfinite(sx) || !std::isfinite(sy) ||
			    sx < -1 || sx > 17 || sy < -1 || sy > 13)
				return false;
			bool outer = !x || !y || x == 16 || y == 12;
			for (unsigned int c = 0; c < LscChannels; ++c) {
				double value = sample(source[c], sx, sy, outer);
				output[c][y * LscWidth + x] = std::clamp(value, 1.0, 8191.0 / 1024);
			}
		}
	}
	*result = output;
	return true;
}

} /* namespace libcamera::ipa */
