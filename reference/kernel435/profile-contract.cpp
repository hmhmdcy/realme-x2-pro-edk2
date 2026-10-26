/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ipe_tone_profile.h"
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
 const auto &tuning=(*root)["modes"][0];std::optional<camss_params_ife_gamma> gamma;
 assert(!configureGammaProfile(tuning["gamma"],&gamma)&&gamma);
 std::optional<IpeToneProfile> profile;assert(!IpeToneProfile::configure(tuning["ipe_tone"],&*gamma,&profile)&&profile&&profile->tracksGtm());
 IpeFrameObservation f;f.epoch=1;f.sof=9;f.exposureNs=5004000;f.exposureLines=539;f.gainCode=32;
 f.analogueGain=1;f.exposureIndex=f.luxIndex=200;f.luxValid=f.ifeGammaOverride=true;f.histogram.fill(3888);f.population=3981312;
 IpeToneState history,a,b,c;camss_params_ife_gtm ga{},gb{},gc{};
 assert(!profile->prepareGtm(f,history,&ga,&a)&&ga.enabled==1&&a.tmcHistogramValid&&a.tmcHistogramSof==9);
 assert(!std::memcmp(a.tmcHistogram.data(),f.histogram.data(),sizeof f.histogram));
 float percentage;std::memcpy(&percentage,a.cache.data()+60,4);assert(percentage>0);
 auto dump=[&](unsigned n,const camss_params_ife_gtm &g,const IpeToneState &s){
  std::ofstream adrc(std::string(argv[2])+"-"+std::to_string(n)+"-adrc.bin",std::ios::binary);adrc.write(reinterpret_cast<const char*>(s.cache.data()),s.cache.size());
  std::ofstream lut(std::string(argv[2])+"-"+std::to_string(n)+"-lut.bin",std::ios::binary);
  for(const auto &seg:g.segments){uint32_t pair[2]={seg.base,uint32_t(seg.slope)&0x3ffffff};lut.write(reinterpret_cast<const char*>(pair),8);}assert(adrc.good()&&lut.good());
 };dump(0,ga,a);
 /* Native force-update at identical triggers retains the previous histogram. */
 f.sof=10;f.histogram.fill(0);f.histogram[170]=f.population;
 assert(!profile->prepareGtm(f,a,&gb,&b));assert(b.tmcHistogramSof==9&&b.cache==a.cache&&!std::memcmp(ga.segments,gb.segments,sizeof ga.segments));dump(1,gb,b);
 f.sof=11;f.luxIndex=230;f.analogueGain=2;
 assert(!profile->prepareGtm(f,b,&gc,&c)&&c.tmcHistogramSof==11&&c.cache!=b.cache);dump(2,gc,c);
 /* The image's new statistics select LTM leaves, never regenerate its upstream ADRC. */
 qcom_ipe_a5_frame_params p;IpeToneState next;
 assert(!profile->calculate(f,history,&p,&next,&a));assert(next.cache==a.cache&&next.adrc==a.adrc&&next.tmcHistogramSof==9);
 assert(next.ltmLuxValid&&next.ltmLuxIndex==230&&!history.initialized);
 IpeToneState old=a;auto before=old.cache;f.luxValid=false;camss_params_ife_gtm unchanged=gc;
 assert(profile->prepareGtm(f,old,&gc,&next)==-ENODATA&&!std::memcmp(&gc,&unchanged,sizeof gc)&&old.cache==before);
 std::cout<<"GTM_PROFILE_PASS stock_share_nonzero=1 upstream_immutable=1 native_histogram_hold=1 future_histogram_refresh=1 cases=3\n";
}
