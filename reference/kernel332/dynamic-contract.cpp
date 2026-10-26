/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <cassert>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <iostream>
#include <fstream>
#include "libipa/awb_colour_temperature.h"
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
	assert(argc==4);
	ipa::AwbIlluminantRatios points;
	std::ifstream pointFile(argv[3],std::ios::binary);
	assert(pointFile.read(reinterpret_cast<char*>(points.data()),sizeof(points)));
	ipa::AwbColourTemperatureModel model;assert(model.configure(points));
	unsigned int checkedTemperatures=0;std::optional<int32_t> firstTemperature;bool changedTemperature=false;
	auto checkCct=[&](const ControlList &metadata) {
	 auto gains=metadata.get(controls::ColourGains);assert(gains);
	 ipa::AwbColourTemperatureEstimate expected;
	 assert(model.estimate({float(1.0/(*gains)[0]),float(1.0/(*gains)[1])},&expected));
	 auto cct=metadata.get(controls::ColourTemperature);assert(cct&&*cct==std::lround(expected.kelvin));
	 if(!firstTemperature)firstTemperature=cct;
	 else if(cct!=firstTemperature)changedTemperature=true;
	 ++checkedTemperatures;
	};
 const bool lsc=argc==4 && std::string(argv[3])=="lsc";
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
		{&gain,ControlInfo(int32_t(0),int32_t(960),int32_t(512))}},ids);
	IPACameraSensorInfo info{};
	info.model="imx319";info.outputSize=Size(1632,1224);info.bitsPerPixel=10;
	info.pixelRate=209066666;info.minLineLength=info.maxLineLength=2080;
	info.minFrameLength=3350;info.maxFrameLength=65535;
	ControlInfoMap controlsInfo;
	ipa::camss::SensorControlConfiguration configuration{};
	const ControlId focus(V4L2_CID_FOCUS_ABSOLUTE,"Focus","V4L2",ControlTypeInteger32,ControlId::Direction::In|ControlId::Direction::Out);
	ControlIdMap lensIds{{V4L2_CID_FOCUS_ABSOLUTE,&focus}};
	const ControlInfoMap lens({{&focus,ControlInfo(int32_t(0),int32_t(1023),int32_t(208))}},lensIds);
	assert(!ipa->init(IPASettings{"","imx319"},info,sensor,lens,"test-lens",&controlsInfo));
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
	const bool afSupported=controlsInfo.find(&controls::AfMode)!=controlsInfo.end();
	assert(afSupported==(argc==4 && std::string(argv[3])=="af"));
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
	constexpr uint32_t legacy=sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist);
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
	assert(!ipa->prepareParameters(1,1,0,&bytes)&&bytes==(lsc?1848:56));
 if(lsc) {
  const auto *mesh=reinterpret_cast<const camss_params_lsc*>(parameters+56);
  assert(mesh->header.type==CAMSS_PARAMS_LSC && mesh->header.size==sizeof(*mesh) && mesh->header.flags==V4L2_ISP_PARAMS_FL_BLOCK_ENABLE);
  assert(mesh->cell_width==52 && mesh->cell_height==52 && mesh->x_start==8 && mesh->y_start==6 && mesh->subdivision==1);
  for(unsigned y=0;y<13;y++)for(unsigned x=0;x<17;x++) {
   double sx=(4+(int(x*52)-8)*2)/1639.0*16;
   double sy=(4+(int(y*52)-6)*2)/1231.0*12;
   std::array<double,4> expected={2*(1.25+.01*sx+.02*sy),1.25+.0175*sx+.01*sy,1.25+.0175*sx+.01*sy,1.5*(2.25+.04*sx+.015*sy)};
   for(unsigned c=0;c<4;c++)assert(std::abs(int(mesh->gains[c][y*17+x])-int(std::lround(expected[c]*1024)))<=1);
  }
  for(auto value:mesh->_pad)assert(!value);
  std::cout<<"LSC_PARAMETERS_PASS calibrated affine mesh and ABI"<<std::endl;
 }
	ipa->parametersApplied(1,2,0);
	ControlList recovered(controls::controls);
	assert(ipa->frameMetadata(1,1,ipa::camss::SensorContext{true,500,512,0},&recovered)==-ENODATA);
	assert(!ipa->frameMetadata(1,2,ipa::camss::SensorContext{true,500,512,0},&recovered));
	assert(recovered.get(controls::AwbEnable).value_or(false));checkCct(recovered);
	assert(!recovered.get(controls::AwbLocked).value_or(true));
	assert(ipa->frameMetadata(1,2,ipa::camss::SensorContext{false,500,512,0},&recovered)==-ENODATA);
	auto process=[&](uint32_t frame,uint32_t length=sizeof(v4l2_isp_buffer)+CAMSS_STATS_MAX_PAYLOAD,int expected=0){
		unsigned int before=observation.calls;
		ipa->processStats(1,frame,100,length,ipa::camss::SensorContext{true,500,512,0});
		assert(observation.calls==before+1&&observation.result.status==expected);
		if(!expected&&observation.result.parametersKnown)checkCct(observation.metadata);
	};
	process(0);
	assert(!observation.result.parametersKnown&&!observation.result.ispUpdate.valid);
	--envelope->data_size;process(1,used,-EPROTO);++envelope->data_size;
	bg->columns=0;process(1,used,-EPROTO);bg->columns=32;
	bg->regions[0].r_count=626;process(1,used,-EPROTO);bg->regions[0].r_count=625;
	envelope->data_size=sizeof(*histogram);process(1,legacy);envelope->data_size=used-sizeof(*envelope);
	assert(!observation.result.rgbPresent&&!observation.result.ispUpdate.valid);
	process(2);
	assert(observation.result.ispUpdate.valid&&observation.result.ispUpdate.revision==1);
	auto first=observation.result.ispUpdate;
	assert(!ipa->prepareParameters(1,1,first.revision,&bytes) && bytes==56);
	process(3);
	assert(!observation.result.ispUpdate.valid&&observation.result.ispRevision==0);
	ipa->parametersApplied(1,5,first.revision);
	process(4);
	assert(observation.result.ispRevision==0);
	auto old=observation.metadata.get(controls::ColourGains);
	assert(old&&(*old)[0]==.5f&&(*old)[1]==.5f);
	std::optional<std::pair<uint32_t,ipa::camss::AutoIspUpdate>> pending;
	unsigned int proposals=1,locked=0,lastFrame=4;
	for(uint32_t frame=5;frame<100;++frame){
		lastFrame=frame;
		if(pending&&pending->first==frame){
			ipa->parametersApplied(1,frame,pending->second.revision);pending.reset();
		}
		process(frame);
		assert(observation.result.parametersKnown&&observation.result.rgbPresent);
		auto gains=observation.metadata.get(controls::ColourGains);
		assert(gains&&std::isfinite((*gains)[0])&&std::isfinite((*gains)[1]));
		if(pending)assert(!observation.result.ispUpdate.valid);
		if(observation.result.ispUpdate.valid){
			auto update=observation.result.ispUpdate;
			assert(update.revision==++proposals&&!pending);
			assert(!ipa->prepareParameters(1,1,update.revision,&bytes) && bytes==56);
			pending=std::make_pair(frame+3,update);
		}
		if(observation.metadata.get(controls::AwbLocked).value_or(false)){
			++locked;
			assert(std::abs((*gains)[0]-2)<.02&&std::abs((*gains)[1]-4)<.02);
			if(locked==4)break;
		}
	}
	assert(locked==4&&!pending&&proposals>4);
	fill(true);process(++lastFrame);
	assert(!observation.result.ispUpdate.valid&&!observation.metadata.get(controls::AwbLocked).value_or(true));
	fill();envelope->data_size=sizeof(*histogram);process(++lastFrame,legacy);
	assert(!observation.result.rgbPresent&&!observation.result.ispUpdate.valid);
	process(lastFrame,legacy,-EALREADY);
	// Runtime mode changes take effect in metadata only at the acknowledged SOF.
	ControlList request(controls::controls),converted(sensor);
	request.set(controls::AwbEnable,false);
	request.set(controls::ColourGains,{1.25f,.75f});
	assert(!ipa->convertControls(1,request,&converted)&&converted.empty());
	ipa::camss::AutoIspUpdate manual{};
	assert(!ipa->applyIspControls(1,request,&manual)&&manual.valid);
	assert(!ipa->prepareParameters(1,1,manual.revision,&bytes) && bytes==56);
	ipa::camss::AutoIspUpdate busy{};
	assert(ipa->applyIspControls(1,request,&busy)==-EAGAIN);
	process(++lastFrame,legacy);
	assert(observation.metadata.get(controls::AwbEnable).value_or(false));
	ipa->parametersApplied(1,lastFrame+2,manual.revision);
	process(++lastFrame,legacy);
	assert(observation.metadata.get(controls::AwbEnable).value_or(false));
	process(++lastFrame,legacy);
	assert(!observation.metadata.get(controls::AwbEnable).value_or(true));
	auto manualGains=observation.metadata.get(controls::ColourGains);
	assert(manualGains&&(*manualGains)[0]==1.25f&&(*manualGains)[1]==.75f);
	request.clear();request.set(controls::ColourGains,{2.0f,.5f});
	assert(!ipa->convertControls(1,request,&converted)&&converted.empty());
	assert(!ipa->applyIspControls(1,request,&manual)&&manual.valid);
	assert(!ipa->prepareParameters(1,1,manual.revision,&bytes) && bytes==56);
	ipa->parametersApplied(1,lastFrame+1,manual.revision);
	process(++lastFrame,legacy);
	manualGains=observation.metadata.get(controls::ColourGains);
	assert(manualGains&&(*manualGains)[0]==2.0f&&(*manualGains)[1]==.5f);
	request.clear();request.set(controls::AwbEnable,true);
	assert(!ipa->applyIspControls(1,request,&manual)&&manual.valid);
	assert(!ipa->prepareParameters(1,1,manual.revision,&bytes) && bytes==56);
	ipa->parametersApplied(1,lastFrame+1,manual.revision);
	process(++lastFrame,legacy);
	assert(observation.metadata.get(controls::AwbEnable).value_or(false));
	request.set(controls::ColourGains,{7.0f,7.0f});
	assert(!ipa->convertControls(1,request,&converted));
	assert(!ipa->applyIspControls(1,request,&manual)&&!manual.valid);
	request.set(controls::ColourGains,{-1.0f,1.0f});
	assert(ipa->convertControls(1,request,&converted)==-ERANGE);
	request.clear();request.set(controls::AwbEnable,false);
	assert(!ipa->applyIspControls(1,request,&manual)&&manual.valid);
	assert(!ipa->prepareParameters(1,1,manual.revision,&bytes) && bytes==56);
	ipa->parametersApplied(1,lastFrame+1,manual.revision);
	process(++lastFrame,legacy);
	manualGains=observation.metadata.get(controls::ColourGains);
	assert(!observation.metadata.get(controls::AwbEnable).value_or(true));
	assert(manualGains&&(*manualGains)[0]==2.0f&&(*manualGains)[1]==.5f);
	ipa->stop();
	assert(!ipa->start(2,startControls,&sensorControls));
	assert(!ipa->prepareParameters(2,1,0,&bytes));
	ipa->parametersApplied(2,0,0);
	fill();ipa->processStats(2,0,100,used,ipa::camss::SensorContext{true,500,512,0});
	assert(!observation.result.status&&observation.result.ispRevision==0&&observation.result.ispUpdate.revision==1);
	ipa->stop();
	if(afSupported){
		assert(!ipa->start(3,startControls,&sensorControls));
		assert(!ipa->prepareParameters(3,1,0,&bytes));ipa->parametersApplied(3,0,0);
		auto now=[](){timespec t{};assert(!clock_gettime(CLOCK_MONOTONIC,&t));return uint64_t(t.tv_sec)*1000000000+t.tv_nsec;};
		ControlList trigger(controls::controls),afMetadata(controls::controls);
		trigger.set(controls::AfTrigger,controls::AfTriggerStart);
		ipa::camss::LensMove move{};
		assert(!ipa->processFocus(3,0,trigger,true,1000,now(),ipa::camss::SensorContext{true,500,512,0},&afMetadata,&move));
		assert(move.valid&&move.position==208&&afMetadata.get(controls::AfState).value_or(-1)==controls::AfStateScanning);
		ipa->lensPositionApplied(3,move.serial,0,now());
		fill();ipa->processStats(3,0,100,used,ipa::camss::SensorContext{true,500,512,0});
		assert(!observation.result.ispUpdate.valid&&!observation.result.automaticUpdate.valid);
		trigger.set(controls::AfTrigger,controls::AfTriggerCancel);
		assert(!ipa->processFocus(3,1,trigger,true,1000,now(),ipa::camss::SensorContext{true,500,512,0},&afMetadata,&move));
		assert(!move.valid&&afMetadata.get(controls::AfState).value_or(-1)==controls::AfStateIdle);
		trigger.set(controls::AfTrigger,controls::AfTriggerStart);
		assert(!ipa->processFocus(3,2,trigger,true,1000,now(),ipa::camss::SensorContext{true,500,512,0},&afMetadata,&move)&&move.valid);
		ipa->lensPositionApplied(3,move.serial,-EIO,now());
		trigger.clear();
		assert(!ipa->processFocus(3,3,trigger,true,1000,now(),ipa::camss::SensorContext{true,500,512,0},&afMetadata,&move));
		assert(!move.valid&&afMetadata.get(controls::AfState).value_or(-1)==controls::AfStateFailed);
		ipa->stop();
	}
	ipa->unmapBuffers({1,100});
	ipa.reset();dlclose(handle);
	munmap(parameters,32768);munmap(memory,32768);
	assert(checkedTemperatures>0&&changedTemperature);
	std::cout<<"AWB_INVERSE_CONTRACT_PASS callbacks="<<observation.calls<<" proposals="<<proposals
		<<" locked="<<locked<<" delayed_ack=3 legacy/truncated/counts/dark/restart=pass"<<std::endl;
}
