/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <array>
#include <map>
#include "../libipa/agc_mean_luminance.h"
#include "exposure_program.h"
#include <linux/qcom-camss-config.h>

namespace libcamera::ipa::camss {

/* BHIST is post-BLS, pre-WB, linear Y; it supplies no RGB AWB information. */
class HardwareAgc final : public AgcMeanLuminance
{
public:
	int initialise(const ValueNode &tuning, double lineUs, int32_t minLines, int32_t maxLines,
		       double minGain, double maxGain, const CameraSensorHelper *helper,
		       const ValueNode &program, uint64_t frameNs,
		       uint32_t minimumGainCode, uint32_t maximumGainCode);
	int calculate(uint32_t sof, Span<const uint32_t> bins, uint32_t exposureLines, uint32_t gainCode,
		      uint32_t *nextLines, uint32_t *nextCode);
	static bool algorithmControl(unsigned int id);
	bool hasExposureProgram() const { return program_.has_value(); }
	int validateControls(const ControlList &controls) const;
	int applyControls(const ControlList &controls, uint32_t firstSof = 0);
	int resetControls();
	void metadata(uint32_t sof, ControlList *metadata) const;
private:
	double estimateLuminance(double gain) const override;
	std::array<uint32_t, CAMSS_STATS_BHIST_BINS> bins_{};
	uint64_t population_ = 0;
	double lineUs_ = 0;
	int32_t minLines_ = 0, maxLines_ = 0;
	double minGain_ = 0, maxGain_ = 0;
	uint32_t minimumGainCode_ = 0, maximumGainCode_ = 0;
	const CameraSensorHelper *helper_ = nullptr;
	std::optional<ExposureProgram> program_;
	float evStops_ = 0;
	int32_t flickerMode_ = 0, flickerPeriodUs_ = 0;
	struct State { float ev; int32_t mode, periodUs; };
	std::map<uint32_t, State> history_;
};

} /* namespace libcamera::ipa::camss */
