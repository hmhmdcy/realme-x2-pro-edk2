/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <optional>
#include "libcamera/internal/yaml_parser.h"
#include "../libipa/aec_lux.h"
#include "statistics.h"

namespace libcamera::ipa::camss {

struct LuxResult {
	float exposureIndex, luma, index;
};

/* Optional per-mode reference coordinates. Their factory/mode binding is a
 * separate calibration task; an absent profile never invents an anchor. */
class LuxProfile {
public:
	static int configure(const ValueNode &tuning, std::optional<LuxProfile> *profile);
	void reset() { filter_.reset(); }
	bool calculate(const GridStatistics &grid, float analogueGain, uint64_t exposureNs,
		       float effectiveRed, float effectiveBlue, LuxResult *result);
private:
	AecExposureAnchor anchor_{};
	AecLuxIndex filter_;
	std::array<float, 3> weights_{}, referenceGains_{};
	bool compensateColour_ = false;
	float normalization_ = 1;
};

} /* namespace libcamera::ipa::camss */
