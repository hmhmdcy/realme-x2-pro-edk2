/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>

namespace libcamera::ipa {
struct Ltm13AdrcSamples {
	std::array<float, 65> equivalent12;
	std::array<float, 65> sampledGainQ10;
	std::array<float, 65> forwardGamma10;
};

struct Ltm13AdrcCurves {
	std::array<float, 65> scale;
	std::array<float, 65> curve;
};

struct Ltm13AdrcBlend {
	std::array<int32_t, 65> curve;
	std::array<int16_t, 65> scale;
};

struct Ltm13AdrcTables {
	std::array<uint32_t, 64> curve;
	std::array<uint32_t, 64> scale;
};

/* Convert already sampled ADRC gains. This does not calculate TMC knees,
 * percentages, version policy, or gain sampling. Inputs remain unchanged.
 * First gain is at least unity (1024); all 65 forward nodes are explicit. */
bool calculateLtm13Adrc(const Ltm13AdrcSamples &input, Ltm13AdrcCurves *output);

/* Base scale is the already rounded int16 curve after strength, temporal
 * processing and attenuation. Curve uses source nearest rounding; scale
 * uses truncation after the max. Failure preserves the complete output. */
bool blendLtm13Adrc(const Ltm13AdrcCurves &adrc, float mix,
		    const std::array<int32_t, 65> &reserveCurve,
		    const std::array<int16_t, 65> &baseScale,
		    Ltm13AdrcBlend *output);

/* Encode unquantized nodes using the target's clipping and sign rules.
 * These are LUT data words, without commands or device addresses. */
bool encodeLtm13AdrcTables(const Ltm13AdrcBlend &input, Ltm13AdrcTables *output);
} /* namespace libcamera::ipa */
