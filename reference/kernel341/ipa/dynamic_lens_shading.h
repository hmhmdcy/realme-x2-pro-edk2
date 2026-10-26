/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <optional>
#include <vector>
#include <linux/qcom-camss-config.h>
#include <libcamera/geometry.h>
#include "libcamera/internal/yaml_parser.h"
#include "../libipa/lens_shading.h"
#include "../libipa/lsc_resample.h"
#include "colour_correction_profile.h"
namespace libcamera::ipa::camss {
struct DynamicLscState {
 camss_params_lsc parameters{};
 std::optional<float> aecValue;
 std::optional<int32_t> temperature;
 std::optional<uint32_t> statisticsSof;
};
class DynamicLensShading {
public:
 static int configure(const ValueNode &tuning,const Size &input,
                      std::optional<DynamicLensShading> *profile);
 bool requiresLux() const {return aecPosition_==0;}
 int select(std::optional<int32_t> kelvin,const ColourCorrectionInputs *runtime,
            const DynamicLscState *fallback,DynamicLscState *state) const;
private:
 struct Node {std::array<float,6> trigger{};std::vector<Node> children;LscMesh gains{};};
 int readNodes(const ValueNode &value,unsigned level,std::vector<Node> *nodes);
 int evaluate(const std::vector<Node> &nodes,unsigned level,float kelvin,float aec,LscMesh *mesh) const;
 Size input_;
 LscMapping mapping_{};
 std::optional<LscMesh> factors_;
 unsigned hdrPosition_=2,aecPosition_=0,ledIndex_=0;
 float lensPosition_=0,drcGain_=1,hdrRatio_=1;
 std::vector<Node> core_;
};
uint32_t lensShadingTrace(const camss_params_lsc &parameters);
} /* namespace libcamera::ipa::camss */
