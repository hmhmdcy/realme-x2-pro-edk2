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
#include "colour_correction_profile.h"

namespace libcamera {
class ValueNode;
namespace ipa::camss {
template<size_t N> struct ToneAecRegion { std::array<float, 4> trigger; std::array<float, N> data; };
struct IpeToneState {
	bool initialized = false, ltmLuxValid = false;
 uint64_t gtmCookie = 0, gtmGeneration = 0;
 bool tmcHistogramValid = false;
 uint32_t tmcHistogramSof = 0;
 std::array<uint32_t,1024> tmcHistogram{};
	float ltmLuxIndex = 0;
	Tmc11PolicyResult policy{};
	TargetAdrcMetadata adrc{}, cache{};
	Ltm13FaceSmoothingState smoothing{};
	std::optional<ColourCorrectionState> colourCorrection;
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
		      qcom_ipe_a5_frame_params *parameters, IpeToneState *next,
               const IpeToneState *appliedTmc = nullptr) const;
 int prepareGtm(const IpeFrameObservation &frame, const IpeToneState &history,
                camss_params_ife_gtm *parameters, IpeToneState *next) const;
 int bootstrap(qcom_ipe_a5_frame_params *packet, const IpeFrameObservation *frame = nullptr,
               const IpeToneState *history = nullptr) const;
 const ColourCorrectionProfile *colourCorrection() const { return ccm_ ? &*ccm_ : nullptr; }
 bool tracksGtm() const { return gtmConfigured_; }
	bool factoryMode() const { return mode_ == 0; }
private:
	int prepareColour(const IpeFrameObservation &frame, const IpeToneState &history,
			  qcom_ipe_a5_frame_params *packet, IpeToneState *next) const;
	std::optional<ColourCorrectionProfile> ccm_;
	bool gtmConfigured_ = false, gtmEnabled_ = false;
 std::array<float,65> gtmAxis_{};
 std::array<uint32_t,65> gtmDomain_{};
 std::array<float,1024> gtmContrastAxis_{};
 int prepareTmc(const IpeFrameObservation &frame,const IpeToneState &history,IpeToneState *next) const;
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
