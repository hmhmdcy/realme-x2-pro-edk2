/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Compile separately against baseline/new headers and archives, never mix ABI. */
#include <array>
#include <cassert>
#include <cmath>
#include <fstream>
#include <libcamera/base/file.h>
#include <libcamera/control_ids.h>
#include "libcamera/internal/yaml_parser.h"
#include "agc_mean_luminance.h"
using namespace libcamera;
class Controller : public ipa::AgcMeanLuminance {
public:
 unsigned int bin=256;
private:
 double estimateLuminance(double gain) const override {return std::min(1.,(bin+.5)/1024*gain);}
};
int main(int argc,char **argv)
{
 assert(argc==10);File file(argv[1]);assert(file.open(File::OpenModeFlag::ReadOnly));auto tuning=YamlParser::parse(file);assert(tuning);
 auto helper=ipa::CameraSensorHelperFactoryBase::create(argv[2]);assert(helper);Controller controller;
 assert(!controller.parseTuningData((*tuning)["modes"][0]["agc"]));
 double lineUs=std::stod(argv[3]);int minLines=std::stoi(argv[4]),maxLines=std::stoi(argv[5]);
 double minGain=helper->gain(std::stoul(argv[6])),maxGain=helper->gain(std::stoul(argv[7]));
 controller.configure(std::chrono::duration<double,std::micro>(lineUs),helper.get());
 controller.setLimits(std::chrono::duration<double,std::micro>(minLines*lineUs),std::chrono::duration<double,std::micro>(maxLines*lineUs),minGain,maxGain,{});
 std::ofstream output(argv[8],std::ios::binary);assert(output);unsigned int frames=std::stoul(argv[9]);
 for(unsigned int frame=0;frame<frames;++frame) {
  if(frame==frames/2)controller.resetFrameCount();
  controller.bin=std::array<unsigned int,8>{0,1,63,256,511,768,1000,1023}[(frame/3)%8];
  controller.setExposureCompensation(std::exp2(int(frame/8)%5-2));
  std::array<uint32_t,1024> bins{};bins[controller.bin]=10000;
  double exposure=frame==0?0:std::array<double,6>{.1,100,5000,20000,100000,1000000}[frame%6];
  auto [time,gain,q,digital]=controller.calculateNewEv(controls::ConstraintNormal,controls::ExposureNormal,ipa::Histogram(bins),std::chrono::duration<double,std::micro>(exposure));
  std::array<double,4> values{std::chrono::duration<double,std::micro>(time).count(),gain,q,digital};
  output.write(reinterpret_cast<const char*>(values.data()),sizeof(values));
 }
}
