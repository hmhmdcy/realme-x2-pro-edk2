/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ipe_tone_profile.h"
#include "gamma_profile.h"
#include <libcamera/base/file.h>
#include "libcamera/internal/yaml_parser.h"
#include <cassert>
#include <cstring>
#include <iostream>
using namespace libcamera;
using namespace libcamera::ipa::camss;
int main(int argc,char **argv)
{
 assert(argc==2);File file(argv[1]);assert(file.open(File::OpenModeFlag::ReadOnly));auto root=YamlParser::parse(file);assert(root);
 const auto &tuning=(*root)["modes"][0];std::optional<camss_params_ife_gamma> gamma;
 assert(!configureGammaProfile(tuning["gamma"],&gamma)&&gamma);
 std::optional<IpeToneProfile> profile;assert(!IpeToneProfile::configure(tuning["ipe_tone"],&*gamma,&profile)&&profile);
 IpeFrameObservation frame;frame.epoch=1;frame.sof=9;frame.exposureNs=5004000;frame.exposureLines=539;frame.gainCode=32;
 frame.analogueGain=1;frame.exposureIndex=200;frame.luxIndex=200;frame.luxValid=true;frame.ifeGammaOverride=true;
 frame.histogram.fill(3888);frame.population=3981312;
 IpeToneState history;history.ltmLuxValid=true;history.ltmLuxIndex=200;
 unsigned char before[sizeof history];std::memcpy(before,&history,sizeof history);
 qcom_ipe_a5_frame_params first,second,third;IpeToneState a,b,c;
 assert(!profile->calculate(frame,history,&first,&a));frame.exposureIndex=400;
 assert(!profile->calculate(frame,history,&second,&b));unsigned changed=0;
 for(size_t i=0;i<sizeof first;++i)changed+=reinterpret_cast<unsigned char*>(&first)[i]!=reinterpret_cast<unsigned char*>(&second)[i];
 std::cerr<<"PHYSICAL_INDEX_DIFFERENCE bytes="<<changed<<std::endl;assert(!changed);
 assert(a.ltmLuxValid&&b.ltmLuxValid&&a.ltmLuxIndex==200&&b.ltmLuxIndex==200);
 uint32_t gtmEnabled;float gtmFraction;std::memcpy(&gtmEnabled,b.cache.data()+8,4);std::memcpy(&gtmFraction,b.cache.data()+60,4);
 assert(gtmEnabled<=1&&std::isfinite(gtmFraction)&&gtmFraction>=0&&gtmFraction<=1);
 std::cout<<"TMC_GTM_SPLIT enabled="<<gtmEnabled<<" nonzero-fraction="<<(gtmFraction>0)<<std::endl;
 assert(!std::memcmp(before,&history,sizeof history));
 frame.luxIndex=230;assert(!profile->calculate(frame,history,&third,&c));assert(c.ltmLuxIndex==230);
 IpeToneState settled=history;settled.ltmLuxIndex=230;assert(!profile->calculate(frame,settled,&second,&b));
 unsigned attenuationChanged=0;
 for(size_t i=0;i<sizeof second.ltm;++i)attenuationChanged+=reinterpret_cast<unsigned char*>(&second.ltm)[i]!=reinterpret_cast<unsigned char*>(&third.ltm)[i];
 std::cerr<<"LUX_HISTORY_DIFFERENCE bytes="<<attenuationChanged<<std::endl;assert(attenuationChanged>0);
 settled.ltmLuxValid=false;settled.ltmLuxIndex=-1000;assert(!profile->calculate(frame,settled,&first,&a));
 assert(!std::memcmp(&first,&second,sizeof first)&&a.ltmLuxIndex==230);
 frame.luxValid=false;std::memset(&first,0xa7,sizeof first);unsigned char outputBefore[sizeof first];std::memcpy(outputBefore,&first,sizeof first);
 assert(profile->calculate(frame,history,&first,&a)==-ENODATA&&!std::memcmp(outputBefore,&first,sizeof first));
 std::cout<<"PROFILE_DOMAIN_CONTRACT passed=1 physical_index_independent=1 lux_history_changes_ltm=1 first_history_no_attenuation=1 input_preserved=1"<<std::endl;
}
