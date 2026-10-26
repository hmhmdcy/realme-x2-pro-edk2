/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>
#include <optional>
#include <vector>
#include <linux/qcom-camss-config.h>
#include <linux/qcom-ipe-a5.h>
#include "../libipa/ltm13_frame.h"
#include "../libipa/tmc_runtime.h"
#include "ipe_frame_history.h"

namespace libcamera {
class ValueNode;
namespace ipa::camss {
template<size_t N> struct ToneAecRegion { std::array<float, 4> trigger; std::array<float, N> data; };
struct IpeToneState {
	bool initialized = false, exposureValid = false;
	float exposureIndex = 0;
	Tmc11PolicyResult policy{};
	TargetAdrcMetadata adrc{}, cache{};
	Ltm13FaceSmoothingState smoothing{};
};
/* Calibration belongs in device-private configuration. This adapter initially
 * accepts explicitly single-exposure, linear-AE paths with no ADRC exposure
 * splitting or face-assisted exposure. It never pretends these inputs are
 * observed Android AEC metadata. Unsupported parent axes are rejected when
 * the selected calibration is exported, rather than silently dropped. */
class IpeToneProfile {
public:
	static int configure(const ValueNode &node, const camss_params_ife_gamma *gamma,
			     std::optional<IpeToneProfile> *profile);
	int calculate(const IpeFrameObservation &frame, const IpeToneState &history,
		      qcom_ipe_a5_frame_params *parameters, IpeToneState *next) const;
	bool factoryMode() const { return mode_ == 0; }
private:
	uint32_t mode_ = 0, ltmAec_ = 0, tmcAec_ = 0, gammaAec_ = 0;
	uint32_t tmcUid_ = 0, tmcEnabled_ = 0, tmcUseLtm_ = 0, tmcUseGtm_ = 0, tmc10Enabled_ = 0, tmc10UseLtm_ = 0;
	Ltm13FrameInput base_{};
	qcom_ipe_a5_colour colour_{};
	std::vector<ToneAecRegion<179>> ltm_;
	std::vector<ToneAecRegion<44>> tmc_;
	std::vector<ToneAecRegion<257>> gamma_;
	std::array<float, 257> tmcGamma_{};
	std::array<float, 1024> logWeights_{}, axis_{};
};
} /* namespace ipa::camss */
} /* namespace libcamera */
