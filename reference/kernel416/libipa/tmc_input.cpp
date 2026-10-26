/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "tmc_input.h"
#include <cmath>
namespace libcamera::ipa {
bool calculateTargetTmcHdrTriggers(const TmcAecExposurePair &input, TmcHdrTriggers *output)
{
	if (!output || !std::isfinite(input.gain0) || !std::isfinite(input.gain1) ||
	    !std::isfinite(input.sensitivity0) || !std::isfinite(input.sensitivity1))
		return false;
	TmcHdrTriggers result{ 1, 1, 1 };
	if (input.time0)
		result.exposureTimeRatio = float(input.time1) / float(input.time0);
	if (!(double(std::fabs(input.gain0)) < 1e-9))
		result.exposureGainRatio = input.gain1 / input.gain0;
	if (!(double(std::fabs(input.sensitivity0)) < 1e-9))
		result.sensitivityRatio = input.sensitivity1 / input.sensitivity0;
	if (!std::isfinite(result.exposureTimeRatio) || !std::isfinite(result.exposureGainRatio) ||
	    !std::isfinite(result.sensitivityRatio))
		return false;
	*output = result;
	return true;
}
uint32_t bindTargetIpeTmcVersion(uint32_t cacheVersion, uint32_t initialVersion)
{
	return cacheVersion == 1 ? 1 : initialVersion;
}
} /* namespace libcamera::ipa */
