/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <cstdint>

#include "aec_exposure_table.h"

namespace libcamera::ipa {

enum class AecAntibandingFpsMethod : uint32_t {
	LegacyAllowFpsToDrop,
	StrictlyEnforceFps,
	MaximizeExposureTime,
};

struct AecAntibandingConfiguration {
	bool enabled;
	uint64_t periodNs;
	float minimumPeriodFraction;
	float minimumGain;
	uint64_t minimumExposureTimeNs;
	uint64_t maximumExposureTimeNs;
	uint64_t minimumPreviewVerticalBlankingNs;
	AecAntibandingFpsMethod fpsMethod;
};

/* Adjust an already allocated exposure using the selected tuning policy.
 * This preserves sensitivity through gain compensation. It does not detect
 * flicker, quantize sensor lines, enforce maximum gain or program frame length.
 */
bool aecApplyAntibanding(const AecAntibandingConfiguration &configuration,
			const AecExposureAllocation &input,
			AecExposureAllocation *output);

} /* namespace libcamera::ipa */
