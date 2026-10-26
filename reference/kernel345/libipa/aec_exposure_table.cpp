/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "aec_exposure_table.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace libcamera::ipa {
bool AecExposureTable::configure(const std::vector<AecExposureKnee> &knees)
{
 if(knees.size()<2)return false;
 for(size_t i=0;i<knees.size();i++) {
  const auto &knee=knees[i];
  if(!std::isfinite(knee.gain) || knee.gain<=0 || !knee.exposureTimeNs || !std::isfinite(knee.index) ||
     static_cast<uint32_t>(knee.priority)>2 || (i && knee.index<knees[i-1].index))return false;
 }
 knees_=knees;return true;
}

bool AecExposureTable::allocate(float index,AecExposureAllocation *allocation) const
{
 if(!allocation || knees_.size()<2 || !std::isfinite(index))return false;
 /* Match the OEM comparison/tie rules, including a requested negative zero. */
 float selected=index>knees_.front().index?index:knees_.front().index;
 selected=selected<knees_.back().index?selected:knees_.back().index;
 auto upper=std::upper_bound(knees_.begin(),knees_.end(),selected,
  [](float value,const AecExposureKnee &knee){return value<knee.index;});
 size_t next=std::max<size_t>(upper-knees_.begin(),1);
 const auto &base=knees_[next-1];
 AecExposureAllocation result{base.gain,base.exposureTimeNs,selected};
 float delta=selected-base.index;
 if(delta>0) {
  if(next>=knees_.size())return false;
  const auto &limit=knees_[next];
  float ratio=std::pow(1.03f,delta),gainRatio,timeRatio;
  if(!std::isfinite(ratio))return false;
  if(base.priority==AecExposurePriority::Gain) {
   gainRatio=limit.gain/base.gain;
   if(ratio<gainRatio){gainRatio=ratio;timeRatio=1.;}
   else timeRatio=ratio/gainRatio;
  } else {
   /* The OEM treats the declared Maximum value as time priority too. */
   float maximum=float(limit.exposureTimeNs)/float(base.exposureTimeNs);
   timeRatio=std::min(ratio,maximum);
   gainRatio=ratio<maximum?1.f:ratio/maximum;
  }
  result.gain=base.gain*gainRatio;
  float increment=(timeRatio-1.f)*float(base.exposureTimeNs);
  if(!std::isfinite(result.gain) || result.gain<=0 || !std::isfinite(increment) || increment>=0x1p64f)return false;
  /* Match FCVTZU's zero for a negative increment. Retain the exact integer
   * anchor and truncate only its float increment, then add in uint64. */
  uint64_t extra=increment>0?uint64_t(increment):0;
  if(extra>std::numeric_limits<uint64_t>::max()-base.exposureTimeNs)return false;
  result.exposureTimeNs+=extra;
 }
 *allocation=result;return true;
}

bool AecExposureTable::frameTimeKnee(uint64_t maximumExposureTimeNs,AecExposureKnee *knee) const
{
 if(!knee || knees_.size()<2 || !maximumExposureTimeNs)return false;
 float index=knees_.back().index;
 if(knees_.back().exposureTimeNs>maximumExposureTimeNs) {
  auto found=std::find_if(knees_.begin(),knees_.end(),[&](const auto &point){return point.exposureTimeNs>=maximumExposureTimeNs;});
  if(found==knees_.end())return false;
  size_t position=found-knees_.begin();
  const auto &base=knees_[position?position-1:0];index=base.index;
  constexpr double scale=77.898529052734375;
  auto offset=[](float ratio){return float(std::log10(double(ratio))*scale);};
  if(base.priority==AecExposurePriority::Gain) {
   size_t next=position?position:1;
   float ratio=knees_[next].gain/base.gain;index+=offset(ratio);
  }
  float ratio=float(maximumExposureTimeNs)/float(base.exposureTimeNs);index+=offset(ratio);
 }
 AecExposureAllocation allocation;
 if(!allocate(index,&allocation))return false;
 *knee={allocation.gain,allocation.exposureTimeNs,AecExposurePriority::Gain,allocation.index};return true;
}
} /* namespace libcamera::ipa */
