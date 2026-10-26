/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <cassert>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <memory>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/videodev2.h>
#include <linux/qcom-camss-config.h>
#include <linux/qcom-ipe-a5.h>
#include <libcamera/control_ids.h>
#include <libcamera/ipa/camss_ipa_interface.h>
using namespace libcamera;
struct Observation {
 ipa::camss::Statistics result{}; unsigned calls=0;
 void ready(uint64_t,uint32_t,uint32_t,const ipa::camss::Statistics &s,const ControlList &){result=s;++calls;}
};
int main(int argc,char **argv)
{
 assert(argc==5);
 void *handle=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);if(!handle){std::cerr<<dlerror()<<std::endl;return 2;}
 auto create=reinterpret_cast<IPAInterface *(*)()>(dlsym(handle,"ipaCreate"));assert(create);
 std::unique_ptr<ipa::camss::IPACamssInterface> ipa(static_cast<ipa::camss::IPACamssInterface*>(create()));
 Observation observed;ipa->statsProcessed.connect(&observed,&Observation::ready);
 const ControlId exposure(V4L2_CID_EXPOSURE,"Exposure","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlId gain(V4L2_CID_ANALOGUE_GAIN,"Gain","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlIdMap ids{{V4L2_CID_EXPOSURE,&exposure},{V4L2_CID_ANALOGUE_GAIN,&gain}};
 const ControlInfoMap sensor({{&exposure,ControlInfo(int32_t(4),int32_t(3576),int32_t(500))},
  {&gain,ControlInfo(int32_t(32),int32_t(512),int32_t(32))}},ids);
 IPACameraSensorInfo info{};info.model="s5kgw1";info.outputSize=Size(4608,3456);info.bitsPerPixel=10;
 info.pixelRate=1920000000;info.minLineLength=info.maxLineLength=17824;info.minFrameLength=3584;info.maxFrameLength=65535;
 ControlInfoMap controlsInfo;ipa::camss::SensorControlConfiguration configuration{};
 const ControlId focus(V4L2_CID_FOCUS_ABSOLUTE,"Focus","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlIdMap lensIds{{V4L2_CID_FOCUS_ABSOLUTE,&focus}};
 const ControlInfoMap lens({{&focus,ControlInfo(int32_t(0),int32_t(1023),int32_t(208))}},lensIds);
 assert(!ipa->init(IPASettings{"","s5kgw1"},info,sensor,lens,"lc898219xi",&controlsInfo));
 int configured=ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration);
 std::cerr<<"TONE_CONFIG status="<<configured<<std::endl;assert(!configured);
 constexpr unsigned capacity=262144;
 SharedFD pfd(memfd_create("parameters",MFD_CLOEXEC)),sfd(memfd_create("statistics",MFD_CLOEXEC));
 assert(!ftruncate(pfd.get(),capacity)&&!ftruncate(sfd.get(),capacity));
 auto *memory=static_cast<uint8_t*>(mmap(nullptr,capacity,PROT_READ|PROT_WRITE,MAP_SHARED,sfd.get(),0));assert(memory!=MAP_FAILED);
 std::vector<FrameBuffer::Plane> pplanes{{pfd,0,capacity}},splanes{{sfd,0,capacity}};
 std::vector<IPABuffer> parameters{IPABuffer(1,pplanes)},statistics{IPABuffer(100,splanes)};
 assert(!ipa->mapBuffers(parameters,statistics));
 auto *envelope=reinterpret_cast<v4l2_isp_buffer*>(memory);
 auto *hist=reinterpret_cast<camss_stats_bhist*>(memory+sizeof(*envelope));
 constexpr uint32_t gridBytes=sizeof(camss_stats_awb_bg)+256*sizeof(camss_stats_bg_region);
 constexpr uint32_t used=sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist)+gridBytes;
 std::memset(memory,0,capacity);envelope->version=V4L2_ISP_VERSION_V1;envelope->data_size=used-sizeof(*envelope);
 hist->header={CAMSS_STATS_AEC_BHIST,0,sizeof(*hist)};for(auto &bin:hist->bins)bin=3888;
 auto *bg=reinterpret_cast<camss_stats_awb_bg*>(memory+sizeof(*envelope)+sizeof(*hist));
 bg->header={CAMSS_STATS_AWB_BG,0,gridBytes};bg->left=16;bg->top=12;
 bg->region_width=bg->region_height=50;bg->columns=16;bg->rows=16;bg->high_threshold=16383;bg->input_bits=14;
 for(unsigned i=0;i<256;++i){auto &r=bg->regions[i];r.r_count=r.b_count=r.gr_count=r.gb_count=625;r.r_sum=r.b_sum=r.gr_sum=r.gb_sum=1250000;}
 ControlList start(controls::controls),converted(sensor);start.set(controls::AwbEnable,false);
 start.set(controls::ColourGains,{1.f,1.f});assert(!ipa->start(1,start,&converted));
 uint32_t bytes=0;assert(!ipa->prepareParameters(1,1,0,&bytes)&&bytes>0);ipa->parametersApplied(1,0,0);
 std::vector<uint8_t> packet,committed;uint64_t revision=0;bool fresh=false;
 const bool bypass=std::string(argv[3])=="bypass";
 auto process=[&](uint32_t sof,int32_t code){unsigned n=observed.calls;ipa->processStats(1,sof,100,used,ipa::camss::SensorContext{true,500,code,0});std::cerr<<"TONE_STATS status="<<observed.result.status<<" token="<<observed.result.ipeToken<<" lux-valid="<<observed.result.luxValid<<std::endl;assert(observed.calls==n+1&&!observed.result.status&&observed.result.ipeToken);return observed.result.ipeToken;};
 auto prepare=[&](uint32_t sof,uint64_t token){return ipa->prepareIpeParameters(1,sof,token,&packet,&revision,&fresh);};
 auto first=process(1,32);assert(!prepare(1,first));
 if(bypass){assert(packet.empty()&&!fresh);ipa->frameProcessed(1,1,first,true);}
 else {
  assert(packet.size()==6008&&fresh&&revision==1);
  assert(reinterpret_cast<const qcom_ipe_a5_frame_params*>(packet.data())->size==6008);
  assert(!prepare(2,0)&&packet.empty()&&!fresh&&revision==0); // busy, no committed state
  ipa->frameProcessed(1,1,first,false); // failure must not advance state
  auto second=process(2,64);assert(!prepare(2,second)&&fresh&&revision==1);
  ipa->frameProcessed(1,2,second,true);committed=packet;
  assert(!prepare(3,0)&&packet==committed&&!fresh&&revision==1);
  auto third=process(3,96);assert(!prepare(3,third)&&fresh&&revision==2);
  assert(!prepare(4,0)&&packet==committed&&!fresh&&revision==1); // hold uses acknowledged program
  assert(ipa->prepareIpeParameters(9,3,third,&packet,&revision,&fresh)==-ESTALE);
  ipa->frameProcessed(9,3,third,true); // stale receipt cannot commit
  ipa->frameProcessed(1,3,third,false);
  assert(!prepare(4,0)&&packet==committed&&revision==1&&!fresh);
  auto fourth=process(4,128);assert(!prepare(4,fourth)&&fresh&&revision==2);
  ipa->frameProcessed(1,4,fourth,true);committed=packet;
  assert(prepare(4,fourth)==-ESTALE); // token consumed
  assert(!prepare(5,0)&&packet==committed&&revision==2&&!fresh);
  std::ofstream output(argv[4],std::ios::binary);output.write(reinterpret_cast<const char*>(packet.data()),packet.size());assert(output.good());
 }
 ipa->stop();assert(!ipa->start(2,start,&converted));
 assert(!ipa->prepareIpeParameters(2,0,0,&packet,&revision,&fresh)&&packet.empty()&&revision==0&&!fresh);
 assert(ipa->prepareIpeParameters(1,1,first,&packet,&revision,&fresh)==-ESTALE);
 ipa->stop();ipa->unmapBuffers({1,100});ipa.reset();dlclose(handle);munmap(memory,capacity);
 std::cout<<"TONE_CONTRACT passed=1 mode="<<argv[3]<<" actual_ipa=1 callbacks="<<observed.calls<<std::endl;
}
