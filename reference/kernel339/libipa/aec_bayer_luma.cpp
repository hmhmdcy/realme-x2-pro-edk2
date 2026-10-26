/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "aec_bayer_luma.h"
#include <cmath>

namespace libcamera::ipa {
namespace {
bool positive(float value){return std::isfinite(value)&&value>0;}
bool validWeights(const std::array<float,3> &weights)
{
 for(float weight:weights)if(!std::isfinite(weight)||weight<0)return false;
 return true;
}
} /* namespace */

bool aecLumaWeights(const std::array<float,3> &tuning,
                    const std::array<float,3> &referenceGains,
                    const std::array<float,3> &currentGains,
                    bool compensate,std::array<float,3> *weights)
{
 if(!weights||!validWeights(tuning))return false;
 auto output=tuning;
 bool valid=true;
 for(unsigned i=0;i<3;i++)valid&=positive(referenceGains[i])&&positive(currentGains[i]);
 /* The OEM falls back to the tuning weights for invalid reference/input gains. */
 if(compensate&&valid)
  for(unsigned i=0;i<3;i++){
   float product=currentGains[i]*tuning[i];
   output[i]=product/referenceGains[i];
  }
 if(!validWeights(output))return false;
 *weights=output;return true;
}

bool aecBayerRegionLuma(const AecBayerLumaConfiguration &configuration,
                        const AecBayerRegion &region,AecLumaCell *result)
{
 if(!result||!configuration.pixelsPerChannel||configuration.pixelsPerChannel>65535||
    configuration.inputBits<8||configuration.inputBits>16||
    !positive(configuration.normalization)||!validWeights(configuration.weights))return false;
 const uint64_t pixels=configuration.pixelsPerChannel;
 std::array<uint64_t,4> totals,missing;
 for(unsigned i=0;i<4;i++){
  if(configuration.highThreshold[i]>((1u<<configuration.inputBits)-1)||
     region.counts[i]>pixels||region.sums[i]>uint64_t(region.counts[i])*configuration.highThreshold[i])return false;
  missing[i]=pixels-region.counts[i];
  totals[i]=region.sums[i]+missing[i]*configuration.highThreshold[i];
 }
 const float scale=1.0f/float(1u<<(configuration.inputBits-8));
 /* Retain the integer green average and distinct float products/adds. */
 volatile float red=configuration.weights[0]*float(totals[0]);
 volatile float green=configuration.weights[1]*float((totals[2]+totals[3])>>1);
 volatile float blue=configuration.weights[2]*float(totals[1]);
 float weighted=red+green;weighted=blue+weighted;
 float numerator=scale*weighted;
 float denominator=configuration.normalization*float(pixels);
 AecLumaCell output{numerator/denominator,float(missing[0]+missing[1]+missing[2]+missing[3])/float(pixels*4)};
 if(!std::isfinite(output.luma)||!std::isfinite(output.saturatedFraction))return false;
 *result=output;return true;
}

bool aecLegacyLumaGrid(const std::vector<AecLumaCell> &regions,
                       unsigned int columns,unsigned int rows,
                       std::array<AecLumaCell,256> *result)
{
 if(!result||!columns||!rows||columns%16||rows%16||uint64_t(columns)*rows>3072||regions.size()!=size_t(columns)*rows)return false;
 std::array<AecLumaCell,256> cells{};
 std::array<unsigned int,256> count{};
 const unsigned int cellWidth=columns/16,cellHeight=rows/16;
 for(unsigned int index=0;index<regions.size();index++){
  const auto &region=regions[index];
  if(!std::isfinite(region.luma)||region.luma<0||!std::isfinite(region.saturatedFraction)||region.saturatedFraction<0||region.saturatedFraction>1)return false;
  unsigned int x=(index%columns)/cellWidth,y=(index/columns)/cellHeight;
  cells[y*16+x].luma+=region.luma;cells[y*16+x].saturatedFraction+=region.saturatedFraction;++count[y*16+x];
 }
 for(unsigned i=0;i<cells.size();i++){
  if(!count[i])return false;
  cells[i].luma/=float(count[i]);cells[i].saturatedFraction/=float(count[i]);
 }
 *result=cells;return true;
}
} /* namespace libcamera::ipa */
