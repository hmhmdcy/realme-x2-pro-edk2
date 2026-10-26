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
 IPACameraSensorInfo info{};info.model="s5kgw1";info.outputSize=Size(4608,std::stoul(argv[3]));info.bitsPerPixel=10;
 info.pixelRate=1920000000;info.minLineLength=info.maxLineLength=17824;info.minFrameLength=3584;info.maxFrameLength=65535;
 ControlInfoMap controlsInfo;ipa::camss::SensorControlConfiguration configuration{};
 const ControlId focus(V4L2_CID_FOCUS_ABSOLUTE,"Focus","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
 const ControlIdMap lensIds{{V4L2_CID_FOCUS_ABSOLUTE,&focus}};
 const ControlInfoMap lens({{&focus,ControlInfo(int32_t(0),int32_t(1023),int32_t(208))}},lensIds);
 assert(!ipa->init(IPASettings{"","s5kgw1"},info,sensor,lens,"lc898219xi",&controlsInfo));
 int configured=ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration);
 std::cerr<<"TONE_CONFIG status="<<configured<<std::endl;assert(!configured);

 constexpr unsigned capacity=262144;
 SharedFD fd(memfd_create("parameters",MFD_CLOEXEC));assert(!ftruncate(fd.get(),capacity));
 std::vector<FrameBuffer::Plane> planes{{fd,0,capacity}};
 assert(!ipa->mapBuffers({IPABuffer(1,planes)},{}));
 ControlList start(controls::controls),converted(sensor);start.set(controls::AwbEnable,false);
 assert(!ipa->start(1,start,&converted));
 uint32_t bytes=0;assert(!ipa->prepareParameters(1,1,0,&bytes)&&bytes>0);
 auto *memory=static_cast<const char*>(mmap(nullptr,capacity,PROT_READ,MAP_SHARED,fd.get(),0));assert(memory!=MAP_FAILED);
 std::ofstream output(argv[4],std::ios::binary);output.write(memory,bytes);output.close();assert(output.good());
 munmap(const_cast<char*>(memory),capacity);ipa->stop();ipa->unmapBuffers({1});
 std::cout<<"DS4_CAPABILITY height="<<argv[3]<<" pd10="<<configuration.pd10<<std::endl;
 ipa.reset();dlclose(handle);
}
