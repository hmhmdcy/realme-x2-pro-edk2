/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ipe_tone_profile.h"
#include "ipe_numeric_history.h"
#include "gamma_profile.h"
#include <libcamera/base/file.h>
#include "libcamera/internal/yaml_parser.h"
#include <cassert>
#include <cstring>
#include <fstream>
#include <iostream>
using namespace libcamera;
using namespace libcamera::ipa::camss;
int main(int argc,char **argv)
{
 assert(argc==3);File file(argv[1]);assert(file.open(File::OpenModeFlag::ReadOnly));auto root=YamlParser::parse(file);assert(root);
 const ValueNode *tuning=nullptr;
 for(const auto &mode:(*root)["modes"].asList())if(mode["match"]["width"].get<unsigned>()==2304)tuning=&mode;
 assert(tuning);std::optional<camss_params_ife_gamma> gamma;assert(!configureGammaProfile((*tuning)["gamma"],&gamma)&&gamma);
 std::optional<IpeToneProfile> profile;assert(!IpeToneProfile::configure((*tuning)["ipe_tone"],&*gamma,&profile)&&profile&&profile->tracksGtm()&&profile->colourCorrection());
 IpeFrameObservation f;f.epoch=1;f.sof=9;f.exposureNs=5004000;f.exposureLines=539;f.gainCode=32;
 f.analogueGain=1;f.exposureIndex=f.luxIndex=100;f.luxValid=f.ifeGammaOverride=true;f.histogram.fill(3888);f.population=3981312;f.colourTemperature=3000;
 IpeFrameHistory observations;assert(observations.start(1));uint64_t token=0;assert(!observations.prepare(f,&token));
 f.colourTemperature=8000;assert(observations.pending(token)->colourTemperature==3000);f=*observations.pending(token);
 IpeToneState empty,next,applied;camss_params_ife_gtm gtm{};
 assert(!profile->prepareGtm(f,empty,&gtm,&applied)&&!gtm.enabled);
 for(const auto &s:gtm.segments)assert(!s.base&&!s.slope);
 assert(!applied.tmcHistogramValid);
 qcom_ipe_a5_frame_params packet;
 assert(!profile->bootstrap(&packet,&f,&empty));assert(packet.flags==0&&packet.colour.modules==7&&!empty.colourCorrection);
 IpeNumericHistory<IpeToneState> history;assert(history.start(1));
 std::ofstream output(argv[2],std::ios::binary);
 const int temperature[]={3000,5750,8000};const float lux[]={100,160,250},gain[]={1,1.5,4};
 for(unsigned i=0;i<3;++i){
  f.sof=9+i;f.colourTemperature=temperature[i];f.exposureIndex=f.luxIndex=lux[i];f.analogueGain=gain[i];
  assert(!profile->calculate(f,history.state(),&packet,&next,&applied));
  assert(packet.flags==3&&packet.colour.modules==7&&next.colourCorrection);
  assert(next.colourCorrection->temperature==f.colourTemperature&&next.colourCorrection->statisticsSof==f.sof);
  assert(next.cache==applied.cache&&!next.tmcHistogramValid);
  output.write(reinterpret_cast<const char*>(&next.colourCorrection->floating),48);
  output.write(reinterpret_cast<const char*>(&next.colourCorrection->quantized),28);
  output.write(reinterpret_cast<const char*>(next.colourCorrection->effective.data()),36);
  assert(!history.prepare(1,f.sof,10+i,history.revision(),next));
  if(i==0){assert(!history.resolve(1,f.sof,10+i,false));assert(!history.state().colourCorrection);}
  else {assert(history.resolve(1,f.sof,10+i,true)==1);assert(history.state().colourCorrection->temperature==f.colourTemperature);}
 }
 assert(output.good());output.close();
 // Missing chromaticity holds only the last successful colour program.
 f.sof=12;f.colourTemperature.reset();IpeToneState held;
 assert(!profile->calculate(f,history.state(),&packet,&held,&applied));
 assert(held.colourCorrection->temperature==8000&&held.colourCorrection->statisticsSof==11);
 assert(!profile->calculate(f,empty,&packet,&held,&applied));
 assert(!held.colourCorrection->temperature&&!held.colourCorrection->statisticsSof);
 for(unsigned i=0;i<9;++i)assert(packet.colour.cc.matrix[i]==(i%4==0?128:0));
 // A manual matrix is owned by the observation, then quantized in IPE.
 f.sof=13;f.manualColourMatrix=std::array<float,9>{0,0,1,0,1,0,1,0,0};
 assert(!profile->calculate(f,history.state(),&packet,&held,&applied));
 assert(packet.colour.cc.matrix[2]==128&&packet.colour.cc.matrix[6]==128&&!packet.colour.cc.matrix[0]);
 assert(history.state().colourCorrection->temperature==8000);
 qcom_ipe_a5_frame_params sentinel;std::memset(&sentinel,0xa7,sizeof sentinel);packet=sentinel;
 f.manualColourMatrix->at(0)=16;
 assert(profile->calculate(f,history.state(),&packet,&held,&applied)==-ERANGE);
 assert(!std::memcmp(&packet,&sentinel,sizeof packet));
 history.stop();assert(history.start(2)&&!history.state().colourCorrection);
 std::cout<<"FRONT_PROFILE_PASS disabled_gtm_tmc=1 ccm_same_sof=1 failed_history_discarded=1 unknown_cct_hold_unity=1 manual=1 restart=1 cases=3\n";
}
