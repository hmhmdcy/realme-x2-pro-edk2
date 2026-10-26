/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <array>
#include "../libipa/agc_mean_luminance.h"
#include <linux/qcom-camss-config.h>

namespace libcamera::ipa::camss {

/* BHIST is post-BLS, pre-WB, linear Y; it supplies no RGB AWB information. */
class HardwareAgc final : public AgcMeanLuminance
{
public:
 int initialise(const ValueNode &tuning, double lineUs, int32_t minLines, int32_t maxLines,
                double minGain, double maxGain, const CameraSensorHelper *helper);
 int calculate(Span<const uint32_t> bins, uint32_t exposureLines, uint32_t gainCode,
               uint32_t *nextLines, uint32_t *nextCode);
private:
 double estimateLuminance(double gain) const override;
 std::array<uint32_t, CAMSS_STATS_BHIST_BINS> bins_{};
 uint64_t population_ = 0;
 double lineUs_ = 0;
 int32_t minLines_ = 0, maxLines_ = 0;
 double minGain_ = 0, maxGain_ = 0;
 const CameraSensorHelper *helper_ = nullptr;
};
}
