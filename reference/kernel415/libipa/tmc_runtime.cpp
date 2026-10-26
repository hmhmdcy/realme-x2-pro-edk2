/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "tmc_runtime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
namespace libcamera::ipa {
bool evaluateTmc11Policy(const Tmc11PolicyInput &input, Tmc11PolicyResult *output)
{
	if (!output || input.cachePresent > 1 || input.histogramPresent > 1 ||
	    input.oldHistogramPresent > 1 || input.awbLock > 255 || input.aecLock > 255 ||
	    !std::all_of(input.oldTriggers.begin(), input.oldTriggers.end(), [](float v) { return std::isfinite(v); }) ||
	    !std::all_of(input.newTriggers.begin(), input.newTriggers.end(), [](float v) { return std::isfinite(v); }))
		return false;
	Tmc11PolicyResult result{};
	result.moduleEnable = input.moduleEnable;
	result.rootRefreshed = !input.cachePresent || input.candidateUid != input.cachedUid;
	result.cachedUid = result.rootRefreshed ? input.candidateUid : input.cachedUid;
	if (result.rootRefreshed)
		result.moduleEnable = input.candidateEnable;
	result.version = result.moduleEnable; /* Actual binary does not normalize the raw value. */
	result.cachedTriggers = input.oldTriggers;
	result.histogramSource = input.oldHistogramPresent ? 1 : 0;
	bool changed = result.rootRefreshed;
	if (result.moduleEnable == 1) {
		bool triggerChanged = false;
		for (size_t i = 0; i < input.oldTriggers.size(); ++i) {
			volatile float difference = input.oldTriggers[i] - input.newTriggers[i];
			if (!(double(std::fabs(difference)) < 1e-9))
				triggerChanged = true;
		}
		if (triggerChanged) {
			result.cachedTriggers = input.newTriggers;
			if (input.histogramPresent)
				result.histogramSource = 2;
			changed = true;
		} else if (input.forceUpdate == 1) {
			/* Force does not refresh a histogram pointer when triggers are equal. */
			changed = true;
		}
		result.moduleAdrcPointer = 1;
	} else {
		changed = false;
	}
	result.requestAdrcPointer = 1; /* Existing allocation is published even while disabled. */
	result.calculate = changed && !(input.awbLock == 1 && input.aecLock == 1);
	*output = result;
	return true;
}
bool selectTargetTmcLtmSource(const TmcLtmInput &input, TmcLtmDecision *output)
{
	if (!output || input.rootPresent > 1 || input.upstreamPresent > 1 || input.changed > 1)
		return false;
	TmcLtmDecision result{ TmcLtmSource::None, 0, input.changed };
	if (input.rootPresent && input.rootEnable == 1 && input.useLtm == 1 && input.version == 0) {
		result = { TmcLtmSource::OwnTmc10, 1, 1 };
	} else if (input.upstreamPresent) {
		result.source = TmcLtmSource::Upstream;
		result.ltmEnable = input.upstreamLtmEnable;
	}
	*output = result;
	return true;
}
bool updateTargetAdrcMetadata(const TargetAdrcMetadata *property, TargetAdrcMetadata *cache)
{
	if (!cache || property == cache)
		return false;
	TargetAdrcMetadata result = *cache;
	if (!property) {
		std::fill_n(result.begin(), 4, 0);
	} else {
		std::copy_n(property->begin(), 16, result.begin());
		uint32_t version = uint32_t((*property)[4]) | uint32_t((*property)[5]) << 8 |
				   uint32_t((*property)[6]) << 16 | uint32_t((*property)[7]) << 24;
		if (version < 2)
			std::copy_n(property->begin() + 16, version ? 40 : 32, result.begin() + 16);
		std::copy(property->begin() + 56, property->end(), result.begin() + 56);
	}
	*cache = result;
	return true;
}
} /* namespace libcamera::ipa */
