/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Copyright (C) 2026 Samurai Linux contributors */

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>

namespace libcamera {

/*
 * Experimental, native-size Quad Bayer interpolation, not a cell-collapse
 * filter. The caller must establish the active mode's physical CFA layout;
 * an ordinary Bayer fourcc alone does not provide that information.
 *
 * Input: CSI-2 RAW10, four samples per five bytes, 4x4 repeating CFA.
 * Output: one RGB10 triplet for EACH physical input pixel. The measured
 * channel is copied exactly; only the two absent channels are interpolated.
 * At an edge use the closest valid sample of the required colour, never a
 * reflected/clamped sample of a different colour. No image-quality claim is
 * made for this simple bilinear baseline (in particular colour aliasing).
 */
class NativeQuadBayer
{
public:
	struct Workspace {
		std::array<std::vector<uint16_t>, 5> rows;
		std::array<int64_t, 5> tags = { -1, -1, -1, -1, -1 };

		void reset(unsigned int width)
		{
			for (auto &row : rows)
				row.resize(width);
			tags.fill(-1);
		}
	};

	bool configure(unsigned int width, unsigned int height,
		       unsigned int stride, unsigned int redCellX,
		       unsigned int redCellY)
	{
		valid_ = false;
		if (width < 4 || height < 4 || width % 4 || height % 4 ||
		    redCellX > 1 || redCellY > 1 ||
		    width > std::numeric_limits<unsigned int>::max() / 5 ||
		    stride < width / 4 * 5 ||
		    height > std::numeric_limits<size_t>::max() / stride)
			return false;

		width_ = width;
		height_ = height;
		stride_ = stride;
		redCellX_ = redCellX;
		redCellY_ = redCellY;
		for (unsigned int cell = 0; cell < 2; cell++) {
			xAxes_[cell].resize(width);
			yAxes_[cell].resize(height);
			for (unsigned int x = 0; x < width; x++)
				xAxes_[cell][x] = axis(x, width, cell);
			for (unsigned int y = 0; y < height; y++)
				yAxes_[cell][y] = axis(y, height, cell);
		}
		valid_ = true;
		return true;
	}

	/* Sink: void(unsigned int x, unsigned int y, array<uint16_t, 3> rgb). */
	template<typename Sink>
	bool processRows(const uint8_t *input, size_t inputBytes,
			 unsigned int firstRow, unsigned int lastRow,
			 Workspace &work, Sink sink) const
	{
		if (!valid_ || !input || inputBytes < size_t(stride_) * height_ ||
		    firstRow > lastRow || lastRow > height_)
			return false;

		work.reset(width_);
		for (unsigned int y = firstRow; y < lastRow; y++) {
			const unsigned int begin = y > 1 ? y - 2 : 0;
			const unsigned int end = y < height_ - 2 ? y + 2 : height_ - 1;
			for (unsigned int row = begin; row <= end; row++) {
				const unsigned int slot = row % work.rows.size();
				if (work.tags[slot] == row)
					continue;
				unpack(input + size_t(row) * stride_, work.rows[slot]);
				work.tags[slot] = row;
			}

			auto sample = [&](unsigned int x, unsigned int row) -> uint16_t {
				return work.rows[row % work.rows.size()][x];
			};
			for (unsigned int x = 0; x < width_; x++) {
				std::array<uint16_t, 3> rgb;
				rgb[0] = interpolate(sample, xAxes_[redCellX_][x],
						     yAxes_[redCellY_][y]);
				rgb[2] = interpolate(sample, xAxes_[1 - redCellX_][x],
						     yAxes_[1 - redCellY_][y]);
				const unsigned int cellX = (x / 2) % 2;
				const unsigned int cellY = (y / 2) % 2;
				if ((cellX == redCellX_) != (cellY == redCellY_)) {
					rgb[1] = sample(x, y);
				} else {
					const Axis &horizontal = xAxes_[1 - cellX][x];
					const Axis &vertical = yAxes_[1 - cellY][y];
					const unsigned int h =
						sample(horizontal.lo, y) * horizontal.loWeight +
						sample(horizontal.hi, y) * horizontal.hiWeight;
					const unsigned int v =
						sample(x, vertical.lo) * vertical.loWeight +
						sample(x, vertical.hi) * vertical.hiWeight;
					const unsigned int divisor =
						2 * horizontal.divisor * vertical.divisor;
					rgb[1] = (h * vertical.divisor +
						  v * horizontal.divisor + divisor / 2) / divisor;
				}
				sink(x, y, rgb);
			}
		}
		return true;
	}

private:
	struct Axis {
		unsigned int lo;
		unsigned int hi;
		unsigned int loWeight;
		unsigned int hiWeight;
		unsigned int divisor;
	};

	static Axis axis(unsigned int coordinate, unsigned int extent, unsigned int cell)
	{
		if ((coordinate / 2) % 2 == cell)
			return { coordinate, coordinate, 1, 0, 1 };
		const int64_t lo = int64_t(coordinate & ~1U) - 1;
		const unsigned int hi = (coordinate & ~1U) + 2;
		if (lo < 0)
			return { hi, hi, 1, 0, 1 };
		if (hi >= extent)
			return { unsigned(lo), unsigned(lo), 1, 0, 1 };
		return { unsigned(lo), hi, hi - coordinate,
			 coordinate - unsigned(lo), hi - unsigned(lo) };
	}

	template<typename Sample>
	static uint16_t interpolate(Sample sample, const Axis &x, const Axis &y)
	{
		const unsigned int sum =
			sample(x.lo, y.lo) * x.loWeight * y.loWeight +
			sample(x.hi, y.lo) * x.hiWeight * y.loWeight +
			sample(x.lo, y.hi) * x.loWeight * y.hiWeight +
			sample(x.hi, y.hi) * x.hiWeight * y.hiWeight;
		const unsigned int divisor = x.divisor * y.divisor;
		return (sum + divisor / 2) / divisor;
	}

	static void unpack(const uint8_t *packed, std::vector<uint16_t> &row)
	{
		for (size_t x = 0; x < row.size(); x += 4, packed += 5) {
			const unsigned int low = packed[4];
			row[x] = (unsigned(packed[0]) << 2) | (low & 3);
			row[x + 1] = (unsigned(packed[1]) << 2) | ((low >> 2) & 3);
			row[x + 2] = (unsigned(packed[2]) << 2) | ((low >> 4) & 3);
			row[x + 3] = (unsigned(packed[3]) << 2) | (low >> 6);
		}
	}

	bool valid_ = false;
	unsigned int width_ = 0;
	unsigned int height_ = 0;
	unsigned int stride_ = 0;
	unsigned int redCellX_ = 0;
	unsigned int redCellY_ = 0;
	std::array<std::vector<Axis>, 2> xAxes_;
	std::array<std::vector<Axis>, 2> yAxes_;
};

} /* namespace libcamera */
