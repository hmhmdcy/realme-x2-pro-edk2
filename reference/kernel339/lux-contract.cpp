/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <cassert>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iomanip>
#include <iostream>
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
 if(mode<0){assert(configured==mode);std::cout<<"LUX_REJECT_PASS"<<std::endl;return 0;}
 assert(!configured);
 const bool enabled=mode!=0;
 std::ifstream file(std::string(argv[2])+".stats",std::ios::binary);std::vector<uint8_t> original((std::istreambuf_iterator<char>(file)),{});assert(original.size()==16424);
 SharedFD fd(memfd_create("lux-parameters",MFD_CLOEXEC)),sf(memfd_create("lux-statistics",MFD_CLOEXEC));
 assert(!ftruncate(fd.get(),32768)&&!ftruncate(sf.get(),32768));
 auto *stats=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,sf.get(),0));assert(stats!=MAP_FAILED);
 IPABuffer p(1,{FrameBuffer::Plane{fd,0,32768}}),s(2,{FrameBuffer::Plane{sf,0,32768}});assert(!ipa->mapBuffers({p},{s}));
 Observation observation;ipa->statsProcessed.connect(&observation,&Observation::ready);
 auto restore=[&](){std::memset(stats,0,32768);std::memcpy(stats,original.data(),original.size());};restore();
 auto *envelope=reinterpret_cast<v4l2_isp_buffer*>(stats);
 auto *bg=reinterpret_cast<camss_stats_awb_bg*>(stats+sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist));
 ControlList request(controls::controls),translated(sensor);
 request.set(controls::ExposureTimeMode,controls::ExposureTimeModeManual);request.set(controls::AnalogueGainMode,controls::AnalogueGainModeManual);
 request.set(controls::AwbEnable,false);request.set(controls::ColourGains,{1.25f,.75f});
 auto start=[&](uint64_t epoch){assert(!ipa->start(epoch,request,&translated));uint32_t used=0;assert(!ipa->prepareParameters(epoch,1,0,&used));ipa->parametersApplied(epoch,2,0);};start(1);
 auto process=[&](uint64_t epoch,uint32_t sof,bool valid,uint32_t lines,uint32_t code,unsigned kind,bool wanted,int status=0){
  unsigned before=observation.calls;
  ipa->processStats(epoch,sof,2,sizeof(*envelope)+envelope->data_size,ipa::camss::SensorContext{valid,lines,code,0});
  assert(observation.calls==before+1&&observation.result.status==status);
  const auto &r=observation.result;assert(r.luxValid==(enabled&&wanted));
  std::cout<<"LUX_OBSERVATION {\"epoch\":"<<epoch<<",\"sof\":"<<sof<<",\"kind\":"<<kind<<",\"valid\":"<<r.luxValid
   <<",\"revision\":"<<r.ispRevision<<",\"lines\":"<<lines<<",\"gain\":"<<observation.metadata.get(controls::AnalogueGain).value_or(0)
   <<",\"red\":"<<(observation.metadata.get(controls::ColourGains)?(*observation.metadata.get(controls::ColourGains))[0]:0)
   <<",\"blue\":"<<(observation.metadata.get(controls::ColourGains)?(*observation.metadata.get(controls::ColourGains))[1]:0)
   <<",\"exposure_index\":"<<r.exposureIndex<<",\"luma\":"<<r.luxLuma<<",\"index\":"<<r.luxIndex<<"}"<<std::endl;
 };
 process(1,0,true,500,512,0,false);
 process(1,2,true,500,512,0,true);
 process(1,2,true,500,512,0,false,-EALREADY);
 process(1,3,false,500,512,0,false);
 process(1,4,true,800,256,0,true);
 envelope->data_size=sizeof(camss_stats_bhist);process(1,5,true,500,512,1,false);restore();
 bg->left=bg->top=0;bg->region_width=6;bg->region_height=4;bg->columns=32;bg->rows=24;bg->header.size=24+768*24;
 for(unsigned n=0;n<768;n++)bg->regions[n]={6000,6000,6000,6000,6,6,6,6};
 envelope->data_size=sizeof(camss_stats_bhist)+bg->header.size;
 process(1,6,true,500,512,2,false);restore();
 process(1,7,true,500,512,0,true);
 --envelope->data_size;process(1,8,true,500,512,0,false,-EPROTO);restore();
 ControlList change(controls::controls);change.set(controls::ColourGains,{4.f,2.f});
 ipa::camss::AutoIspUpdate update{};assert(!ipa->applyIspControls(1,change,&update)&&update.valid);
 uint32_t bytes=0;assert(!ipa->prepareParameters(1,1,update.revision,&bytes));
 process(1,10,true,700,512,0,true);process(1,11,true,900,768,0,true);
 ipa->parametersApplied(1,12,update.revision);process(1,12,true,900,768,0,true);
 for(unsigned n=0;n<512;n++)bg->regions[n].r_sum=bg->regions[n].b_sum=bg->regions[n].gr_sum=bg->regions[n].gb_sum=0;
 process(1,13,true,900,768,3,true);
 for(unsigned n=0;n<512;n++)bg->regions[n]={0,0,0,0,0,0,0,0};
 process(1,14,true,900,768,4,true);
 ipa->stop();restore();start(2);process(2,2,true,500,512,0,true);
 ipa->stop();ipa->unmapBuffers({1,2});ipa.reset();dlclose(handle);
 std::cout<<"LUX_CONTRACT_PASS"<<std::endl;
}
