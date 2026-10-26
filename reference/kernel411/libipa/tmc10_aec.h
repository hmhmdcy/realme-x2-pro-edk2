/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>

namespace libcamera::ipa {
enum class Tmc10AecControl : uint32_t { LuxIndex = 0, RealGain = 1 };
struct Tmc10AecRegion {
	/* Lux start/end, real gain start/end. */
	std::array<float, 4> trigger;
	/* GTM,LTM,LA,Gamma percentages,knee midpoint,dark boost,reserves1..5. */
	std::array<float, 11> data;
};
struct Tmc10AecResult {
	std::array<float, 11> data;
	uint32_t startIndex, endIndex;
	float ratio;
};
/* Select within a trigger region; interpolate only in the gap to the next.
 * Does not select a TMC version or enable a factory-disabled root.
 * Regions retain their source order; the first matching region wins,
 * including overlapping intervals in unused factory control axes.
 * Failed calls preserve output and never modify region data. */
bool interpolateTmc10Aec(const Tmc10AecRegion *regions, uint32_t count,
			Tmc10AecControl control, float luxIndex, float realGain,
			Tmc10AecResult *output);
} /* namespace libcamera::ipa */
