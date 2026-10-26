/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "colour_correction_profile.h"
#include <algorithm>
#include <cerrno>
#include <cmath>
#include <utility>

namespace libcamera::ipa::camss {
namespace {
constexpr std::array<unsigned int, 5> triggerSize{ 2, 6, 1, 4, 2 };
const ColourCorrectionData unity{ { 1, 0, 0, 0, 1, 0, 0, 0, 1 }, { 0, 0, 0 } };
} /* namespace */

int ColourCorrectionProfile::encode(const ColourCorrectionData &data,
				    ColourCorrectionState *state) const
{
	if (!state) return -EINVAL;
	ColourCorrectionState result;
	result.data = data;
	if (!encodeColourCorrection(data, qfactor_, &result.parameters, &result.effective))
		return -ERANGE;
	*state = result;
	return 0;
}

int ColourCorrectionProfile::manual(Span<const float> matrix,
				    ColourCorrectionState *state) const
{
	if (matrix.size() != 9) return -EINVAL;
	ColourCorrectionData data{};
	std::copy(matrix.begin(), matrix.end(), data.matrix.begin());
	return encode(data, state);
}

int ColourCorrectionProfile::select(std::optional<int32_t> kelvin,
				    const std::optional<ColourMatrix> &manualMatrix,
				    const ColourCorrectionState *fallback,
				    ColourCorrectionState *state, const ColourCorrectionInputs *runtime) const
{
	if (manualMatrix) return manual(*manualMatrix, state);
 std::optional<float> aec = aecValue_;
 if (runtimeAec_) aec = runtime ? (aecPosition_ == 0 ? runtime->luxIndex : runtime->analogueGain) : std::nullopt;
 if (aec && !std::isfinite(*aec)) return -ERANGE;
	if (!kelvin || !aec) {
		if (fallback) { *state = *fallback; return 0; }
		/* Undefined chromaticity, such as a zero channel gain, has no CCT.
		 * Keep the last matrix, or begin with unity, without inventing a CCT. */
		return encode(unity, state);
	}
	ColourCorrectionData data;
 int ret = evaluate(core_, 0, float(*kelvin), *aec, &data);
 if (ret) return ret;
 ret = encode(data, state);
 if (!ret) {
  state->aecValue = aec; state->temperature = kelvin;
  if (runtimeAec_ && runtime) state->statisticsSof = runtime->statisticsSof;
 }
 return ret;
}

int ColourCorrectionProfile::readNodes(const ValueNode &value, unsigned int level,
				       std::vector<Node> *nodes)
{
	if (!value.isList() || !value.size() || level >= triggerSize.size()) return -EINVAL;
	for (const auto &item : value.asList()) {
		if (!item.isDictionary()) return -EINVAL;
		const auto &trigger = item["trigger"];
		if (!trigger.isList() || trigger.size() != triggerSize[level]) return -EINVAL;
		Node node;
		for (unsigned int i = 0; i < trigger.size(); ++i) {
			auto v = trigger[i].get<float>();
			if (!v || !std::isfinite(*v)) return -EINVAL;
			node.trigger[i] = *v;
		}
		if (level == 2) {
			if (node.trigger[0] < 0 || std::floor(node.trigger[0]) != node.trigger[0]) return -EINVAL;
		} else {
			for (unsigned int i = 0; i < trigger.size(); i += 2)
				if (node.trigger[i] > node.trigger[i + 1]) return -EINVAL;
		}
		unsigned int position = level == 1 ? hdrPosition_ : level == 3 ? aecPosition_ : 0;
		if (!nodes->empty()) {
			if (level == 2 ? nodes->back().trigger[0] >= node.trigger[0]
				       : nodes->back().trigger[position + 1] > node.trigger[position])
				return -EINVAL;
		}
		if (level == 4) {
			const auto &matrix = item["matrix"], &offsets = item["offsets"];
			if (!matrix.isList() || matrix.size() != 9 || !offsets.isList() || offsets.size() != 3) return -EINVAL;
			for (unsigned int i = 0; i < 9; ++i) {
				auto v = matrix[i].get<float>();
				if (!v) return -EINVAL;
				node.data.matrix[i] = *v;
			}
			for (unsigned int i = 0; i < 3; ++i) {
				auto v = offsets[i].get<int32_t>();
				if (!v) return -EINVAL;
				node.data.offsets[i] = *v;
			}
			ColourCorrectionState check;
			if (encode(node.data, &check)) return -ERANGE;
		} else {
			int ret = readNodes(item["children"], level + 1, &node.children);
			if (ret) return ret;
		}
		nodes->push_back(std::move(node));
	}
	return 0;
}

int ColourCorrectionProfile::evaluate(const std::vector<Node> &nodes,
				      unsigned int level, float kelvin, float aecValue,
				      ColourCorrectionData *data) const
{
	if (nodes.empty() || level >= triggerSize.size()) return -EINVAL;
	auto child = [&](const Node &node, ColourCorrectionData *output) {
		if (level == 4) { *output = node.data; return 0; }
		return evaluate(node.children, level + 1, kelvin, aecValue, output);
	};
	if (level == 2) {
		for (const Node &node : nodes)
			if (node.trigger[0] == ledIndex_) return child(node, data);
		return -ENOENT;
	}
	float value = level == 0 ? drcGain_ : level == 1 ? hdrRatio_ : level == 3 ? aecValue : kelvin;
	unsigned int position = level == 1 ? hdrPosition_ : level == 3 ? aecPosition_ : 0;
	for (unsigned int i = 0; i < nodes.size(); ++i) {
		const Node &first = nodes[i];
		if (value <= first.trigger[position + 1] || i + 1 == nodes.size()) return child(first, data);
		const Node &second = nodes[i + 1];
		if (value < second.trigger[position]) {
			ColourCorrectionData a, b;
			int ret = child(first, &a);
			if (ret) return ret;
			ret = child(second, &b);
			if (ret) return ret;
			float weight = float((double(value) - first.trigger[position + 1]) /
					     (double(second.trigger[position]) - first.trigger[position + 1]));
			return interpolateColourCorrection(a, b, weight, data) ? 0 : -ERANGE;
		}
	}
	return -EINVAL;
}

int ColourCorrectionProfile::configure(const ValueNode &tuning,
				       std::optional<ColourCorrectionProfile> *profile)
{
	if (!profile) return -EINVAL;
	profile->reset();
	if (tuning.isEmpty()) return 0;
	if (!tuning.isDictionary()) return -EINVAL;
	if (!tuning["enabled"].isEmpty()) {
		auto enabled = tuning["enabled"].get<bool>();
		if (!enabled) return -EINVAL;
		if (!*enabled) return 0;
	}
	ColourCorrectionProfile result;
	auto q = tuning["qfactor"].get<unsigned int>();
	if (!q || *q > 3) return -EINVAL;
	result.qfactor_ = *q;
	auto aec = tuning["aec_control"].get<std::string>();
	auto hdr = tuning["hdr_control"].get<std::string>();
	if (!aec || !hdr) return -EINVAL;
	if (*aec == "lux_index") result.aecPosition_ = 0;
	else if (*aec == "analogue_gain") result.aecPosition_ = 2;
	else return -EINVAL;
	if (*hdr == "exposure_time_ratio") result.hdrPosition_ = 0;
	else if (*hdr == "sensitivity_ratio") result.hdrPosition_ = 2;
	else if (*hdr == "exposure_gain_ratio") result.hdrPosition_ = 4;
	else return -EINVAL;
 const auto source = tuning["aec_source"].get<std::string>("reference");
 if (source != "reference" && source != "runtime") return -EINVAL;
 result.runtimeAec_ = source == "runtime";
 /* DRC, HDR and flash coordinates remain explicit references. The optional
  * runtime AEC coordinate and CCT are selected for each ISP revision. */
	const auto &reference = tuning["reference_triggers"];
	if (!reference.isDictionary()) return -EINVAL;
	auto drc = reference["drc_gain"].get<float>(), ratio = reference["hdr_ratio"].get<float>(), aecValue = reference["aec_value"].get<float>();
	auto led = reference["led_index"].get<unsigned int>();
 if (result.runtimeAec_ && !aecValue) aecValue = 0.f;
	if (!drc || !ratio || !aecValue || !led || !std::isfinite(*drc) || !std::isfinite(*ratio) || !std::isfinite(*aecValue)) return -EINVAL;
	result.drcGain_ = *drc; result.hdrRatio_ = *ratio; result.aecValue_ = *aecValue; result.ledIndex_ = *led;
	int ret = result.readNodes(tuning["core"], 0, &result.core_);
	if (ret) return ret;
	ColourCorrectionData probe;
	ret = result.evaluate(result.core_, 0, 6500, result.aecValue_, &probe);
	if (ret) return ret;
	*profile = std::move(result);
	return 0;
}

} /* namespace libcamera::ipa::camss */
