/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <optional>
#include <vector>
#include <libcamera/base/span.h>
#include "libcamera/internal/yaml_parser.h"
#include "../libipa/colour_correction.h"

namespace libcamera::ipa::camss {

using ColourMatrix = std::array<float, 9>;
struct ColourCorrectionState {
	ColourCorrectionData data;
	ColourCorrectionParameters parameters;
	ColourMatrix effective;
};

class ColourCorrectionProfile {
public:
	static int configure(const ValueNode &tuning,
			     std::optional<ColourCorrectionProfile> *profile);
	int manual(Span<const float> matrix, ColourCorrectionState *state) const;
	int select(std::optional<int32_t> kelvin, const std::optional<ColourMatrix> &manual,
		   const ColourCorrectionState *fallback, ColourCorrectionState *state) const;
	float minimum() const { return -2048.0f / (1u << (7 + qfactor_)); }
	float maximum() const { return 2047.0f / (1u << (7 + qfactor_)); }
private:
	struct Node {
		std::array<float, 6> trigger{};
		std::vector<Node> children;
		ColourCorrectionData data{};
	};
	int readNodes(const ValueNode &value, unsigned int level, std::vector<Node> *nodes);
	int evaluate(const std::vector<Node> &nodes, unsigned int level, float kelvin,
		     ColourCorrectionData *data) const;
	int encode(const ColourCorrectionData &data, ColourCorrectionState *state) const;
	unsigned int qfactor_ = 0, hdrPosition_ = 2, aecPosition_ = 0, ledIndex_ = 0;
	float drcGain_ = 1, hdrRatio_ = 1, aecValue_ = 0;
	std::vector<Node> core_;
};

} /* namespace libcamera::ipa::camss */
