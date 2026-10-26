/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* RAW green-channel focus statistics shared by the software ISP and its IPA. */
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <limits>
#include <optional>
#include <vector>

namespace libcamera {

struct FocusRegion {
	uint64_t energy = 0;
	uint64_t sum = 0;
	uint32_t samples = 0;
};

struct FocusStatistics {
	static constexpr unsigned int kColumns = 4;
	static constexpr unsigned int kRows = 3;
	bool valid = false;
	std::array<FocusRegion, kColumns * kRows> regions{};

	std::optional<int32_t> figureOfMerit() const
	{
		if (!valid)
			return std::nullopt;

		std::vector<double> scores;
		for (const FocusRegion &region : regions) {
			if (!region.samples || !region.sum)
				continue;
			/* Brightness normalization is not a substitute for locking AE. */
			double mean = double(region.sum) / region.samples;
			scores.push_back(double(region.energy) / region.samples / (mean * mean));
		}
		if (scores.empty())
			return std::nullopt;

		/* Flat regions should not dominate a scene with useful edges. */
		std::sort(scores.begin(), scores.end(), std::greater<double>());
		unsigned int count = std::min<size_t>(4, scores.size());
		double score = 0;
		for (unsigned int i = 0; i < count; ++i)
			score += scores[i];
		score *= 1000000.0 / count;
		return static_cast<int32_t>(std::min(std::round(score),
						   double(std::numeric_limits<int32_t>::max())));
	}
};

struct FocusBayerFormat {
	unsigned int bits;
	bool packed;
	/* True for GBRG/GRBG; false for BGGR/RGGB. */
	bool greenFirst;
	bool quad;
};

/*
 * Read packed CSI-2 RAW10/12 or little-endian unpacked RAW8/10/12. Check the
 * complete input layout and ROI before reading. Sampling and storage are
 * bounded independently of resolution; every sample averages a 4x4 RAW area.
 * The two green phases are combined before spatial filtering, avoiding red /
 * blue pattern edges. This also handles native 4x4 quad-cell patterns.
 */
inline FocusStatistics measureBayerFocus(const uint8_t *data, size_t bytes,
					unsigned int width, unsigned int height,
					unsigned int stride, unsigned int left,
					unsigned int top, unsigned int roiWidth,
					unsigned int roiHeight, const FocusBayerFormat &format)
{
	FocusStatistics result;
	if (!data || !width || !height || !stride ||
	    (format.bits != 8 && format.bits != 10 && format.bits != 12) ||
	    (format.packed && format.bits == 8) ||
	    left > width || top > height || roiWidth > width - left ||
	    roiHeight > height - top)
		return result;

	unsigned int groupPixels = format.bits == 10 ? 4 : 2;
	if (format.packed && width % groupPixels)
		return result;
	uint64_t rowBytes = format.packed ? uint64_t(width) * format.bits / 8
					 : uint64_t(width) * (format.bits == 8 ? 1 : 2);
	if (stride < rowBytes || uint64_t(height - 1) * stride + rowBytes > bytes)
		return result;

	unsigned int columns = std::min(320U, roiWidth / 4);
	unsigned int rows = std::min(240U, roiHeight / 4);
	if (columns < 5 || rows < 5)
		return result;

	auto pixel = [&](unsigned int x, unsigned int y) -> uint16_t {
		const uint8_t *line = data + size_t(y) * stride;
		unsigned int value;
		if (!format.packed) {
			value = format.bits == 8 ? line[x] : line[2 * size_t(x)] |
								 (unsigned(line[2 * size_t(x) + 1]) << 8);
		} else if (format.bits == 10) {
			size_t group = size_t(x / 4) * 5;
			unsigned int lane = x % 4;
			value = (unsigned(line[group + lane]) << 2) |
				((line[group + 4] >> (2 * lane)) & 3);
		} else {
			size_t group = size_t(x / 2) * 3;
			unsigned int lane = x % 2;
			value = (unsigned(line[group + lane]) << 4) |
				((line[group + 2] >> (4 * lane)) & 15);
		}
		value = std::min(value, (1U << format.bits) - 1);
		return value << (16 - format.bits);
	};

	std::vector<uint16_t> grid(size_t(columns) * rows);
	for (unsigned int y = 0; y < rows; ++y) {
		unsigned int py = top + uint64_t(y) * (roiHeight - 4) / (rows - 1);
		for (unsigned int x = 0; x < columns; ++x) {
			unsigned int px = left + uint64_t(x) * (roiWidth - 4) / (columns - 1);
			uint32_t sum = 0;
			unsigned int count = 0;
			for (unsigned int j = 0; j < 4; ++j) {
				for (unsigned int i = 0; i < 4; ++i) {
					unsigned int cx = format.quad ? (px + i) / 2 : px + i;
					unsigned int cy = format.quad ? (py + j) / 2 : py + j;
					if (bool((cx ^ cy) & 1) != format.greenFirst) {
						sum += pixel(px + i, py + j);
						++count;
					}
				}
			}
			grid[size_t(y) * columns + x] = sum / count;
		}
	}

	std::vector<uint16_t> smooth(grid.size());
	for (unsigned int y = 1; y + 1 < rows; ++y) {
		for (unsigned int x = 1; x + 1 < columns; ++x) {
			uint32_t sum = 0;
			for (unsigned int j = y - 1; j <= y + 1; ++j)
				for (unsigned int i = x - 1; i <= x + 1; ++i)
					sum += grid[size_t(j) * columns + i];
			smooth[size_t(y) * columns + x] = sum / 9;
		}
	}

	for (unsigned int y = 2; y + 2 < rows; ++y) {
		for (unsigned int x = 2; x + 2 < columns; ++x) {
			uint16_t mean = smooth[size_t(y) * columns + x];
			/* No useful contrast information in black or clipped samples. */
			if (mean < 1024 || mean > 64512)
				continue;
			int64_t dx = int64_t(smooth[size_t(y) * columns + x + 1]) -
				     smooth[size_t(y) * columns + x - 1];
			int64_t dy = int64_t(smooth[size_t(y + 1) * columns + x]) -
				     smooth[size_t(y - 1) * columns + x];
			unsigned int column = x * FocusStatistics::kColumns / columns;
			unsigned int row = y * FocusStatistics::kRows / rows;
			FocusRegion &region = result.regions[row * FocusStatistics::kColumns + column];
			region.energy += dx * dx + dy * dy;
			region.sum += mean;
			++region.samples;
		}
	}
	result.valid = true;
	return result;
}

} /* namespace libcamera */
