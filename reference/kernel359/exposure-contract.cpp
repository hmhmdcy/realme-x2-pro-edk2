/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Real AArch64 IPA + OEM-instruction allocation reference, no device emulation. */
#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <cerrno>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <limits>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/videodev2.h>
#include <linux/qcom-camss-config.h>
#include <libcamera/camera_manager.h>
#include <libcamera/control_ids.h>
#include <libcamera/base/event_dispatcher.h>
#include <libcamera/base/file.h>
#include <libcamera/base/object.h>
#include <libcamera/base/thread.h>
#include <libcamera/base/timer.h>
#include <libcamera/ipa/camss_ipa_interface.h>
#include <libcamera/ipa/camss_ipa_proxy.h>
#include "libcamera/internal/ipa_module.h"
#include "libcamera/internal/yaml_parser.h"
#include "exposure_program.h"
#include "../libipa/exposure_mode_helper.h"
using namespace libcamera;
struct Observation : Object {
 unsigned int calls=0;
 ipa::camss::Statistics result{};
 ControlList metadata;
 void ready(uint64_t,uint32_t,uint32_t,const ipa::camss::Statistics &s,const ControlList &m)
 {++calls;result=s;metadata=m;Thread::current()->eventDispatcher()->interrupt();}
};
struct Case {
 unsigned int ordinal;float ev;int32_t mode,period;uint32_t lines,code,bin;
 double target;float gain;uint64_t time;float index;
};
int main(int argc,char **argv)
{
 assert(argc==16);
 const std::string model=argv[4];
 const uint32_t width=std::stoul(argv[5]),height=std::stoul(argv[6]),rate=std::stoul(argv[7]),lineLength=std::stoul(argv[8]),frameLength=std::stoul(argv[9]);
 const int32_t minLines=std::stoi(argv[10]),maxLines=std::stoi(argv[11]),minCode=std::stoi(argv[12]),maxCode=std::stoi(argv[13]);
 CameraManager manager;
 void *handle=nullptr;
 std::unique_ptr<ipa::camss::IPACamssInterface> module;
 std::unique_ptr<IPAModule> description;
 if(std::string(argv[2])=="direct") {
  handle=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);if(!handle){std::cerr<<dlerror()<<std::endl;return 2;}
  auto create=reinterpret_cast<IPAInterface *(*)()>(dlsym(handle,"ipaCreate"));assert(create);
  module.reset(static_cast<ipa::camss::IPACamssInterface*>(create()));
 } else {
  description=std::make_unique<IPAModule>(argv[1]);assert(description->isValid());
  assert(description->info().pipelineVersion==1);
  if(std::string(argv[2])=="isolated") module=std::make_unique<ipa::camss::IPAProxyCamssIsolated>(description.get(),manager);
  else module=std::make_unique<ipa::camss::IPAProxyCamssThreaded>(description.get(),manager);
  assert(static_cast<ipa::camss::IPAProxyCamss*>(module.get())->isValid());
 }
 auto helper=ipa::CameraSensorHelperFactoryBase::create(model);assert(helper);
 const double lineUs=double(lineLength)*1000000/rate,minGain=helper->gain(minCode),maxGain=helper->gain(maxCode);
 const ControlId exposure(V4L2_CID_EXPOSURE,"Exposure","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlId gain(V4L2_CID_ANALOGUE_GAIN,"Gain","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlId vblank(V4L2_CID_VBLANK,"VBlank","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlIdMap ids{{V4L2_CID_EXPOSURE,&exposure},{V4L2_CID_ANALOGUE_GAIN,&gain},{V4L2_CID_VBLANK,&vblank}};
 const ControlInfoMap sensor({{&exposure,ControlInfo(minLines,maxLines,int32_t(500))},
  {&gain,ControlInfo(minCode,maxCode,minCode)},{&vblank,ControlInfo(int32_t(frameLength-height),int32_t(65535-height),int32_t(frameLength-height))}},ids);
 IPACameraSensorInfo info{};info.model=model;info.outputSize=Size(width,height);info.bitsPerPixel=10;
 info.pixelRate=rate;info.minLineLength=info.maxLineLength=lineLength;info.minFrameLength=frameLength;info.maxFrameLength=65535;
 ControlInfoMap supported;ipa::camss::SensorControlConfiguration configuration{};ControlInfoMap lens;
 assert(!module->init(IPASettings{"",model},info,sensor,lens,"",&supported));
 assert(!module->configure(info,info.outputSize,sensor,argv[15],&supported,&configuration)); // Complete calibration profile also parses.
 assert(!module->configure(info,info.outputSize,sensor,argv[3],&supported,&configuration));
 assert(supported.count(&controls::ExposureValue)&&supported.count(&controls::AeFlickerMode)&&supported.count(&controls::AeFlickerPeriod));
 File file(argv[3]);assert(file.open(File::OpenModeFlag::ReadOnly));auto tuning=YamlParser::parse(file);assert(tuning);
 std::optional<ipa::camss::ExposureProgram> program;
 assert(!ipa::camss::ExposureProgram::configure((*tuning)["modes"][0]["exposure_program"],std::llround(minLines*lineUs*1000),std::llround(maxLines*lineUs*1000),std::llround(frameLength*lineUs*1000),minGain,&program)&&program);
 std::ifstream input(argv[14]);assert(input);std::vector<Case> cases;Case c;
 while(input>>c.ordinal>>c.ev>>c.mode>>c.period>>c.lines>>c.code>>c.bin>>c.target>>c.gain>>c.time>>c.index)cases.push_back(c);
 assert(cases.size()==6);
 SharedFD parameterFd(memfd_create("parameters",MFD_CLOEXEC)),statisticsFd(memfd_create("statistics",MFD_CLOEXEC));
 assert(!ftruncate(parameterFd.get(),32768)&&!ftruncate(statisticsFd.get(),32768));
 auto *memory=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,statisticsFd.get(),0));assert(memory!=MAP_FAILED);
 const IPABuffer parameterBuffer(1,{FrameBuffer::Plane{parameterFd,0,32768}});
 const IPABuffer statisticsBuffer(2,{FrameBuffer::Plane{statisticsFd,0,32768}});
 const std::vector<IPABuffer> parameterBuffers{parameterBuffer},statisticsBuffers{statisticsBuffer};
 assert(!module->mapBuffers(parameterBuffers,statisticsBuffers));
 auto *envelope=reinterpret_cast<v4l2_isp_buffer*>(memory);auto *hist=reinterpret_cast<camss_stats_bhist*>(memory+sizeof(*envelope));
 constexpr uint32_t statsBytes=sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist);
 std::memset(memory,0,32768);envelope->version=V4L2_ISP_VERSION_V1;envelope->data_size=sizeof(*hist);hist->header={CAMSS_STATS_AEC_BHIST,0,sizeof(*hist)};
 Observation observation;module->statsProcessed.connect(&observation,&Observation::ready);
 uint64_t epoch=0;uint32_t bytes;ControlList output(sensor);
 auto acknowledge=[&](uint32_t sof) {
  std::memset(hist->bins,0,sizeof(hist->bins));hist->bins[256]=uint64_t(width)*height/4;
  unsigned int before=observation.calls;module->processStats(epoch,sof,2,statsBytes,{});
  Timer deadline;deadline.start(std::chrono::milliseconds(3000));
  while(observation.calls==before&&deadline.isRunning())Thread::current()->eventDispatcher()->processEvents();
  deadline.stop();assert(observation.calls==before+1&&!observation.result.status);
 };
 auto start=[&](const ControlList &settings) {
  assert(!module->start(++epoch,settings,&output));assert(!module->prepareParameters(epoch,1,0,&bytes));module->parametersApplied(epoch,0,0);
  // parametersApplied is asynchronous. Its following stats reply establishes
  // completion before any synchronous calls, without advancing AE filtering.
  acknowledge(0);
 };
 auto settings=[&](const Case &test) {
  ControlList values(controls::controls);values.set(controls::ExposureTimeMode,controls::ExposureTimeModeAuto);values.set(controls::AnalogueGainMode,controls::AnalogueGainModeAuto);values.set(controls::AwbEnable,false);
  values.set(controls::ExposureValue,test.ev);values.set(controls::AeFlickerMode,test.mode);values.set(controls::AeFlickerPeriod,test.period);return values;
 };
 auto metadata=[&](uint32_t sof,const Case &test,float ev,int mode,int period) {
  ControlList values(controls::controls);assert(!module->frameMetadata(epoch,sof,{true,test.lines,test.code,0},&values));
  assert(values.get(controls::ExposureValue).value_or(100)==ev);assert(values.get(controls::AeFlickerMode).value_or(-1)==mode);assert(values.get(controls::AeFlickerPeriod).value_or(-1)==period);
  assert(values.get(controls::ExposureTime).value_or(0)==std::lround(test.lines*lineUs));return values;
 };
 auto expected=[&](const Case &test) {
  std::array<std::pair<utils::Duration,double>,1> stages{{{std::chrono::duration<double,std::nano>(test.time),test.gain}}};
  ipa::ExposureModeHelper quantizer(stages);quantizer.configure(std::chrono::duration<double,std::micro>(lineUs),helper.get());
  quantizer.setLimits(std::chrono::duration<double,std::micro>(minLines*lineUs),std::chrono::duration<double,std::micro>(maxLines*lineUs),minGain,maxGain);
  auto [time,analogue,q,digital]=quantizer.splitExposure(std::chrono::duration<double,std::nano>(double(test.time)*test.gain));(void)q;(void)digital;
  return std::pair<uint32_t,uint32_t>{std::clamp<int64_t>(std::llround(std::chrono::duration<double,std::micro>(time).count()/lineUs),minLines,maxLines),std::clamp(helper->gainCode(std::clamp(analogue,minGain,maxGain)),uint32_t(minCode),uint32_t(maxCode))};
 };
 auto process=[&](uint32_t sof,const Case &test) {
  std::memset(hist->bins,0,sizeof(hist->bins));hist->bins[test.bin]=uint64_t(width)*height/4;
  unsigned int before=observation.calls;module->processStats(epoch,sof,2,statsBytes,{true,test.lines,test.code,0});
  Timer deadline;deadline.start(std::chrono::milliseconds(3000));
  while(observation.calls==before&&deadline.isRunning())Thread::current()->eventDispatcher()->processEvents();
  deadline.stop();
  if(observation.calls!=before+1||observation.result.status||!observation.result.parametersKnown||!observation.result.sensorControlsKnown){std::cerr<<"stats failure case="<<test.ordinal<<" calls="<<observation.calls-before<<" status="<<observation.result.status<<" parameters="<<observation.result.parametersKnown<<" sensor="<<observation.result.sensorControlsKnown<<std::endl;std::abort();}
  assert(observation.metadata.get(controls::ExposureValue).value_or(100)==test.ev);
  assert(observation.metadata.get(controls::AeFlickerMode).value_or(-1)==test.mode);
  assert(observation.metadata.get(controls::AeFlickerPeriod).value_or(-1)==test.period);
  auto [lines,code]=expected(test);auto update=observation.result.automaticUpdate;
  if(lines==test.lines&&code==test.code)assert(!update.valid);
  else if(!update.valid||update.exposureLines!=lines||update.gainCode!=code){std::cerr<<"allocation mismatch case="<<test.ordinal<<" expected="<<lines<<","<<code<<" actual="<<update.valid<<","<<update.exposureLines<<","<<update.gainCode<<std::endl;std::abort();}
  assert(lines>=uint32_t(minLines)&&lines<=uint32_t(maxLines)&&code>=uint32_t(minCode)&&code<=uint32_t(maxCode));
 };
 for(const auto &test:cases) {
  assert(program->adjust(test.ev));ipa::AecExposureAllocation allocation{};
  assert(program->allocate(test.target,test.mode?uint64_t(test.period)*1000:0,&allocation));
  if(allocation.exposureTimeNs!=test.time||std::bit_cast<uint32_t>(allocation.gain)!=std::bit_cast<uint32_t>(test.gain)||std::bit_cast<uint32_t>(allocation.index)!=std::bit_cast<uint32_t>(test.index)){
   std::cerr<<"native mismatch case="<<test.ordinal<<" time="<<allocation.exposureTimeNs<<" expected="<<test.time<<" gain="<<std::hex<<std::bit_cast<uint32_t>(allocation.gain)<<" expected="<<std::bit_cast<uint32_t>(test.gain)<<std::endl;std::abort();}
  start(settings(test));process(4,test);metadata(4,test,test.ev,test.mode,test.period);module->stop();
 }
 // Pending requests cannot relabel or calculate an earlier frame with a later EV.
 for(unsigned int which:{0U,1U}) {
  start(settings(cases[0]));ControlList request(controls::controls);request.set(controls::ExposureValue,1.f);request.set(controls::AeFlickerMode,controls::FlickerManual);request.set(controls::AeFlickerPeriod,10000);
  ControlList converted(sensor);assert(!module->convertControls(epoch,request,&converted)&&converted.empty());metadata(12,cases[0],0,0,0);
  ipa::camss::AutoIspUpdate update{};assert(!module->applyIspControls(epoch,10,request,&update)&&!update.valid);
  metadata(9,cases[0],0,0,0);metadata(10,cases[0],1,1,10000);
  process(which?10:4,cases[which]);
  assert(module->applyIspControls(epoch,9,request,&update)==-ESTALE);
  request.set(controls::ExposureValue,std::numeric_limits<float>::quiet_NaN());assert(module->applyIspControls(epoch,11,request,&update)==-ERANGE);
  request.clear();request.set(controls::ExposureValue.id(),ControlValue(int32_t(1)));assert(module->applyIspControls(epoch,11,request,&update)==-EINVAL);
  request.clear();request.set(controls::AeFlickerMode,controls::FlickerAuto);assert(module->applyIspControls(epoch,11,request,&update)==-ENOTSUP);
  request.clear();request.set(controls::ExposureValue,-1.f);request.set(controls::AeFlickerPeriod,-1);assert(module->applyIspControls(epoch,11,request,&update)==-ERANGE);metadata(11,cases[0],1,1,10000);
  request.clear();request.set(controls::AeFlickerMode,controls::FlickerOff);assert(!module->applyIspControls(epoch,12,request,&update)&&!update.valid);metadata(12,cases[0],1,0,10000);
  assert(module->applyIspControls(epoch-1,13,request,&update)==-ESTALE);
  module->stop();
 }
 // A restart without controls clears the prior policy. Combined WB+EV retains
 // WB acknowledgement while the algorithm policy uses its explicit SOF.
 ControlList defaults(controls::controls);defaults.set(controls::AwbEnable,false);start(defaults);metadata(1,cases[0],0,0,0);
 ControlList request(controls::controls);request.set(controls::ExposureValue,-1.f);request.set(controls::ColourGains,{1.25f,.75f});
 ipa::camss::AutoIspUpdate update{};assert(!module->applyIspControls(epoch,5,request,&update)&&update.valid&&update.revision==1);
 auto before=metadata(4,cases[0],0,0,0);assert((*before.get(controls::ColourGains))[0]==1.f);
 assert(!module->prepareParameters(epoch,1,update.revision,&bytes));module->parametersApplied(epoch,7,update.revision);
 acknowledge(1);
 before=metadata(6,cases[0],-1,0,0);assert((*before.get(controls::ColourGains))[0]==1.f);
 auto after=metadata(7,cases[0],-1,0,0);assert((*after.get(controls::ColourGains))[0]==1.25f);
 module->stop();
 std::string legacy=argv[3];legacy.resize(legacy.size()-5);legacy+="-legacy.yaml";
 assert(!module->configure(info,info.outputSize,sensor,legacy,&supported,&configuration));
 assert(supported.count(&controls::ExposureValue)&&!supported.count(&controls::AeFlickerMode)&&!supported.count(&controls::AeFlickerPeriod));
 start(defaults);ControlList fallback(controls::controls);assert(!module->frameMetadata(epoch,1,{true,cases[0].lines,cases[0].code,0},&fallback));
 assert(fallback.get(controls::ExposureValue).value_or(100)==0&&!fallback.get(controls::AeFlickerMode));
 request.clear();request.set(controls::AeFlickerMode,controls::FlickerManual);assert(module->applyIspControls(epoch,2,request,&update)==-ENOTSUP);
 request.clear();request.set(controls::ExposureValue,1.f);assert(!module->applyIspControls(epoch,2,request,&update)&&!update.valid);
 module->stop();module->unmapBuffers({1,2});module.reset();if(handle)dlclose(handle);munmap(memory,32768);
 std::cout<<"EXPOSURE_CONTRACT_PASS native="<<cases.size()<<" policy_history=2 transport="<<argv[2]<<std::endl;
}
