/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cstdint>

namespace libcamera::ipa {

struct AecExposureAnchor {
 float gain;
 uint64_t exposureTimeNs;
 float index;
};

/* Qualcomm tuning indices, not physical illuminance in lux or exposure EV. */
bool aecManualExposureIndex(const AecExposureAnchor &anchor, float gain,
                           uint64_t exposureTimeNs, float *index);
bool aecSensitivityExposureIndex(const AecExposureAnchor &anchor,
                                float correction, float sensitivity, float *index);

/* Input cells must already be the OEM-equivalent, processed 8-bit lux-luma
 * cells. This does not establish equivalence of raw Bayer statistics. */
bool aecUniformLuxLuma(const std::array<float,256> &cells, float *luma);

class AecLuxIndex {
public:
 struct Configuration {
  bool compensate;
  float referenceZeroSensitivity;
  float tableZeroSensitivity;
  float filterFactor;
 };
 bool configure(const Configuration &configuration);
 void reset() { previous_=0;initialized_=false; }
 bool calculate(float exposureIndex, float luma8, float *index,
                bool resetFilter=false);
private:
 Configuration configuration_{};
 bool configured_=false,initialized_=false;
 float previous_=0;
};
} /* namespace libcamera::ipa */
