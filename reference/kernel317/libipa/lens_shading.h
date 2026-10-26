/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <array>
#include <cstdint>

namespace libcamera::ipa {

/* Full-sensor mesh. Mapping to a cropped/binned mode is a separate operation. */
constexpr unsigned int LscWidth = 17, LscHeight = 13;
constexpr unsigned int LscPoints = LscWidth * LscHeight;
enum LscChannel { LscR, LscGr, LscGb, LscB, LscChannels };
using LscMesh = std::array<std::array<float, LscPoints>, LscChannels>;

struct LscPackedMesh {
	std::array<uint32_t, LscPoints> grr;
	std::array<uint32_t, LscPoints> gbb;
};

bool lscCalibrationFactors(const LscMesh &golden, const LscMesh &unit,
			   LscMesh *factors);
bool lscApplyCalibration(const LscMesh &base, const LscMesh &factors,
			 LscMesh *calibrated);
bool lscPackTitan17x(const LscMesh &mesh, LscPackedMesh *packed);

} /* namespace libcamera::ipa */
