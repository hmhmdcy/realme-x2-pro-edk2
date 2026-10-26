/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <cstdio>
#include <string>
#include <cassert>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <iostream>
#include <optional>
#include <time.h>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/videodev2.h>
#include <linux/qcom-camss-config.h>
#include <libcamera/control_ids.h>
#include <libcamera/ipa/camss_ipa_interface.h>
using namespace libcamera;
struct Observation {
	ipa::camss::Statistics result{};
	ControlList metadata;
	unsigned int calls=0;
	void ready(uint64_t,uint32_t,uint32_t,const ipa::camss::Statistics &s,const ControlList &m)
	{ result=s;metadata=m;++calls; }
};
int main(int argc,char **argv)
{
	assert(argc==9);

	void *handle=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
	if(!handle){std::cerr<<dlerror()<<std::endl;return 2;}
	auto create=reinterpret_cast<IPAInterface *(*)()>(dlsym(handle,"ipaCreate"));
	assert(create);
	std::unique_ptr<ipa::camss::IPACamssInterface> ipa(static_cast<ipa::camss::IPACamssInterface*>(create()));
	Observation observation;
	ipa->statsProcessed.connect(&observation,&Observation::ready);
	const ControlId exposure(V4L2_CID_EXPOSURE,"Exposure","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
	const ControlId gain(V4L2_CID_ANALOGUE_GAIN,"Gain","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
	const ControlIdMap ids{{V4L2_CID_EXPOSURE,&exposure},{V4L2_CID_ANALOGUE_GAIN,&gain}};
	const ControlInfoMap sensor({{&exposure,ControlInfo(int32_t(4),int32_t(3332),int32_t(500))},
		{&gain,ControlInfo(int32_t(32),int32_t(960),int32_t(512))}},ids);
	IPACameraSensorInfo info{};

 info.model=argv[3];info.outputSize=Size(std::stoul(argv[4]),std::stoul(argv[5]));info.bitsPerPixel=10;
 info.pixelRate=std::stoull(argv[6]);info.minLineLength=info.maxLineLength=std::stoul(argv[7]);
 info.minFrameLength=std::stoul(argv[8]);info.maxFrameLength=65535;
	ControlInfoMap controlsInfo;
	ipa::camss::SensorControlConfiguration configuration{};
	const ControlId focus(V4L2_CID_FOCUS_ABSOLUTE,"Focus","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
	ControlIdMap lensIds{{V4L2_CID_FOCUS_ABSOLUTE,&focus}};
	const ControlInfoMap lens({{&focus,ControlInfo(int32_t(0),int32_t(1023),int32_t(208))}},lensIds);
	assert(!ipa->init(IPASettings{"",info.model},info,sensor,lens,"test-lens",&controlsInfo));
	/* configure() resets the proxy's dynamic V4L2 IDs after init(). */
	lensIds.clear();
	if(argc==4){
		auto wrong=info;wrong.pixelRate++;
		assert(ipa->configure(wrong,wrong.outputSize,sensor,argv[2],&controlsInfo,&configuration)==-ENOTSUP);
	}
	if(argc==4 && std::string(argv[3])=="reject-lsc") {
 assert(ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration)==-EINVAL);
 std::cout<<"LSC_REJECT_PASS"<<std::endl;return 0;
 }
 assert(!ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration));
	assert(controlsInfo.at(&controls::AwbEnable).max().get<bool>());

	SharedFD parameterFd(memfd_create("parameters",MFD_CLOEXEC)),statisticsFd(memfd_create("statistics",MFD_CLOEXEC));
	assert(!ftruncate(parameterFd.get(),32768)&&!ftruncate(statisticsFd.get(),32768));
	auto *parameters=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,parameterFd.get(),0));
	auto *memory=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,statisticsFd.get(),0));
	assert(parameters!=MAP_FAILED&&memory!=MAP_FAILED);
	IPABuffer p(1,{FrameBuffer::Plane{parameterFd,0,32768}}),s(100,{FrameBuffer::Plane{statisticsFd,0,32768}});
	assert(!ipa->mapBuffers({p},{s}));
	auto *envelope=reinterpret_cast<v4l2_isp_buffer*>(memory);
	auto *histogram=reinterpret_cast<camss_stats_bhist*>(memory+sizeof(*envelope));
	auto *bg=reinterpret_cast<camss_stats_awb_bg*>(memory+sizeof(*envelope)+sizeof(*histogram));
	
	constexpr uint32_t used=sizeof(v4l2_isp_buffer)+CAMSS_STATS_MAX_PAYLOAD;
	auto fill=[&](bool dark=false){
		std::memset(memory,0,32768);
		envelope->version=V4L2_ISP_VERSION_V1;envelope->data_size=used-sizeof(*envelope);
		histogram->header={CAMSS_STATS_AEC_BHIST,0,sizeof(*histogram)};
		histogram->bins[256]=499392;
		bg->header={CAMSS_STATS_AWB_BG,0,CAMSS_STATS_BG_MAX_PAYLOAD};
		bg->left=16;bg->top=12;bg->region_width=bg->region_height=50;
		bg->columns=32;bg->rows=24;bg->high_threshold=16383;bg->input_bits=14;
		for(unsigned int n=0;n<768;++n){
			auto &r=bg->regions[n];
			r.r_count=r.b_count=r.gr_count=r.gb_count=625;
			r.r_sum=dark?0:625000;r.b_sum=dark?0:312500;
			r.gr_sum=r.gb_sum=dark?0:1250000;
		}
	};
	fill();
	ControlList startControls(controls::controls),sensorControls(sensor);
	startControls.set(controls::AwbEnable,true);
	startControls.set(controls::ColourGains,{.5f,.5f});
	assert(!ipa->start(1,startControls,&sensorControls));
	uint32_t bytes=0;
	assert(!ipa->prepareParameters(1,1,0,&bytes)&&bytes==1848);
 assert(bytes==1848);
 assert(std::fwrite(parameters+56,1,sizeof(camss_params_lsc),stdout)==sizeof(camss_params_lsc));
 ipa->stop();ipa->unmapBuffers({1,100});ipa.reset();dlclose(handle);
 return 0;
}
