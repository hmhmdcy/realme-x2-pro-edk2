/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>
namespace libcamera::ipa {
struct Tmc11PolicyInput {
	uint32_t candidateUid, candidateEnable, cachedUid, cachePresent, moduleEnable;
	uint32_t forceUpdate, awbLock, aecLock, histogramPresent, oldHistogramPresent;
	std::array<float, 6> oldTriggers, newTriggers; /* DRC,dark,gain,lux,module88,module92 */
};
struct Tmc11PolicyResult {
	uint32_t moduleEnable, version, calculate, moduleAdrcPointer, requestAdrcPointer;
	uint32_t rootRefreshed, histogramSource, cachedUid;
	std::array<float, 6> cachedTriggers;
};
/* Existing ADRC allocation is required. Does not select a chromatix root,
 * allocate buffers, publish history, or change product defaults. */
bool evaluateTmc11Policy(const Tmc11PolicyInput &input, Tmc11PolicyResult *output);

enum class TmcLtmSource : uint32_t { OwnTmc10, Upstream, None };
struct TmcLtmInput {
	uint32_t rootPresent, rootEnable, useLtm, version;
	uint32_t upstreamPresent, upstreamLtmEnable, changed;
};
struct TmcLtmDecision { TmcLtmSource source; uint32_t ltmEnable, changed; };
/* Selection gate only: OwnTmc10 still requires successful allocation/calculation. */
bool selectTargetTmcLtmSource(const TmcLtmInput &input, TmcLtmDecision *output);

using TargetAdrcMetadata = std::array<uint8_t, 4236>;
/* Exact old HAL cache copy, including stale/unused bytes. Unknown versions
 * preserve knees; missing property clears only enable. This is a wire adapter,
 * not validation or permission to submit its contents to hardware. */
bool updateTargetAdrcMetadata(const TargetAdrcMetadata *property, TargetAdrcMetadata *cache);
} /* namespace libcamera::ipa */
