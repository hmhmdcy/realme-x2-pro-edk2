/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "lux_profile.h"
#include <cerrno>
#include <charconv>
#include <cmath>
#include <utility>
#include "../libipa/aec_bayer_luma.h"

namespace libcamera::ipa::camss {

int LuxProfile::configure(const ValueNode &tuning, std::optional<LuxProfile> *profile)
{
	if (!profile) return -EINVAL;
	profile->reset();
	if (tuning.isEmpty()) return 0;
	if (!tuning.isDictionary()) return -EINVAL;
	if (!tuning["enabled"].isEmpty()) {
		auto enabled = tuning["enabled"].get<bool>();
		if (!enabled) return -EINVAL;
		if (!*enabled) return 0;
	}
	LuxProfile result;
	const auto &anchor = tuning["exposure_anchor"];
	auto gain = anchor["analogue_gain"].get<float>();
	auto timeText = anchor["exposure_time_ns"].get<std::string>();
	auto index = anchor["index"].get<float>();
	if (!gain || !timeText || !index) return -EINVAL;
	/* ValueNode implements integer accessors only through uint32_t. Preserve
	 * the 64-bit nanosecond domain without converting it through float. */
	uint64_t time = 0;
	auto [end, error] = std::from_chars(timeText->data(), timeText->data() + timeText->size(), time);
	if (error != std::errc() || end != timeText->data() + timeText->size()) return -EINVAL;
	result.anchor_ = { *gain, time, *index };
	float check;
	if (!aecManualExposureIndex(result.anchor_, *gain, time, &check)) return -ERANGE;
	auto array = [](const ValueNode &value, std::array<float, 3> *output) {
		if (!value.isList() || value.size() != 3) return false;
		for (unsigned int i = 0; i < 3; ++i) {
			auto v = value[i].get<float>();
			if (!v || !std::isfinite(*v)) return false;
			(*output)[i] = *v;
		}
		return true;
	};
	auto colour = tuning["compensate_colour"].get<bool>();
	auto normalization = tuning["normalization"].get<float>();
	if (!colour || !normalization || !std::isfinite(*normalization) || *normalization <= 0 ||
	    !array(tuning["weights"], &result.weights_) ||
	    !array(tuning["reference_gains"], &result.referenceGains_)) return -EINVAL;
	for (float weight : result.weights_) if (weight < 0) return -ERANGE;
	result.compensateColour_ = *colour;
	result.normalization_ = *normalization;
	const auto &lux = tuning["lux"];
	auto compensate = lux["compensate_sensitivity"].get<bool>();
	auto factor = lux["filter_factor"].get<float>();
	if (!compensate || !factor) return -EINVAL;
	float reference = 0, zero = 0;
	if (*compensate) {
		auto r = lux["reference_zero_sensitivity"].get<float>();
		auto z = lux["table_zero_sensitivity"].get<float>();
		if (!r || !z) return -EINVAL;
		reference = *r; zero = *z;
	}
	if (!result.filter_.configure({ *compensate, reference, zero, *factor })) return -ERANGE;
	*profile = std::move(result);
	return 0;
}

bool LuxProfile::calculate(const GridStatistics &grid, float analogueGain,
			   uint64_t exposureNs, float red, float blue, LuxResult *result)
{
	if (!result || grid.regions.empty()) return false;
	LuxResult output;
	if (!aecManualExposureIndex(anchor_, analogueGain, exposureNs, &output.exposureIndex)) return false;
	std::array<float, 3> weights;
	if (!aecLumaWeights(weights_, referenceGains_, { red, 1, blue }, compensateColour_, &weights)) return false;
	AecBayerLumaConfiguration config{
		uint32_t(grid.width) * grid.height / 4,
		{ grid.highThreshold, grid.highThreshold, grid.highThreshold, grid.highThreshold },
		grid.inputBits, weights, normalization_
	};
	std::vector<AecLumaCell> regions;
	regions.reserve(grid.regions.size());
	for (const auto &raw : grid.regions) {
		AecBayerRegion region{ { raw.r_sum, raw.b_sum, raw.gr_sum, raw.gb_sum },
				       { raw.r_count, raw.b_count, raw.gr_count, raw.gb_count } };
		AecLumaCell cell;
		if (!aecBayerRegionLuma(config, region, &cell)) return false;
		regions.push_back(cell);
	}
	std::array<AecLumaCell, 256> pooled;
	if (!aecLegacyLumaGrid(regions, grid.columns, grid.rows, &pooled)) return false;
	std::array<float, 256> luma;
	for (unsigned int i = 0; i < luma.size(); ++i) luma[i] = pooled[i].luma;
	if (!aecUniformLuxLuma(luma, &output.luma) ||
	    !filter_.calculate(output.exposureIndex, output.luma, &output.index)) return false;
	*result = output;
	return true;
}

} /* namespace libcamera::ipa::camss */
