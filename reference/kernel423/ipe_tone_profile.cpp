/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ipe_tone_profile.h"
#include "../libipa/tmc_input.h"
#include "../libipa/gamma_segments.h"
#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstring>
#include <limits>
#include <libcamera/base/span.h>
#include "libcamera/internal/yaml_parser.h"

namespace libcamera::ipa::camss {
namespace {
template<class T, size_t N> bool array(const ValueNode &node, std::array<T, N> *out)
{
	if (!node.isList() || node.size() != N) return false;
	for (size_t i = 0; i < N; ++i) {
		auto value = node[i].get<T>();
		if (!value || !std::isfinite(double(*value))) return false;
		(*out)[i] = *value;
	}
	return true;
}
template<size_t N> bool regions(const ValueNode &node, std::vector<ToneAecRegion<N>> *out)
{
	if (!node.isList() || !node.size() || node.size() > 20) return false;
	for (const auto &leaf : node.asList()) {
		ToneAecRegion<N> r;
		if (!array(leaf["trigger"], &r.trigger) || !array(leaf["data"], &r.data) ||
		    r.trigger[0] > r.trigger[1] || r.trigger[2] > r.trigger[3]) return false;
		out->push_back(r);
	}
	return true;
}
float blend(float a, float b, float ratio)
{
	int32_t ai = int32_t(a), bi = int32_t(b);
	double af = double(a - float(ai)) * 1000000.0;
	double bf = double(b - float(bi)) * 1000000.0;
	volatile double fractional = double(ratio) * (bf - af);
	float fraction = float(af + fractional) / 1000000.0f;
	volatile double integral = double(ratio) * float(int64_t(bi) - ai);
	return fraction + float(double(ai) + integral);
}
template<size_t N> bool select(const std::vector<ToneAecRegion<N>> &regions, uint32_t axis, float trigger,
			     std::array<float, N> *out)
{
	if (regions.empty() || axis > 1 || !std::isfinite(trigger)) return false;
	size_t left = regions.size() - 1, right = left; float ratio = 0;
	for (size_t i = 0; i < regions.size(); ++i) {
		if (trigger <= regions[i].trigger[axis * 2 + 1]) { left = right = i; break; }
		if (i + 1 < regions.size() && trigger < regions[i + 1].trigger[axis * 2]) {
			left = i; right = i + 1;
			double a = regions[i].trigger[axis * 2 + 1], b = regions[i + 1].trigger[axis * 2];
			ratio = float((double(trigger) - a) / (b - a)); break;
		}
	}
	if (left == right) { *out = regions[left].data; return true; }
	for (size_t i = 0; i < N; ++i) {
		float a = regions[left].data[i], b = regions[right].data[i];
		if (double(a) < INT32_MIN || double(a) > INT32_MAX || double(b) < INT32_MIN || double(b) > INT32_MAX ||
		    double(b) - double(a) < INT32_MIN || double(b) - double(a) > INT32_MAX) return false;
		(*out)[i] = blend(a, b, ratio);
	}
	return true;
}
template<class T> void store(TargetAdrcMetadata &out, size_t at, const T &value)
{
	std::memcpy(out.data() + at, &value, sizeof value);
}
uint32_t word(const TargetAdrcMetadata &in, size_t at)
{
	uint32_t v; std::memcpy(&v, in.data() + at, 4); return v;
}
Tmc11GenerationResult generated(const TargetAdrcMetadata &in)
{
	Tmc11GenerationResult r{};
	std::memcpy(r.pchip.x.data(), in.data() + 16, 20); std::memcpy(r.pchip.y.data(), in.data() + 36, 20);
	std::memcpy(&r.darkGain, in.data() + 56, 4); std::memcpy(&r.gtmPercentage, in.data() + 60, 4);
	std::memcpy(&r.ltm.percentage, in.data() + 64, 4); std::memcpy(r.pchip.coefficient.data(), in.data() + 92, 36);
	std::memcpy(r.contrastCurve.data(), in.data() + 128, 4096);
	std::memcpy(&r.ltm.bright, in.data() + 4228, 4); std::memcpy(&r.ltm.dark, in.data() + 4232, 4);
	return r;
}
} /* namespace */
int IpeToneProfile::configure(const ValueNode &node, const camss_params_ife_gamma *ife,
			    std::optional<IpeToneProfile> *out)
{
	if (!out) return -EINVAL;
	out->reset(); if (node.isEmpty()) return 0;
	if (!node.isDictionary()) return -EINVAL;
	auto enabled = node["enabled"].get<bool>(); if (!enabled) return -EINVAL;
	if (!*enabled) return 0;
	if (!ife || node["input_policy"].get<std::string>("") != "single-exposure-linear-ae-no-face" ||
	    node["input_transfer"].get<std::string>("") != "ife-green-common-rgb" ||
	    node["parent_axes"].get<std::string>("") != "single-drc-single-hdr-led-off-cct-invariant") return -ENOTSUP;
	IpeToneProfile p;
	std::string mode = node["mode"].get<std::string>("");
	if (mode == "factory") p.mode_ = 0;
	else if (mode == "gamma-roundtrip") p.mode_ = 1;
	else if (mode == "colour-roundtrip") p.mode_ = 2;
	else return -EINVAL;
	p.ltmAec_ = node["ltm_aec_control"].get<uint32_t>(2);
	p.tmcAec_ = node["tmc_aec_control"].get<uint32_t>(2);
	p.gammaAec_ = node["gamma_aec_control"].get<uint32_t>(2);
	if (p.ltmAec_ > 1 || p.tmcAec_ > 1 || p.gammaAec_ > 1 ||
	    !regions(node["ltm_regions"], &p.ltm_) || !regions(node["tmc_regions"], &p.tmc_) ||
	    !regions(node["gamma_regions"], &p.gamma_) || !array(node["tmc_gamma"], &p.tmcGamma_) ||
	    !array(node["histogram_log_weights"], &p.logWeights_) || !array(node["contrast_axis"], &p.axis_)) return -EINVAL;
	std::array<uint8_t, sizeof(qcom_ipe_a5_colour)> bytes;
	if (!array(node["colour"], &bytes)) return -EINVAL;
	std::memcpy(&p.colour_, bytes.data(), bytes.size());
	if (p.colour_.modules != (QCOM_IPE_A5_COLOUR_CST | QCOM_IPE_A5_COLOUR_CV) || p.colour_.padding) return -EINVAL;
	p.tmcUid_ = node["tmc_uid"].get<uint32_t>(0);
	p.tmcEnabled_ = node["tmc_enabled"].get<uint32_t>(2); p.tmcUseLtm_ = node["tmc_use_ltm"].get<uint32_t>(2);
	p.tmcUseGtm_ = node["tmc_use_gtm"].get<uint32_t>(2);
	p.tmc10Enabled_ = node["tmc10_enabled"].get<uint32_t>(2); p.tmc10UseLtm_ = node["tmc10_use_ltm"].get<uint32_t>(2);
	if (!p.tmcUid_ || p.tmcEnabled_ > 1 || p.tmcUseLtm_ > 1 || p.tmcUseGtm_ > 1 || p.tmc10Enabled_ > 1 || p.tmc10UseLtm_ > 1) return -EINVAL;
	std::array<uint32_t, 5> flags;
	if (!array(node["rgb2y"], &p.base_.constants.rgb2y) || !array(node["flags"], &flags) ||
	    !array(node["weights"], &p.base_.constants.weights) || !array(node["mask_kernel"], &p.base_.constants.maskKernel) ||
	    !array(node["mask_curve"], &p.base_.constants.maskCurve) || !array(node["reserve_curve"], &p.base_.reserveCurve)) return -EINVAL;
	for (uint32_t f : flags) if (f > 1) return -EINVAL;
	auto &c = p.base_.constants;
	c.reverseGamma = flags[0]; c.localAdaptation = flags[1]; c.maskFilter = flags[2];
	c.dataCollection = flags[3]; c.imageProcessing = flags[4];
	c.lceThreshold = node["lce_threshold"].get<uint32_t>(UINT32_MAX);
	p.base_.curves.manualCurve = node["manual_curve"].get<uint32_t>(2);
	if (c.lceThreshold > 1023 || p.base_.curves.manualCurve > 1) return -EINVAL;
	for (unsigned i = 0; i < 64; ++i) {
		for (unsigned ch : {0U, 2U}) if (ife->segments[ch][i].base != ife->segments[1][i].base ||
		    ife->segments[ch][i].delta != ife->segments[1][i].delta) return -ENOTSUP;
		p.base_.ifeGreen[i] = ife->segments[1][i].base;
		p.base_.forwardGamma[i] = float(ife->segments[1][i].base);
	}
	auto endpoint = node["ife_forward_endpoint"].get<float>();
	if (!endpoint || !std::isfinite(*endpoint) || *endpoint < 0 || *endpoint > 1024) return -EINVAL;
	if (*endpoint != float(ife->segments[1][63].base + ife->segments[1][63].delta)) return -EINVAL;
	p.base_.forwardGamma[64] = *endpoint;
	/* The explicit single-exposure path has no HDR/ADRC exposure split and
	 * no face-assisted AEC transition. These are native mode policies, not
	 * reconstructed Android AEC fields124/140. */
	p.base_.smoothing = {0, 0, 0};
	*out = std::move(p); return 0;
}
int IpeToneProfile::calculate(const IpeFrameObservation &frame, const IpeToneState &history,
			    qcom_ipe_a5_frame_params *parameters, IpeToneState *next) const
{
	if (!parameters || !next || next == &history || !frame.luxValid || !frame.ifeGammaOverride) return -ENODATA;
	qcom_ipe_a5_frame_params packet{}; packet.version = 1; packet.size = sizeof packet; packet.colour = colour_;
	IpeToneState state = history;
	if (mode_ == 2) { *parameters = packet; *next = state; return 0; }
	Ltm13FrameInput in = base_;
	std::array<float, 179> leaf;
	if (!select(ltm_, ltmAec_, ltmAec_ ? frame.analogueGain : frame.luxIndex, &leaf)) return -EINVAL;
	std::copy_n(leaf.begin(), 65, in.constants.laCurve.begin());
	std::copy_n(leaf.begin() + 65, 65, in.curves.scale.begin());
	std::copy_n(leaf.begin() + 130, 17, in.curves.lcePositive.begin());
	std::copy_n(leaf.begin() + 147, 17, in.curves.lceNegative.begin());
	in.constants.yRatioMaximum = leaf[164]; in.curves.strength = leaf[165];
	in.curves.attenuationStart = leaf[166]; in.curves.attenuationEnd = leaf[167];
	in.curves.darkBoost = leaf[168]; in.curves.brightSuppress = leaf[169]; in.curves.lceStrength = leaf[170];
	in.curves.darkRange = leaf[173]; in.curves.brightRange = leaf[174]; in.curves.darkMaximum = leaf[175];
	in.curves.brightMaximum = leaf[176]; in.curves.darkGamma = leaf[177]; in.curves.brightGamma = leaf[178];
	in.curves.exposureIndex = frame.exposureIndex;
	in.curves.previousExposureIndex = history.exposureValid ? history.exposureIndex : frame.exposureIndex;
	Tmc11GenerationResult adrc; bool useAdrc = false;
	if (mode_ == 0) {
		Tmc11PolicyInput policy{ tmcUid_, tmcEnabled_, history.policy.cachedUid, history.initialized,
			history.policy.moduleEnable, 1, 0, 0, 1, 0, history.policy.cachedTriggers,
			{1, 1, frame.analogueGain, frame.luxIndex, 1, 1} };
		if (!evaluateTmc11Policy(policy, &state.policy)) return -EINVAL;
		if (state.policy.calculate) {
			std::array<float, 44> values; Tmc11Region r;
			if (!select(tmc_, tmcAec_, tmcAec_ ? frame.analogueGain : frame.luxIndex, &values)) return -EINVAL;
			std::memcpy(&r, values.data(), sizeof r);
			if (!generateTmc11Curve(r, 1, 1, tmcGamma_, logWeights_, &frame.histogram, &adrc)) return -ERANGE;
			store(state.adrc, 0, uint32_t(1)); store(state.adrc, 4, uint32_t(1));
			store(state.adrc, 8, tmcUseGtm_); store(state.adrc, 12, tmcUseLtm_);
			store(state.adrc, 16, adrc.pchip.x); store(state.adrc, 36, adrc.pchip.y);
			store(state.adrc, 56, adrc.darkGain); store(state.adrc, 60, adrc.gtmPercentage);
			store(state.adrc, 64, adrc.ltm.percentage); store(state.adrc, 92, adrc.pchip.coefficient);
			store(state.adrc, 128, adrc.contrastCurve); store(state.adrc, 4224, uint32_t(2));
			store(state.adrc, 4228, adrc.ltm.bright); store(state.adrc, 4232, adrc.ltm.dark);
		}
		if (!updateTargetAdrcMetadata(state.policy.moduleAdrcPointer ? &state.adrc : nullptr, &state.cache)) return -EINVAL;
		uint32_t version = bindTargetIpeTmcVersion(word(state.cache, 4), 0);
		TmcLtmDecision decision;
		if (!selectTargetTmcLtmSource({1, tmc10Enabled_, tmc10UseLtm_, version, 1, word(state.cache, 12), 1}, &decision)) return -EINVAL;
		if (decision.source == TmcLtmSource::OwnTmc10) return -ENOTSUP;
		useAdrc = decision.source == TmcLtmSource::Upstream && decision.ltmEnable;
		if (useAdrc) adrc = generated(state.cache);
	} else {
		in.constants.localAdaptation = 0; in.constants.maskFilter = 0; in.constants.dataCollection = 0;
		in.curves.strength = in.curves.lceStrength = 0; in.reserveCurve.fill(0);
	}
	Ltm13Program program;
	if (!prepareLtm13Frame(in, history.smoothing, useAdrc ? &adrc : nullptr, useAdrc ? &axis_ : nullptr,
			      &program, &state.smoothing)) return -ERANGE;
	static_assert(sizeof(program) == sizeof(packet.ltm));
	std::memcpy(&packet.ltm, &program, sizeof program); packet.flags = QCOM_IPE_A5_LTM | QCOM_IPE_A5_GAMMA;
	std::array<float, 257> gamma;
	if (mode_ == 0) {
		if (!select(gamma_, gammaAec_, gammaAec_ ? frame.analogueGain : frame.luxIndex, &gamma)) return -EINVAL;
	} else {
		for (unsigned i = 0; i < 256; ++i) {
			unsigned at = i / 4; gamma[i] = base_.forwardGamma[at] +
				(base_.forwardGamma[at + 1] - base_.forwardGamma[at]) * float(i % 4) / 4;
		}
		gamma[256] = base_.forwardGamma[64];
	}
	GammaSegments<256> encoded;
	if (!encodeGammaSegments<256>(gamma, &encoded)) return -ERANGE;
	for (unsigned ch = 0; ch < 3; ++ch) for (unsigned i = 0; i < 256; ++i) {
		packet.gamma.base[ch][i] = encoded[i] & 1023;
		uint32_t d = (encoded[i] >> 10) & 1023; packet.gamma.delta[ch][i] = d >= 512 ? int(d) - 1024 : int(d);
	}
	state.initialized = true; state.exposureValid = true; state.exposureIndex = frame.exposureIndex;
	*parameters = packet; *next = state; return 0;
}
} /* namespace libcamera::ipa::camss */
