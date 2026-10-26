/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <bit>
#include <cassert>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/videodev2.h>
#include <linux/qcom-camss-config.h>
#include <libcamera/control_ids.h>
#include <libcamera/ipa/camss_ipa_interface.h>
using namespace libcamera;
struct Observation {
 ipa::camss::Statistics result{};ControlList metadata;unsigned calls=0;
 void ready(uint64_t,uint32_t,uint32_t,const ipa::camss::Statistics &s,const ControlList &m){result=s;metadata=m;++calls;}
};
struct Proposal { uint32_t revision,sourceSof,bits;int kelvin;std::string kind;uint32_t parent; };
int main(int argc,char **argv)
{
 assert(argc==10);std::cout<<std::setprecision(9);
 void *handle=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);if(!handle){std::cerr<<dlerror()<<std::endl;return 2;}
 auto create=reinterpret_cast<IPAInterface *(*)()>(dlsym(handle,"ipaCreate"));assert(create);
 std::unique_ptr<ipa::camss::IPACamssInterface> ipa(static_cast<ipa::camss::IPACamssInterface*>(create()));
 const ControlId exposure(V4L2_CID_EXPOSURE,"Exposure","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlId gain(V4L2_CID_ANALOGUE_GAIN,"Gain","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlIdMap ids{{V4L2_CID_EXPOSURE,&exposure},{V4L2_CID_ANALOGUE_GAIN,&gain}};
 const ControlInfoMap sensor({{&exposure,ControlInfo(int32_t(4),int32_t(3332),int32_t(500))},{&gain,ControlInfo(int32_t(32),int32_t(960),int32_t(512))}},ids);
 IPACameraSensorInfo info{};info.model=argv[3];info.bitsPerPixel=10;
 info.outputSize=Size(std::stoul(argv[4]),std::stoul(argv[5]));info.pixelRate=std::stoull(argv[6]);
 info.minLineLength=info.maxLineLength=std::stoul(argv[7]);info.minFrameLength=std::stoul(argv[8]);info.maxFrameLength=65535;
 ControlInfoMap supported;ipa::camss::SensorControlConfiguration configuration{};
 assert(!ipa->init(IPASettings{"",info.model},info,sensor,ControlInfoMap{},"",&supported));
 const int mode=std::stoi(argv[9]);int configured=ipa->configure(info,info.outputSize,sensor,argv[2],&supported,&configuration);
 if(mode<0){assert(configured==mode);std::cout<<"RUNTIME_CCM_REJECT_PASS"<<std::endl;return 0;}
 assert(!configured);const bool enabled=mode!=0,useGain=mode==2;
 assert((supported.find(&controls::ColourCorrectionMatrix)!=supported.end())==enabled);
 std::ifstream file(std::string(argv[2])+".stats",std::ios::binary);std::vector<uint8_t> original((std::istreambuf_iterator<char>(file)),{});assert(original.size()==16424);
 SharedFD fd(memfd_create("runtime-ccm-parameters",MFD_CLOEXEC)),sf(memfd_create("runtime-ccm-statistics",MFD_CLOEXEC));
 assert(!ftruncate(fd.get(),32768)&&!ftruncate(sf.get(),32768));
 auto *parameters=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,fd.get(),0));
 auto *stats=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,sf.get(),0));assert(parameters!=MAP_FAILED&&stats!=MAP_FAILED);
 std::memcpy(stats,original.data(),original.size());
 IPABuffer p(1,{FrameBuffer::Plane{fd,0,32768}}),s(2,{FrameBuffer::Plane{sf,0,32768}});assert(!ipa->mapBuffers({p},{s}));
 Observation observation;ipa->statsProcessed.connect(&observation,&Observation::ready);
 ControlList startControls(controls::controls),translated(sensor),metadata(controls::controls);
 startControls.set(controls::ExposureTimeMode,controls::ExposureTimeModeManual);startControls.set(controls::AnalogueGainMode,controls::AnalogueGainModeManual);
 startControls.set(controls::AwbEnable,false);startControls.set(controls::ColourTemperature,6500);
 uint64_t epoch=1;uint32_t used=0,active=0,sof=0,lastSource=0,lastBits=0;unsigned packets=0,noops=0;int kelvin=6500;
 std::optional<Proposal> pending;bool prepared=false;std::array<float,9> current{};
 auto matrix=[&](uint32_t sequence){
  assert(!ipa->frameMetadata(epoch,sequence,ipa::camss::SensorContext{true,500,512,0},&metadata));
  auto m=metadata.get(controls::ColourCorrectionMatrix);assert(bool(m)==enabled);std::array<float,9> result{};
  if(m)std::copy(m->begin(),m->end(),result.begin());
  return result;
 };
 auto dump=[&](const Proposal &proposal){
  std::cout<<"CCM_PACKET {\"epoch\":"<<epoch<<",\"revision\":"<<proposal.revision<<",\"source_sof\":"<<proposal.sourceSof
   <<",\"bits\":"<<proposal.bits<<",\"kind\":\""<<proposal.kind<<"\",\"kelvin\":"<<proposal.kelvin<<",\"parent\":"<<proposal.parent<<",\"packet\":\"";
  static const char hex[]="0123456789abcdef";for(unsigned i=0;i<used;i++)std::cout<<hex[parameters[i]>>4]<<hex[parameters[i]&15];
  std::cout<<"\",\"matrix\":[";for(unsigned i=0;i<9;i++)std::cout<<(i?",":"")<<current[i];std::cout<<"]}"<<std::endl;++packets;
 };
 auto start=[&](){
  assert(!ipa->start(epoch,startControls,&translated));assert(!ipa->prepareParameters(epoch,1,0,&used));assert(used==(enabled?96u:56u));
  ipa->parametersApplied(epoch,2,0);current=matrix(2);active=0;dump({0,0,0,6500,"unity",0});
 };start();
 auto process=[&](uint32_t sequence,uint32_t lines,uint32_t code,bool wantCurrent=true){
  unsigned calls=observation.calls;ipa->processStats(epoch,sequence,2,original.size(),ipa::camss::SensorContext{true,lines,code,0});
  assert(observation.calls==calls+1&&!observation.result.status);
  if(pending || !wantCurrent)assert(!observation.result.ispUpdate.valid);
  if(wantCurrent){
   lastSource=sequence;lastBits=std::bit_cast<uint32_t>(useGain?*observation.metadata.get(controls::AnalogueGain):observation.result.luxIndex);
   auto m=observation.metadata.get(controls::ColourCorrectionMatrix);assert(bool(m)==enabled);
   if(m)assert(!std::memcmp(m->data(),current.data(),36));
  }
  if(observation.result.ispUpdate.valid){assert(enabled&&!pending);pending=Proposal{observation.result.ispUpdate.revision,sequence,lastBits,kelvin,"tree",active};}
  else if(!pending&&enabled)++noops;
  return observation.result.luxIndex;
 };
 auto prepare=[&](){assert(pending&&!prepared);assert(!ipa->prepareParameters(epoch,1,pending->revision,&used));assert(used==96);prepared=true;};
 auto acknowledge=[&](uint32_t first){
  assert(pending&&prepared);assert(matrix(first-1)==current);ipa->parametersApplied(epoch,first,pending->revision);
  assert(matrix(first-1)==current);current=matrix(first);dump(*pending);active=pending->revision;pending.reset();prepared=false;
 };
 process(2,100,32);if(enabled)assert(pending);
 process(3,800,512); // Change the AEC input before prepareParameters().
 if(pending){prepare();std::array<uint8_t,96> before;std::copy(parameters,parameters+96,before.begin());process(4,3000,900);assert(!std::memcmp(before.data(),parameters,96));acknowledge(6);}
 process(5,500,512,false); // Historical SOF cannot propose against a future acknowledgement.
 process(6,3000,900);if(pending){prepare();process(7,100,32);acknowledge(9);}
 float previous=-1;bool converged=false;
 for(sof=9;sof<73;sof++){
  float value=process(sof,3000,900);
  if(pending){prepare();acknowledge(sof+1);}
  if(value==previous){converged=true;break;}previous=value;
 }
 assert(converged);
 if(enabled){
  const std::array<float,9> manual{0,0,1,0,.75f,0,1,0,0};
  auto request=[&](const ControlList &controls,const std::string &kind){
   ipa::camss::AutoIspUpdate update{};assert(!ipa->applyIspControls(epoch,controls,&update)&&update.valid);
   pending=Proposal{update.revision,lastSource,lastBits,kelvin,kind,active};
  };
  ControlList change(controls::controls);change.set(controls::ColourCorrectionMatrix,Span<const float,9>(manual));request(change,"manual");prepare();acknowledge(++sof);
  process(sof,100,32);assert(!pending);process(++sof,3000,900);assert(!pending);
  change.clear();change.set(controls::ColourTemperature,2850);kelvin=2850;request(change,"tree");
  process(++sof,100,32);prepare();acknowledge(sof+2);sof+=2;
  // Undefined CCT retains the applied matrix, including its old offsets.
  change.clear();change.set(controls::ColourGains,{0.f,0.f});request(change,"fallback");prepare();acknowledge(++sof);
  process(sof,3000,900);assert(!pending);assert(!observation.metadata.get(controls::ColourTemperature));
  change.clear();change.set(controls::ColourTemperature,6500);kelvin=6500;request(change,"tree");prepare();acknowledge(++sof);
  assert(noops);
 }
 ipa->stop();++epoch;start();ipa->stop();ipa->unmapBuffers({1,2});ipa.reset();dlclose(handle);
 std::cout<<"RUNTIME_CCM_CONTRACT_PASS packets="<<packets<<" quantized-noops="<<noops<<std::endl;
}
