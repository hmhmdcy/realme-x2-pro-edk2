/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <cassert>
#include <cmath>
#include <cstring>
#include <cstdlib>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <limits>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/videodev2.h>
#include <linux/qcom-camss-config.h>
#include <libcamera/control_ids.h>
#include <libcamera/ipa/camss_ipa_interface.h>
using namespace libcamera;
struct Expected { camss_params_color_correct packet;std::array<float,9> matrix; };
constexpr size_t expectedRecordSize=40+36;
struct Observation {
 ControlList metadata;int status=-1;
 void ready(uint64_t,uint32_t,uint32_t,const ipa::camss::Statistics &s,const ControlList &m) {status=s.status;metadata=m;}
};
int main(int argc,char **argv)
{
 assert(argc==12);
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
 int mode=std::atoi(argv[11]);int configured=ipa->configure(info,info.outputSize,sensor,argv[2],&supported,&configuration);
 if(mode<0){assert(configured==mode);std::cout<<"CCM_REJECT_PASS"<<std::endl;return 0;}
 assert(!configured);bool enabled=mode!=0,withLsc=mode==2;
 assert((supported.find(&controls::ColourCorrectionMatrix)!=supported.end())==enabled);
 std::ifstream expectedFile(argv[9],std::ios::binary),manualFile(argv[10],std::ios::binary);Expected manual;
 assert(manualFile.read(reinterpret_cast<char*>(&manual.packet),40));assert(manualFile.read(reinterpret_cast<char*>(manual.matrix.data()),36));
 auto expected=[&](int kelvin){Expected result;assert(kelvin>=1500&&kelvin<=12000);expectedFile.seekg((kelvin-1500)*expectedRecordSize);assert(expectedFile.read(reinterpret_cast<char*>(&result.packet),40));assert(expectedFile.read(reinterpret_cast<char*>(result.matrix.data()),36));return result;};
 SharedFD fd(memfd_create("ccm-parameters",MFD_CLOEXEC)),sf(memfd_create("ccm-statistics",MFD_CLOEXEC));
 assert(!ftruncate(fd.get(),32768)&&!ftruncate(sf.get(),32768));
 auto *memory=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,fd.get(),0));
 auto *stats=static_cast<uint8_t*>(mmap(nullptr,32768,PROT_READ|PROT_WRITE,MAP_SHARED,sf.get(),0));
 assert(memory!=MAP_FAILED&&stats!=MAP_FAILED);
 IPABuffer buffer(1,{FrameBuffer::Plane{fd,0,32768}}),statBuffer(2,{FrameBuffer::Plane{sf,0,32768}});
 assert(!ipa->mapBuffers({buffer},{statBuffer}));
 if(enabled){IPABuffer small(3,{FrameBuffer::Plane{fd,0,withLsc?1887u:95u}});assert(!ipa->mapBuffers({small},{}));}
 ControlList request(controls::controls),converted(sensor),metadata(controls::controls);
 request.set(controls::ExposureTimeMode,controls::ExposureTimeModeManual);request.set(controls::AnalogueGainMode,controls::AnalogueGainModeManual);
 request.set(controls::AwbEnable,false);request.set(controls::ColourTemperature,6500);
 assert(!ipa->start(1,request,&converted));uint32_t bytes=0;
 auto packet=[&](const Expected &wanted,bool startup=false){
  assert(bytes==(enabled?96u:56u)+(startup&&withLsc?1792u:0u));
  if(enabled)assert(!std::memcmp(memory+56+(startup&&withLsc?1792:0),&wanted.packet,40));
 };
 auto meta=[&](uint32_t sof){assert(!ipa->frameMetadata(1,sof,ipa::camss::SensorContext{true,500,512,0},&metadata));};
 auto check=[&](const ControlList &m,const Expected &wanted){
  auto matrix=m.get(controls::ColourCorrectionMatrix);assert(bool(matrix)==enabled);
  if(enabled)assert(!std::memcmp(matrix->data(),wanted.matrix.data(),36));
 };
 if(enabled)assert(ipa->prepareParameters(1,3,0,&bytes)==-ENOSPC&&bytes==0);
 assert(!ipa->prepareParameters(1,1,0,&bytes));packet(expected(6500),true);ipa->parametersApplied(1,2,0);
 uint32_t sof=2;Expected current=expected(6500);meta(sof);check(metadata,current);
 ipa::camss::AutoIspUpdate update{};
 auto apply=[&](const Expected &wanted){
  assert(!ipa->convertControls(1,request,&converted)&&converted.empty());
  assert(!ipa->applyIspControls(1,request,&update)&&update.valid);
  assert(!ipa->prepareParameters(1,1,update.revision,&bytes));packet(wanted);
  meta(sof+1);check(metadata,current);
  ipa->parametersApplied(1,sof+2,update.revision);meta(sof+1);check(metadata,current);
  sof+=2;meta(sof);check(metadata,wanted);current=wanted;
 };
 for(int kelvin:{1500,2850,3100,4100,5000,5750,6500,7000,7500,8250,10000,12000}){
  request.clear();request.set(controls::ColourTemperature,kelvin);apply(expected(kelvin));assert(metadata.get(controls::ColourTemperature)==kelvin);
 }
 if(enabled){
  request.clear();request.set(controls::ColourCorrectionMatrix,Span<const float,9>(manual.matrix));request.set(controls::ColourTemperature,6500);apply(manual);
  request.clear();assert(!ipa->applyIspControls(1,request,&update)&&!update.valid);
  request.set(controls::ColourCorrectionMatrix,Span<const float,9>(manual.matrix));assert(!ipa->applyIspControls(1,request,&update)&&!update.valid);
  request.clear();request.set(controls::ColourTemperature,6500);apply(expected(6500));
  request.clear();request.set(controls::ColourCorrectionMatrix,Span<const float,9>(manual.matrix));apply(manual);
  request.clear();request.set(controls::ColourGains,{1.25f,.75f});
  assert(!ipa->applyIspControls(1,request,&update)&&update.valid);assert(!ipa->prepareParameters(1,1,update.revision,&bytes));
  ipa->parametersApplied(1,sof+2,update.revision);sof+=2;meta(sof);assert(metadata.get(controls::ColourTemperature));
  current=expected(*metadata.get(controls::ColourTemperature));packet(current);check(metadata,current);
  request.clear();request.set(controls::AwbEnable,true);request.set(controls::ColourCorrectionMatrix,Span<const float,9>(manual.matrix));request.set(controls::ColourTemperature,2850);
  apply(current);assert(metadata.get(controls::AwbEnable).value_or(false)&&metadata.get(controls::ColourTemperature)!=2850);
  request.clear();request.set(controls::AwbEnable,false);request.set(controls::ColourGains,{0.f,0.f});apply(current);assert(!metadata.get(controls::ColourTemperature));
  std::array<float,9> bad=manual.matrix;bad[0]=std::numeric_limits<float>::quiet_NaN();
  request.clear();request.set(controls::ColourCorrectionMatrix,Span<const float,9>(bad));assert(ipa->convertControls(1,request,&converted)==-ERANGE);
  bad[0]=16;request.set(controls::ColourCorrectionMatrix,Span<const float,9>(bad));assert(ipa->convertControls(1,request,&converted)==-ERANGE);
  const std::array<float,8> shortMatrix{};request.set(controls::ColourCorrectionMatrix.id(),ControlValue(Span<const float,8>(shortMatrix)));assert(ipa->convertControls(1,request,&converted)==-EINVAL);
 }else{request.clear();request.set(controls::ColourCorrectionMatrix,Span<const float,9>(manual.matrix));assert(ipa->convertControls(1,request,&converted)==-ENOTSUP);}
 Observation observation;ipa->statsProcessed.connect(&observation,&Observation::ready);
 auto *envelope=reinterpret_cast<v4l2_isp_buffer*>(stats);auto *histogram=reinterpret_cast<camss_stats_bhist*>(stats+sizeof(*envelope));
 envelope->version=V4L2_ISP_VERSION_V1;envelope->data_size=sizeof(*histogram);histogram->header={CAMSS_STATS_AEC_BHIST,0,sizeof(*histogram)};
 histogram->bins[256]=info.outputSize.width*info.outputSize.height/4;
 ipa->processStats(1,sof,2,sizeof(*envelope)+sizeof(*histogram),ipa::camss::SensorContext{true,500,512,0});assert(!observation.status);check(observation.metadata,current);
 ipa->stop();ipa->unmapBuffers({1,2});ipa.reset();dlclose(handle);
 std::cout<<"CCM_CONTRACT_PASS full-tree oracle, manual/CCT priority, delayed SOF, stats metadata and zero-gain fallback"<<std::endl;
}
