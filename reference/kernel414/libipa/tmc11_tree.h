/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>
#include <vector>

namespace libcamera::ipa {
using Tmc11RegionValues = std::array<float, 44>;
struct Tmc11AecRegion {
	std::array<float, 4> trigger;
	Tmc11RegionValues data;
};
struct Tmc11HdrRegion {
	std::array<float, 6> trigger;
	std::vector<Tmc11AecRegion> children;
};
struct Tmc11DrcRegion {
	std::array<float, 2> trigger;
	std::vector<Tmc11HdrRegion> children;
};
struct Tmc11TreeTriggers {
	float drcGain, realGain, luxIndex;
	/* Actual module offsets; upstream HDR field identities remain unverified. */
	float module88, module92;
};
/* AEC0=lux/1=gain. HDR0=module88/1=module92/2=zero in this binary.
 * This numerical API neither selects a root nor changes its enable flag.
 * Input tree is immutable; failure leaves output untouched. */
bool interpolateTmc11Tree(const std::vector<Tmc11DrcRegion> &tree,
			 uint32_t aecControl, uint32_t hdrControl,
			 const Tmc11TreeTriggers &triggers, Tmc11RegionValues *output);
} /* namespace libcamera::ipa */
