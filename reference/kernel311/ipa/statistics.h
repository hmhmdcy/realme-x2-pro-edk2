/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <array>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <span>
#include <vector>
#include <linux/qcom-camss-config.h>

namespace libcamera::ipa::camss {

struct GridStatistics {
	uint16_t left = 0, top = 0, width = 0, height = 0, columns = 0, rows = 0;
	uint16_t highThreshold = 0, inputBits = 0;
	std::vector<camss_stats_bg_region> regions;
};
struct ParsedStatistics {
	std::array<uint32_t, CAMSS_STATS_BHIST_BINS> histogram{};
	uint64_t population = 0, weightedSum = 0;
	GridStatistics grid;
};

/* Parse sized blocks, including legacy BHIST packets, without aligned loads. */
inline int parseStatistics(std::span<const uint8_t> data, uint32_t width,
			  uint32_t height, ParsedStatistics *result)
{
	if (!result || data.size() < sizeof(v4l2_isp_buffer))
		return -EINVAL;
	v4l2_isp_buffer envelope;
	std::memcpy(&envelope, data.data(), sizeof(envelope));
	if (envelope.version != V4L2_ISP_VERSION_V1 ||
	    envelope.data_size != data.size() - sizeof(envelope))
		return -EPROTO;
	ParsedStatistics parsed;
	bool histogramFound = false, gridFound = false;
	size_t offset = sizeof(envelope);
	while (offset < data.size()) {
		v4l2_isp_block_header header;
		if (data.size() - offset < sizeof(header))
			return -EPROTO;
		std::memcpy(&header, data.data() + offset, sizeof(header));
		if (header.size < sizeof(header) || header.size % 8 ||
		    header.size > data.size() - offset || header.flags)
			return -EPROTO;
		if (header.type == CAMSS_STATS_AEC_BHIST) {
			if (histogramFound || header.size != sizeof(camss_stats_bhist))
				return -EPROTO;
			histogramFound = true;
			std::memcpy(parsed.histogram.data(), data.data() + offset + sizeof(header),
				    sizeof(parsed.histogram));
		} else if (header.type == CAMSS_STATS_AWB_BG) {
			if (gridFound || header.size < sizeof(camss_stats_awb_bg))
				return -EPROTO;
			gridFound = true;
			camss_stats_awb_bg config;
			std::memcpy(&config, data.data() + offset, sizeof(config));
			const uint32_t count = uint32_t(config.columns) * config.rows;
			if (!config.columns || !config.rows || config.columns > 160 || config.rows > 90 ||
			    config.region_width < 6 || config.region_width > 390 ||
			    config.region_height < 2 || config.region_height > 512 ||
			    ((config.left | config.top | config.region_width | config.region_height) & 1) ||
			    uint32_t(config.left) + uint32_t(config.columns) * config.region_width > width ||
			    uint32_t(config.top) + uint32_t(config.rows) * config.region_height > height ||
			    config.input_bits != 14 || !config.high_threshold || config.high_threshold > 16383 ||
			    header.size != sizeof(config) + count * sizeof(camss_stats_bg_region))
				return -EPROTO;
			auto &grid = parsed.grid;
			grid = { config.left, config.top, config.region_width, config.region_height,
				 config.columns, config.rows, config.high_threshold, config.input_bits, {} };
			grid.regions.resize(count);
			std::memcpy(grid.regions.data(), data.data() + offset + sizeof(config),
				    count * sizeof(camss_stats_bg_region));
			const uint32_t maximum = uint32_t(config.region_width) * config.region_height / 4;
			for (const auto &region : grid.regions) {
				const std::array<uint32_t, 4> sums{region.r_sum,region.b_sum,region.gr_sum,region.gb_sum};
				const std::array<uint16_t, 4> counts{region.r_count,region.b_count,region.gr_count,region.gb_count};
				for (unsigned int c = 0; c < 4; ++c)
					if (counts[c] > maximum || sums[c] > uint64_t(counts[c]) * config.high_threshold)
						return -EPROTO;
			}
		}
		/* Unknown, structurally valid blocks can be added without breaking BHIST. */
		offset += header.size;
	}
	if (!histogramFound)
		return -ENODATA;
	for (unsigned int i = 0; i < parsed.histogram.size(); ++i) {
		parsed.population += parsed.histogram[i];
		parsed.weightedSum += uint64_t(i) * parsed.histogram[i];
	}
	if (parsed.population != uint64_t(width / 2) * (height / 2))
		return -ENODATA;
	*result = std::move(parsed);
	return 0;
}

} /* namespace libcamera::ipa::camss */
