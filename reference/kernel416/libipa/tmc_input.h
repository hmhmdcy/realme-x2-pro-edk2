/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <cstdint>
namespace libcamera::ipa {
struct TmcAecExposurePair {
	uint64_t time0, time1;
	float gain0, gain1, sensitivity0, sensitivity1;
};
struct TmcHdrTriggers { float exposureTimeRatio, exposureGainRatio, sensitivityRatio; };
/* AEC slots1/0. Native TMC11 module88/92 receive time/sensitivity ratios;
 * its HDR control2 does not consume the exposure-gain ratio. */
bool calculateTargetTmcHdrTriggers(const TmcAecExposurePair &input, TmcHdrTriggers *output);
/* Actual IPE binder only writes1 when cache.version==1, otherwise preserves
 * initialVersion. The normal19928B request initialization supplies zero. */
uint32_t bindTargetIpeTmcVersion(uint32_t cacheVersion, uint32_t initialVersion);
} /* namespace libcamera::ipa */
