/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <cassert>
#include <array>
#include <cstdlib>
#include <ctime>
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
 IPACameraSensorInfo info{};info.model="s5kgw1";info.outputSize=Size(4608,std::stoul(getenv("CONTRACT_HEIGHT")));info.bitsPerPixel=10;
 info.pixelRate=1920000000;info.minLineLength=info.maxLineLength=17824;info.minFrameLength=3584;info.maxFrameLength=65535;
 ControlInfoMap controlsInfo;ipa::camss::SensorControlConfiguration configuration{};
 const ControlId focus(V4L2_CID_FOCUS_ABSOLUTE,"Focus","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlIdMap lensIds{{V4L2_CID_FOCUS_ABSOLUTE,&focus}};
 const ControlInfoMap lens({{&focus,ControlInfo(int32_t(0),int32_t(1023),int32_t(208))}},lensIds);
 assert(!ipa->init(IPASettings{"","s5kgw1"},info,sensor,lens,"lc898219xi",&controlsInfo));
 int configured=ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration);
 std::cerr<<"TONE_CONFIG status="<<configured<<std::endl;assert(!configured);assert(configuration.pd10==(std::string(argv[3])=="factory"));
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
 constexpr uint32_t baseUsed=sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist)+gridBytes;
 std::memset(memory,0,capacity);envelope->version=V4L2_ISP_VERSION_V1;envelope->data_size=baseUsed-sizeof(*envelope);
 hist->header={CAMSS_STATS_AEC_BHIST,0,sizeof(*hist)};for(auto &bin:hist->bins)bin=(info.outputSize.width/2)*(info.outputSize.height/2)/1024;
 auto *bg=reinterpret_cast<camss_stats_awb_bg*>(memory+sizeof(*envelope)+sizeof(*hist));
 bg->header={CAMSS_STATS_AWB_BG,0,gridBytes};bg->left=16;bg->top=12;
 bg->region_width=bg->region_height=50;bg->columns=16;bg->rows=16;bg->high_threshold=16383;bg->input_bits=14;
 for(unsigned i=0;i<256;++i){auto &r=bg->regions[i];r.r_count=r.b_count=r.gr_count=r.gb_count=625;r.r_sum=r.b_sum=r.gr_sum=r.gb_sum=1250000;}
 ControlList start(controls::controls),converted(sensor);start.set(controls::AwbEnable,false);
 start.set(controls::ColourGains,{1.f,1.f});assert(!ipa->start(1,start,&converted));
 uint32_t bytes=0;auto *parameterMemory=static_cast<uint8_t*>(mmap(nullptr,capacity,PROT_READ,MAP_SHARED,pfd.get(),0));assert(parameterMemory!=MAP_FAILED);
 auto queue=[&](uint32_t rev){
  assert(!ipa->prepareParameters(1,1,rev,&bytes));camss_params_ife_gtm g{};bool found=false;
  v4l2_isp_buffer e;std::memcpy(&e,parameterMemory,sizeof e);assert(e.data_size+sizeof e==bytes);
  for(size_t at=sizeof e;at<bytes;){v4l2_isp_block_header h;std::memcpy(&h,parameterMemory+at,sizeof h);assert(h.size>=8&&at+h.size<=bytes);
   if(h.type==CAMSS_PARAMS_IFE_GTM){assert(!found&&h.size==sizeof g&&!h.flags);std::memcpy(&g,parameterMemory+at,sizeof g);found=true;}at+=h.size;}
  assert(found&&g.cookie);ipa->parametersApplied(1,0,rev);return g;
 };
 auto initial=queue(0);assert(initial.cookie==1&&initial.enabled==0);
 constexpr uint32_t used=baseUsed+sizeof(camss_stats_ife_gtm);
 camss_stats_ife_gtm receipt{};receipt.header={CAMSS_STATS_IFE_GTM,0,sizeof receipt};receipt.cookie=1;receipt.generation=1;receipt.status=1;
 auto stamp=[&](){envelope->data_size=used-sizeof(*envelope);std::memcpy(memory+baseUsed,&receipt,sizeof receipt);};
 auto process=[&](uint32_t sof){stamp();unsigned calls=observed.calls;ipa->processStats(1,sof,100,used,ipa::camss::SensorContext{true,500,32,0});assert(observed.calls==calls+1);return observed.result;};
 auto bad=receipt;receipt.cookie=999;auto rejected=process(0);assert(rejected.status==-ESTALE&&!rejected.parametersKnown&&!rejected.ipeToken);receipt=bad;
 auto first=process(0);assert(!first.status&&first.ipeToken&&first.ispRevision==0&&first.ispUpdate.valid);
 std::vector<uint8_t> packet,committed;uint64_t revision=0;bool fresh=false;

 const bool combined=std::string(getenv("COMBINED_FOCUS"))=="1";
 std::ofstream snapshot(argv[4],std::ios::binary);assert(snapshot.good());
 ControlList focusControls(controls::controls);ipa::camss::LensMove lastMove{};
 bool lastPrepared=false;int lastFocusStatus=0;
 auto focused=[&](uint64_t epoch,uint32_t sof,uint64_t token,const ControlList &focus){
  ControlList metadata(controls::controls);ipa::camss::LensMove move{};
  bool prepared=false;int32_t toneStatus=0;packet.clear();revision=0;fresh=false;
  timespec clock{};assert(!clock_gettime(CLOCK_MONOTONIC,&clock));
  const uint64_t captured=uint64_t(clock.tv_sec)*1000000000+clock.tv_nsec;
  int focusStatus;
  if(combined)focusStatus=ipa->prepareFocusedIpe(epoch,sof,token,focus,true,321,captured,
    ipa::camss::SensorContext{true,500,32,0},&metadata,&move,&prepared,&toneStatus,&packet,&revision,&fresh);
  else {
   focusStatus=ipa->processFocus(epoch,sof,focus,true,321,captured,ipa::camss::SensorContext{true,500,32,0},&metadata,&move);
   if(!move.valid){prepared=true;toneStatus=ipa->prepareIpeParameters(epoch,sof,token,&packet,&revision,&fresh);}
  }
  const std::array<uint64_t,15> header{epoch,sof,token,uint64_t(int64_t(focusStatus)),uint64_t(int64_t(toneStatus)),
   prepared,revision,fresh,packet.size(),uint64_t(int64_t(metadata.get(controls::FocusFoM).value_or(-1))),
   uint64_t(int64_t(metadata.get(controls::AfState).value_or(-1))),uint64_t(int64_t(metadata.get(controls::AfMode).value_or(-1))),
   move.valid,move.serial,uint64_t(int64_t(move.position))};
  snapshot.write(reinterpret_cast<const char*>(header.data()),sizeof header);
  snapshot.write(reinterpret_cast<const char*>(packet.data()),packet.size());assert(snapshot.good());
  lastMove=move;lastPrepared=prepared;lastFocusStatus=focusStatus;
  return int(toneStatus);
 };
 auto prepare=[&](uint32_t sof,uint64_t token){
  int ret=focused(1,sof,token,focusControls);assert(!lastFocusStatus&&lastPrepared&&!lastMove.valid);return ret;
 };

 assert(!prepare(0,first.ipeToken)&&packet.size()==6008&&!fresh&&revision==0);
 assert(reinterpret_cast<const qcom_ipe_a5_frame_params*>(packet.data())->flags==0);
 ipa->frameProcessed(1,0,first.ipeToken,true);
 auto second=queue(first.ispUpdate.revision);assert(second.cookie==2&&second.enabled==1);
 auto stillInitial=process(1);assert(!stillInitial.status&&stillInitial.ispRevision==0&&!stillInitial.ispUpdate.valid);
 assert(!prepare(1,stillInitial.ipeToken)&&!fresh&&revision==0);ipa->frameProcessed(1,1,stillInitial.ipeToken,true);
 receipt.cookie=2;receipt.generation=2;receipt.status=3;receipt.bank=1;
 auto applied=process(2);assert(!applied.status&&applied.ispRevision==1&&applied.ispUpdate.valid);
 assert(!prepare(2,applied.ipeToken)&&fresh&&revision==1&&packet.size()==6008);
 auto third=queue(applied.ispUpdate.revision);assert(third.cookie==3&&third.enabled==1);
 ControlList deferredControls(controls::controls);ipa::camss::AutoIspUpdate deferred{};
 assert(ipa->applyIspControls(1,3,deferredControls,&deferred)==-EAGAIN);
 ipa->frameProcessed(1,2,applied.ipeToken,false);
 auto oldVersion=process(3);assert(!oldVersion.status&&oldVersion.ispRevision==1);
 assert(!prepare(3,oldVersion.ipeToken)&&fresh&&revision==1);ipa->frameProcessed(1,3,oldVersion.ipeToken,true);committed=packet;
 receipt.cookie=3;receipt.generation=3;receipt.bank=0;
 auto newest=process(4);assert(!newest.status&&newest.ispRevision==2&&!newest.ispUpdate.valid);
 assert(!ipa->applyIspControls(1,5,deferredControls,&deferred));
 assert(!prepare(4,newest.ipeToken)&&fresh&&revision==2);
 ipa->frameProcessed(99,4,newest.ipeToken,true);assert(prepare(5,0)==-ENODATA);
 const uint32_t legacy=sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist);std::vector<uint8_t> grid(memory+legacy,memory+baseUsed);
 auto noLux=[&](uint32_t sof){
  envelope->data_size=sizeof(camss_stats_bhist)+sizeof receipt;std::memcpy(memory+legacy,&receipt,sizeof receipt);
  ipa->processStats(1,sof,100,legacy+sizeof receipt,ipa::camss::SensorContext{true,500,32,0});
  std::memcpy(memory+legacy,grid.data(),grid.size());assert(!observed.result.status&&observed.result.ipeToken&&!observed.result.luxValid);return observed.result;
 };
 auto missing=noLux(5);assert(prepare(5,missing.ipeToken)==-EAGAIN); // old held LTM cannot consume a different upstream GTM
 ipa->frameProcessed(1,4,newest.ipeToken,false);ipa->frameProcessed(1,5,missing.ipeToken,false);
 auto recovered=process(6);assert(!recovered.status&&recovered.ispRevision==2);
 assert(!prepare(6,recovered.ipeToken)&&fresh&&revision==2);ipa->frameProcessed(1,6,recovered.ipeToken,true);committed=packet;
 auto held=noLux(7);assert(!prepare(7,held.ipeToken)&&packet==committed&&!fresh&&revision==2);ipa->frameProcessed(1,7,held.ipeToken,true);
 auto saved=receipt;receipt.generation=99;rejected=process(8);assert(rejected.status==-EPROTO&&!rejected.ipeToken);receipt=saved;
 auto resumed=process(8);assert(!resumed.status&&resumed.ipeToken&&resumed.ispRevision==2);ipa->frameProcessed(1,8,resumed.ipeToken,false);

 // A real AF trigger creates a move. Neither path prepares tone before ACK.
 ControlList trigger(controls::controls);trigger.set(controls::AfTrigger,controls::AfTriggerStart);
 assert(!focused(1,100,UINT64_MAX,trigger));assert(!lastFocusStatus&&lastMove.valid&&!lastPrepared&&packet.empty()&&!revision&&!fresh);
 ipa->lensPositionApplied(1,lastMove.serial,-EIO,0);
 assert(focused(1,101,UINT64_MAX,focusControls)==-ESTALE&&lastPrepared&&!lastMove.valid);
 ipa->stop();
 assert(focused(1,102,0,focusControls)==-ESTALE&&lastFocusStatus==-ESTALE);
 assert(!ipa->start(2,start,&converted));
 assert(focused(1,103,0,focusControls)==-ESTALE&&lastFocusStatus==-ESTALE);
assert(ipa->prepareIpeParameters(2,0,0,&packet,&revision,&fresh)==-ENODATA);
 assert(ipa->prepareIpeParameters(1,6,recovered.ipeToken,&packet,&revision,&fresh)==-ESTALE);
 ipa->stop();ipa->unmapBuffers({1,100});ipa.reset();dlclose(handle);munmap(memory,capacity);munmap(parameterMemory,capacity);
 snapshot.close();assert(snapshot.good());
 std::cout<<"GTM_IPA_CONTRACT passed=1 actual_module=1 submission_not_ack=1 bootstrap_no_math_commit=1 physical_vs_numeric_history=1 incompatible_hold_rejected=1 matching_hold_kept=1\n";
}
