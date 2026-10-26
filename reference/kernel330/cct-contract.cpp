/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <cassert>
#include <cmath>
#include <cstring>
#include <cstdlib>
#include <dlfcn.h>
#include <iostream>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/videodev2.h>
#include <linux/qcom-camss-config.h>
#include <libcamera/control_ids.h>
#include <libcamera/ipa/camss_ipa_interface.h>
using namespace libcamera;
struct Observation {
	ControlList metadata;
	int status=-1;
	void ready(uint64_t,uint32_t,uint32_t,const ipa::camss::Statistics &s,const ControlList &m)
	{ status=s.status;metadata=m; }
};
int main(int argc,char **argv)
{
	assert(argc==13);
	void *handle=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(handle);
	auto create=reinterpret_cast<IPAInterface *(*)()>(dlsym(handle,"ipaCreate"));assert(create);
	std::unique_ptr<ipa::camss::IPACamssInterface> ipa(static_cast<ipa::camss::IPACamssInterface*>(create()));
	const ControlId exposure(V4L2_CID_EXPOSURE,"Exposure","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
	const ControlId gain(V4L2_CID_ANALOGUE_GAIN,"Gain","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
	const ControlIdMap ids{{V4L2_CID_EXPOSURE,&exposure},{V4L2_CID_ANALOGUE_GAIN,&gain}};
	const ControlInfoMap sensor({{&exposure,ControlInfo(int32_t(4),int32_t(3332),int32_t(500))},
		{&gain,ControlInfo(int32_t(32),int32_t(960),int32_t(512))}},ids);
	IPACameraSensorInfo info{};info.model=argv[3];info.bitsPerPixel=10;
	info.outputSize=Size(std::stoul(argv[4]),std::stoul(argv[5]));info.pixelRate=std::stoull(argv[6]);
	info.minLineLength=info.maxLineLength=std::stoul(argv[7]);info.minFrameLength=std::stoul(argv[8]);info.maxFrameLength=65535;
	ControlInfoMap controlsInfo;ipa::camss::SensorControlConfiguration configuration{};
	assert(!ipa->init(IPASettings{"",info.model},info,sensor,ControlInfoMap{},"",&controlsInfo));
	assert(!ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration));
	assert(controlsInfo.at(&controls::ColourTemperature).min().get<int32_t>()==1500);
	assert(controlsInfo.at(&controls::ColourTemperature).max().get<int32_t>()==12000);
	SharedFD fd(memfd_create("cct-parameters",MFD_CLOEXEC)),sf(memfd_create("cct-statistics",MFD_CLOEXEC));
	assert(!ftruncate(fd.get(),32768)&&!ftruncate(sf.get(),32768));
	auto *memory=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,fd.get(),0));
	auto *stats=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,sf.get(),0));
	assert(memory!=MAP_FAILED&&stats!=MAP_FAILED);
	IPABuffer buffer(1,{FrameBuffer::Plane{fd,0,32768}}),statBuffer(2,{FrameBuffer::Plane{sf,0,32768}});
	assert(!ipa->mapBuffers({buffer},{statBuffer}));
	ControlList request(controls::controls),converted(sensor);
	request.set(controls::ExposureTimeMode,controls::ExposureTimeModeManual);
	request.set(controls::AnalogueGainMode,controls::AnalogueGainModeManual);
	request.set(controls::AwbEnable,false);request.set(controls::ColourTemperature,6500);
	assert(!ipa->start(1,request,&converted));uint32_t bytes=0;
	auto check=[&](unsigned index) {
		assert(bytes==56);
		const auto *wb=reinterpret_cast<const camss_params_wb_gain*>(memory+sizeof(v4l2_isp_buffer));
		assert(wb->r_gain==std::lround(std::atof(argv[9+index*2])*1024));
		assert(wb->g_gain==1024);
		assert(wb->b_gain==std::lround(std::atof(argv[10+index*2])*1024));
	};
	assert(!ipa->prepareParameters(1,1,0,&bytes));check(0);ipa->parametersApplied(1,2,0);
	ControlList metadata(controls::controls);
	auto meta=[&](uint32_t sof){assert(!ipa->frameMetadata(1,sof,ipa::camss::SensorContext{true,500,512,0},&metadata));};
	meta(2);assert(metadata.get(controls::ColourTemperature)==6500);
	request.clear();request.set(controls::ColourTemperature,2850);
	assert(!ipa->convertControls(1,request,&converted)&&converted.empty());
	ipa::camss::AutoIspUpdate update{};
	assert(!ipa->applyIspControls(1,request,&update)&&update.valid);
	assert(!ipa->prepareParameters(1,1,update.revision,&bytes));check(1);
	meta(4);assert(metadata.get(controls::ColourTemperature)==6500);
	ipa->parametersApplied(1,5,update.revision);
	meta(4);assert(metadata.get(controls::ColourTemperature)==6500);
	meta(5);assert(metadata.get(controls::ColourTemperature)==2850);
	Observation observation;ipa->statsProcessed.connect(&observation,&Observation::ready);
	auto *envelope=reinterpret_cast<v4l2_isp_buffer*>(stats);
	auto *histogram=reinterpret_cast<camss_stats_bhist*>(stats+sizeof(*envelope));
	envelope->version=V4L2_ISP_VERSION_V1;envelope->data_size=sizeof(*histogram);
	histogram->header={CAMSS_STATS_AEC_BHIST,0,sizeof(*histogram)};
	histogram->bins[256]=info.outputSize.width*info.outputSize.height/4;
	ipa->processStats(1,6,2,sizeof(*envelope)+sizeof(*histogram),ipa::camss::SensorContext{true,500,512,0});
	assert(!observation.status&&observation.metadata.get(controls::ColourTemperature)==2850);
	request.set(controls::ColourTemperature,1499);assert(ipa->convertControls(1,request,&converted)==-ERANGE);
	request.clear();request.set(controls::ColourGains,{1.25f,.75f});
	assert(!ipa->convertControls(1,request,&converted)&&converted.empty());
	assert(!ipa->applyIspControls(1,request,&update)&&update.valid);
	assert(!ipa->prepareParameters(1,1,update.revision,&bytes));ipa->parametersApplied(1,7,update.revision);
	meta(7);assert(!metadata.get(controls::ColourTemperature));
	request.clear();request.set(controls::AwbEnable,true);request.set(controls::ColourTemperature,6500);
	assert(!ipa->applyIspControls(1,request,&update)&&update.valid);
	assert(!ipa->prepareParameters(1,1,update.revision,&bytes));ipa->parametersApplied(1,8,update.revision);
	meta(8);assert(!metadata.get(controls::ColourTemperature)&&metadata.get(controls::AwbEnable).value_or(false));
	ipa->stop();ipa->unmapBuffers({1,2});ipa.reset();dlclose(handle);
	std::cout<<"CCT_CONTRACT_PASS startup/runtime packets, SOF metadata, explicit-gain clearing, auto-ignore"<<std::endl;
	return 0;
}
