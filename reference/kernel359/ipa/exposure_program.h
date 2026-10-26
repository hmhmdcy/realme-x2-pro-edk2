/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <optional>

#include "libcamera/internal/value_node.h"
#include "../libipa/aec_antibanding.h"

namespace libcamera::ipa::camss {

/* A selected tuning table, independent of the AE target and filtering policy. */
class ExposureProgram
{
public:
	static int configure(const ValueNode &tuning, uint64_t minimumNs,
			     uint64_t maximumNs, uint64_t frameNs, float minimumGain,
			     std::optional<ExposureProgram> *program);
	bool adjust(float evStops);
	bool allocate(double exposureNsGain, uint64_t flickerPeriodNs,
		      AecExposureAllocation *allocation) const;
private:
	AecExposureTable source_, active_;
	AecExposureKnee anchor_{};
	AecExposureAdjustment adjustment_{};
	AecAntibandingConfiguration banding_{};
	bool adjustEv_ = false;
};

} /* namespace libcamera::ipa::camss */
