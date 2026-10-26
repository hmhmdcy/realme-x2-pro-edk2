/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "dynamic_lens_shading.h"
#include "lens_shading.h"
#include <cerrno>
#include <cmath>
#include <utility>
namespace libcamera::ipa::camss {
namespace {constexpr std::array<unsigned,6> triggerSize{2,2,6,1,4,2};}

uint32_t lensShadingTrace(const camss_params_lsc &parameters)
{
 uint32_t value=2166136261u;
 const auto *bytes=reinterpret_cast<const uint8_t*>(&parameters);
 for(unsigned i=0;i<sizeof(parameters);i++)value=(value^bytes[i])*16777619u;
 return value;
}

int DynamicLensShading::readNodes(const ValueNode &value,unsigned level,std::vector<Node> *nodes)
{
 if(level>=triggerSize.size()||!value.isList()||!value.size())return -EINVAL;
 for(const auto &item:value.asList()){
  const auto &trigger=item["trigger"];
  if(!item.isDictionary()||!trigger.isList()||trigger.size()!=triggerSize[level])return -EINVAL;
  Node node;
  for(unsigned i=0;i<trigger.size();i++){
   auto v=trigger[i].get<float>();if(!v||!std::isfinite(*v))return -EINVAL;node.trigger[i]=*v;
  }
  unsigned position=level==2?hdrPosition_:level==4?aecPosition_:0;
  if(level==3){if(node.trigger[0]<0||std::floor(node.trigger[0])!=node.trigger[0])return -EINVAL;}
  else for(unsigned i=0;i<trigger.size();i+=2)if(node.trigger[i]>node.trigger[i+1])return -EINVAL;
  if(!nodes->empty()&&(level==3?nodes->back().trigger[0]>=node.trigger[0]:nodes->back().trigger[position+1]>node.trigger[position]))return -EINVAL;
  int ret=level==5?readLensShadingMesh(item["gains"],&node.gains):readNodes(item["children"],level+1,&node.children);
  if(ret)return ret;
  nodes->push_back(std::move(node));
 }
 return 0;
}

int DynamicLensShading::evaluate(const std::vector<Node> &nodes,unsigned level,float kelvin,float aec,LscMesh *mesh) const
{
 if(nodes.empty()||level>=triggerSize.size())return -EINVAL;
 auto child=[&](const Node &node,LscMesh *result){
  if(level==5){*result=node.gains;return 0;}
  return evaluate(node.children,level+1,kelvin,aec,result);
 };
 if(level==3){for(const auto &node:nodes)if(node.trigger[0]==ledIndex_)return child(node,mesh);return -ENOENT;}
 const float value=level==0?lensPosition_:level==1?drcGain_:level==2?hdrRatio_:level==4?aec:kelvin;
 const unsigned position=level==2?hdrPosition_:level==4?aecPosition_:0;
 for(unsigned i=0;i<nodes.size();i++){
  const auto &first=nodes[i];
  if(value<=first.trigger[position+1]||i+1==nodes.size())return child(first,mesh);
  const auto &second=nodes[i+1];
  if(value<second.trigger[position]){
   LscMesh a,b;int ret=child(first,&a);if(ret)return ret;ret=child(second,&b);if(ret)return ret;
   float weight=float((double(value)-first.trigger[position+1])/(double(second.trigger[position])-first.trigger[position+1]));
   return interpolateLscMesh(a,b,weight,mesh)?0:-ERANGE;
  }
 }
 return -EINVAL;
}

int DynamicLensShading::configure(const ValueNode &tuning,const Size &input,std::optional<DynamicLensShading> *profile)
{
 if(!profile)return -EINVAL;
 profile->reset();if(tuning.isEmpty())return 0;
 const auto mode=tuning["mode"].get<std::string>("static");
 if(mode=="static")return 0;
 if(mode!="dynamic"||!tuning.isDictionary())return -EINVAL;
 if(!tuning["enabled"].isEmpty()){
  auto enabled=tuning["enabled"].get<bool>();if(!enabled)return -EINVAL;if(!*enabled)return 0;
 }
 DynamicLensShading result;result.input_=input;
 int ret=readLensShadingMapping(tuning,&result.mapping_);if(ret)return ret;
 auto aec=tuning["aec_control"].get<std::string>(),hdr=tuning["hdr_control"].get<std::string>();
 if(!aec||!hdr)return -EINVAL;
 if(*aec=="lux_index")result.aecPosition_=0;else if(*aec=="analogue_gain")result.aecPosition_=2;else return -EINVAL;
 if(*hdr=="exposure_time_ratio")result.hdrPosition_=0;else if(*hdr=="sensitivity_ratio")result.hdrPosition_=2;else if(*hdr=="exposure_gain_ratio")result.hdrPosition_=4;else return -EINVAL;
 const auto &reference=tuning["reference_triggers"];
 auto lens=reference["lens_position"].get<float>(),drc=reference["drc_gain"].get<float>(),ratio=reference["hdr_ratio"].get<float>();
 auto led=reference["led_index"].get<unsigned>();
 if(!lens||!drc||!ratio||!led||!std::isfinite(*lens)||!std::isfinite(*drc)||!std::isfinite(*ratio))return -EINVAL;
 result.lensPosition_=*lens;result.drcGain_=*drc;result.hdrRatio_=*ratio;result.ledIndex_=*led;
 ret=result.readNodes(tuning["core"],0,&result.core_);if(ret)return ret;
 // One explicitly paired golden/unit response, matching the retained
 // Default profiles. Additional illuminant bindings are not inferred.
 if(!tuning["golden"].isEmpty()||!tuning["unit"].isEmpty()){
  LscMesh golden,unit,factors;
  if(readLensShadingMesh(tuning["golden"],&golden)||readLensShadingMesh(tuning["unit"],&unit)||!lscCalibrationFactors(golden,unit,&factors))return -EINVAL;
  result.factors_=factors;
 }
 LscMesh check;ret=result.evaluate(result.core_,0,6500,0,&check);if(ret)return ret;
 camss_params_lsc encoded;ret=encodeLensShading(check,input,result.mapping_,&encoded);if(ret)return ret;
 *profile=std::move(result);return 0;
}

int DynamicLensShading::select(std::optional<int32_t> kelvin,const ColourCorrectionInputs *runtime,const DynamicLscState *fallback,DynamicLscState *state) const
{
 if(!state)return -EINVAL;
 auto aec=runtime?(aecPosition_==0?runtime->luxIndex:runtime->analogueGain):std::nullopt;
 if(aec&&!std::isfinite(*aec))return -ERANGE;
 DynamicLscState result;
 if(!kelvin||!aec){
  if(fallback){*state=*fallback;return 0;}
  LscMesh unity;for(auto &channel:unity)channel.fill(1);
  int ret=encodeLensShading(unity,input_,mapping_,&result.parameters);if(ret)return ret;
 }else{
  LscMesh source;int ret=evaluate(core_,0,*kelvin,*aec,&source);if(ret)return ret;
  if(factors_){LscMesh calibrated;if(!lscApplyCalibration(source,*factors_,&calibrated))return -ERANGE;source=calibrated;}
  ret=encodeLensShading(source,input_,mapping_,&result.parameters);if(ret)return ret;
  result.aecValue=aec;result.temperature=kelvin;result.statisticsSof=runtime->statisticsSof;
 }
 *state=result;return 0;
}
} /* namespace libcamera::ipa::camss */
