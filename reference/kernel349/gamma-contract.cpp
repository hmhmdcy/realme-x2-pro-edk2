/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <cassert>
#include <cerrno>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/videodev2.h>
#include <linux/qcom-camss-config.h>
#include <libcamera/control_ids.h>
#include <libcamera/ipa/camss_ipa_interface.h>
using namespace libcamera;
int main(int argc,char **argv)
{
 assert(argc==13);
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
 int result=std::stoi(argv[9]);bool gamma=std::stoi(argv[10]);
 int configured=ipa->configure(info,info.outputSize,sensor,argv[2],&supported,&configuration);
 if(result){assert(configured==result);std::cout<<"GAMMA_CONFIG_REJECT_PASS"<<std::endl;return 0;}
 assert(!configured);
 std::vector<uint8_t> expected;
 if(gamma){std::ifstream file(argv[11],std::ios::binary);expected={std::istreambuf_iterator<char>(file),{}};assert(expected.size()==776);}
 SharedFD fd(memfd_create("gamma-parameters",MFD_CLOEXEC));assert(!ftruncate(fd.get(),32768));
 auto *memory=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,fd.get(),0));assert(memory!=MAP_FAILED);
 if(gamma){IPABuffer shortBuffer(2,{FrameBuffer::Plane{fd,0,56}});assert(ipa->mapBuffers({shortBuffer},{})==-ENOSPC);}
 IPABuffer buffer(1,{FrameBuffer::Plane{fd,0,32768}});assert(!ipa->mapBuffers({buffer},{}));
 ControlList start(controls::controls),translated(sensor),metadata(controls::controls);
 start.set(controls::ExposureTimeMode,controls::ExposureTimeModeManual);start.set(controls::AnalogueGainMode,controls::AnalogueGainModeManual);start.set(controls::AwbEnable,false);
 uint32_t used=0;unsigned packets=0,gammaPackets=0;uint64_t epoch=0;
 auto packet=[&](bool wantGamma){
  auto *envelope=reinterpret_cast<const v4l2_isp_buffer *>(memory);assert(envelope->version==1&&envelope->data_size+sizeof(*envelope)==used);
  unsigned offset=sizeof(*envelope),found=0;
  while(offset<used){
   auto *header=reinterpret_cast<const v4l2_isp_params_block_header *>(memory+offset);assert(header->size>=8&&header->size%8==0&&offset+header->size<=used&&header->flags==2);
   if(header->type==CAMSS_PARAMS_IFE_GAMMA){assert(header->size==776&&wantGamma);assert(!std::memcmp(header,expected.data(),776));++found;}
   offset+=header->size;
  }
  assert(offset==used&&found==unsigned(wantGamma));++packets;gammaPackets+=found;
 };
 for(unsigned restart=0;restart<2;restart++){
  ++epoch;assert(!ipa->start(epoch,start,&translated));assert(!ipa->prepareParameters(epoch,1,0,&used));packet(gamma);
  assert(ipa->frameMetadata(epoch,1,ipa::camss::SensorContext{true,500,512,0},&metadata)==-ENODATA);
  ipa->parametersApplied(epoch,2,0);
  assert(!ipa->frameMetadata(epoch,2,ipa::camss::SensorContext{true,500,512,0},&metadata));
  auto old=metadata.get(controls::ColourGains);assert(old);std::array<float,2> oldGains{(*old)[0],(*old)[1]};
  ControlList change(controls::controls);const std::array<float,2> gains{1.25f,.75f};change.set(controls::ColourGains,Span<const float,2>(gains));
  ipa::camss::AutoIspUpdate update{};assert(!ipa->applyIspControls(epoch,change,&update)&&update.valid);
  assert(!ipa->prepareParameters(epoch,1,update.revision,&used));packet(false);
  assert(!ipa->frameMetadata(epoch,2,ipa::camss::SensorContext{true,500,512,0},&metadata));
  old=metadata.get(controls::ColourGains);assert(old&&(*old)[0]==oldGains[0]&&(*old)[1]==oldGains[1]);
  ipa->parametersApplied(epoch,4,update.revision);
  assert(!ipa->frameMetadata(epoch,4,ipa::camss::SensorContext{true,500,512,0},&metadata));
  auto now=metadata.get(controls::ColourGains);assert(now&&((*now)[0]!=oldGains[0]||(*now)[1]!=oldGains[1]));
  ipa->stop();
 }
 ipa->unmapBuffers({1});
 assert(!ipa->configure(info,info.outputSize,sensor,argv[12],&supported,&configuration));
 assert(!ipa->mapBuffers({buffer},{}));assert(!ipa->start(++epoch,start,&translated));
 assert(!ipa->prepareParameters(epoch,1,0,&used));packet(false);ipa->parametersApplied(epoch,2,0);ipa->stop();ipa->unmapBuffers({1});
 munmap(memory,32768);
 std::cout<<"GAMMA_CONTRACT_PASS packets="<<packets<<" gamma_packets="<<gammaPackets<<" restart=1 reconfigure_legacy=1"<<std::endl;
 return 0;
}
