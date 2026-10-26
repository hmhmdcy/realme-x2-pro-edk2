/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "aec_lux.h"
#include <algorithm>
#include <cmath>

namespace libcamera::ipa {
namespace {
/* Exact stored OEM double constant: a float32 approximation of1/log10(1.03).
 * Recomputing log10(1.03) changes trigger boundaries. */
constexpr double logarithmScale=77.898529052734375;
bool positive(float value) { return std::isfinite(value) && value>0; }
bool validAnchor(const AecExposureAnchor &anchor)
{ return positive(anchor.gain) && anchor.exposureTimeNs && std::isfinite(anchor.index); }
bool indexFromRatio(float ratio,float anchor,float *index)
{
 if(!index || !positive(ratio))return false;
 float delta=float(std::log10(double(ratio))*logarithmScale);
 float result=anchor+delta;
 if(!std::isfinite(result))return false;
 *index=result;return true;
}
} /* namespace */

bool aecManualExposureIndex(const AecExposureAnchor &anchor,float gain,
                           uint64_t exposureTimeNs,float *index)
{
 if(!validAnchor(anchor) || !positive(gain) || !exposureTimeNs)return false;
 float gainRatio=gain/anchor.gain;
 float timeRatio=float(exposureTimeNs)/float(anchor.exposureTimeNs);
 return indexFromRatio(timeRatio*gainRatio,anchor.index,index);
}

bool aecSensitivityExposureIndex(const AecExposureAnchor &anchor,float correction,
                                float sensitivity,float *index)
{
 if(!validAnchor(anchor) || !positive(correction) || !positive(sensitivity))return false;
 float zero=correction*anchor.gain;
 zero*=float(anchor.exposureTimeNs);
 return indexFromRatio(sensitivity/zero,anchor.index,index);
}

bool aecUniformLuxLuma(const std::array<float,256> &cells,float *luma)
{
 if(!luma)return false;
 float sum=0;
 for(float cell:cells){
  if(!std::isfinite(cell) || cell<0 || cell>255)return false;
  sum+=cell;
 }
 *luma=std::max(sum*(1.0f/256),.1f);return true;
}

bool AecLuxIndex::configure(const Configuration &configuration)
{
 if(!std::isfinite(configuration.filterFactor) || configuration.filterFactor<0 ||
    configuration.filterFactor>1 ||
    (configuration.compensate && (!positive(configuration.referenceZeroSensitivity) ||
                                 !positive(configuration.tableZeroSensitivity))))return false;
 configuration_=configuration;configured_=true;reset();return true;
}

bool AecLuxIndex::calculate(float exposureIndex,float luma8,float *index,bool resetFilter)
{
 if(!configured_ || !index || !std::isfinite(exposureIndex) || !positive(luma8))return false;
 float result;
 if(!indexFromRatio(50.0f/luma8,exposureIndex,&result))return false;
 if(configuration_.compensate) {
  float ratio=configuration_.tableZeroSensitivity/configuration_.referenceZeroSensitivity;
  if(!indexFromRatio(ratio,result,&result))return false;
 }
 result=std::max(result,0.0f);
 float previous=resetFilter?result:previous_;
 if(initialized_ && configuration_.filterFactor>0) {
  /* Keep the OEM's separate float multiply/add under default compiler FMA
   * contraction too; this runs once per frame. */
  volatile float adjustment=configuration_.filterFactor*(result-previous);
  result=previous+adjustment;
 }
 if(!std::isfinite(result))return false;
 previous_=result;initialized_=true;*index=result;return true;
}
} /* namespace libcamera::ipa */
