/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <chrono>
#include <condition_variable>
#include <csignal>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <linux/v4l2-subdev.h>
#include <fcntl.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <memory>
#include <mutex>
#include <vector>
#include <linux/dma-buf.h>
#include <linux/videodev2.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <libcamera/camera.h>
#include <libcamera/camera_manager.h>
#include <libcamera/control_ids.h>
#include <libcamera/formats.h>
#include <libcamera/framebuffer_allocator.h>
#include <libcamera/property_ids.h>
using namespace libcamera;
static volatile sig_atomic_t interrupted;
static void onSignal(int){interrupted=1;}
static bool readFrame(FrameBuffer *buffer,std::vector<uint8_t> *result) {
 if(buffer->planes().size()!=buffer->metadata().planes().size())return false;
 result->clear();
 for(size_t index=0;index<buffer->planes().size();++index){
 const auto &plane=buffer->planes()[index];size_t used=buffer->metadata().planes()[index].bytesused;
 if(!used || used>plane.length){std::cerr<<"LSC_PLANE_ERROR index="<<index<<" used="<<used<<" capacity="<<plane.length<<std::endl;return false;}
 dma_buf_sync sync{};sync.flags=DMA_BUF_SYNC_START|DMA_BUF_SYNC_READ;
 if(ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync))return false;
 size_t size=size_t(plane.offset)+plane.length;
 void *map=mmap(nullptr,size,PROT_READ,MAP_SHARED,plane.fd.get(),0);
 bool ok=map!=MAP_FAILED;
 if(ok){auto *data=static_cast<uint8_t*>(map)+plane.offset;result->insert(result->end(),data,data+used);munmap(map,size);}
 sync.flags=DMA_BUF_SYNC_END|DMA_BUF_SYNC_READ;
 if(ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync)||!ok)return false;
 }
 return !result->empty();
}
class Capture {
public:
 std::shared_ptr<Camera> camera;
 std::mutex mutex;std::condition_variable condition;
 bool running=false,done=false;unsigned frames=0,failed=0,phase=0;
 uint64_t lastTimestamp=0;std::vector<uint8_t> previous;
 std::vector<std::vector<uint8_t>> images;
 std::vector<int> targets;
 std::vector<std::array<float,9>> expected;
 const std::array<float,9> manual{0,0,1,0,.75f,0,1,0,0};
 void complete(Request *request) {
  std::lock_guard lock(mutex);
  if(!running || done || request->status()==Request::RequestCancelled)return;
  bool next=false;
  const int target=targets[phase];
  auto temperature=request->metadata().get(controls::ColourTemperature);
  auto gains=request->metadata().get(controls::ColourGains);
  auto awb=request->metadata().get(controls::AwbEnable);
  auto locked=request->metadata().get(controls::AwbLocked);
  auto matrix=request->metadata().get(controls::ColourCorrectionMatrix);
  bool matrixMatches=false;
  if(matrix && temperature && *temperature>=1500 && *temperature<=12000) {
   const auto &wanted=target==-2?manual:expected[*temperature-1500];
   matrixMatches=!std::memcmp(matrix->data(),wanted.data(),36);
  }
  const bool manualGain=gains && std::abs((*gains)[0]-1.25f)<.01f && std::abs((*gains)[1]-.75f)<.01f;
  const bool applied=matrixMatches && (target>0 ? temperature==target && awb==false : target==-1 ? temperature.has_value() && awb==true && locked==true : awb==false && (target!=-3 || manualGain));
  for(const auto &[stream,buffer]:request->buffers()) {
   (void)stream;const auto &m=buffer->metadata();std::vector<uint8_t> data;
   if(m.status!=FrameMetadata::FrameSuccess || !m.timestamp || m.timestamp<=lastTimestamp || !readFrame(buffer,&data))++failed;
   bool settled=applied && gains && m.sequence>=2 && !data.empty() && data==previous;
   if(applied)previous=data;else previous.clear();
   lastTimestamp=m.timestamp;
   std::cout<<"CCM_FRAME phase="<<phase<<" sequence="<<m.sequence<<" target="<<target<<" metadata="<<temperature.value_or(0)<<" settled="<<settled<<" awb="<<awb.value_or(false)<<" locked="<<locked.value_or(false);
   if(gains)std::cout<<" red="<<(*gains)[0]<<" blue="<<(*gains)[1];
   std::cout<<" matrix-match="<<matrixMatches;
   if(matrix){std::cout<<" matrix=";for(unsigned i=0;i<9;i++)std::cout<<(i?",":"")<<(*matrix)[i];}
   std::cout<<std::endl;
   if(settled) {
    images.push_back(std::move(data));
    if(++phase==targets.size())done=true;
    else {next=true;previous.clear();}
   }
  }
  ++frames;done|=failed!=0;
  if(!done) {
   request->reuse(Request::ReuseBuffers);request->controls().clear();
   if(next) {
    const int wanted=targets[phase];
    request->controls().set(controls::AwbEnable,wanted==-1);
    if(wanted>0)request->controls().set(controls::ColourTemperature,wanted);
    else if(wanted==-2)request->controls().set(controls::ColourCorrectionMatrix,Span<const float,9>(manual));
    else if(wanted==-3)request->controls().set(controls::ColourGains,{1.25f,.75f});
   }
   if(camera->queueRequest(request)){++failed;done=true;}
  }
  condition.notify_one();
 }
};
int main(int argc,char **argv) {
 if(argc!=8)return 2;
 std::ifstream expectedFile(argv[7],std::ios::binary);if(!expectedFile)return 2;
 std::cout<<std::setprecision(9);
 int selectedPattern=0;if(std::sscanf(argv[6],"%d",&selectedPattern)!=1 || selectedPattern<=0)return 2;
 unsigned ow=0,oh=0,sw=0,sh=0;
 if(std::sscanf(argv[4],"%ux%u",&ow,&oh)!=2 || std::sscanf(argv[5],"%ux%u",&sw,&sh)!=2 || !ow || !oh || !sw || !sh)return 2;
 const Size requested(ow,oh),sensorRequested(sw,sh);
 std::signal(SIGINT,onSignal);std::signal(SIGTERM,onSignal);
 CameraManager manager;if(manager.start())return 3;
 Capture capture;capture.targets=std::vector<int>{6500,2850,-2,6500,-3,-1};
 for(int kelvin=1500;kelvin<=12000;kelvin++) {
  std::array<char,40> packet;std::array<float,9> matrix;
  if(!expectedFile.read(packet.data(),40) || !expectedFile.read(reinterpret_cast<char*>(matrix.data()),36))return 2;
  capture.expected.push_back(matrix);
 }
for(auto &c:manager.cameras())if(c->properties().get(properties::Model).value_or("")==argv[1])capture.camera=c;
 if(!capture.camera || capture.camera->acquire())return 4;
 auto camera=capture.camera;
 struct Release{std::shared_ptr<Camera> camera;~Release(){camera->release();}}release{camera};
 auto config=camera->generateConfiguration({StreamRole::Viewfinder});if(!config)return 5;
 config->at(0).pixelFormat=formats::NV12;config->at(0).size=requested;
 SensorConfiguration sensorConfig;sensorConfig.bitDepth=10;sensorConfig.outputSize=sensorRequested;
 config->sensorConfig=sensorConfig;
 if(config->validate()==CameraConfiguration::Invalid || camera->configure(config.get()))return 5;
 const auto &format=config->at(0);
 if(format.size!=requested || format.pixelFormat!=formats::NV12)return 5;
 bool supported=camera->controls().find(&controls::ColourTemperature)!=camera->controls().end();
 if(!supported || camera->controls().find(&controls::ColourCorrectionMatrix)==camera->controls().end())return 5;
 std::cout<<"CCT_CONTROL supported="<<supported<<std::endl;
 std::cout<<"LSC_CONFIG stride="<<format.stride<<" frame-size="<<format.frameSize<<std::endl;
 int sensor=open(argv[2],O_RDWR|O_CLOEXEC);if(sensor<0)return 6;
 v4l2_subdev_format sensorFormat{};sensorFormat.which=V4L2_SUBDEV_FORMAT_ACTIVE;
 if(ioctl(sensor,VIDIOC_SUBDEV_G_FMT,&sensorFormat) || Size(sensorFormat.format.width,sensorFormat.format.height)!=sensorRequested){close(sensor);return 6;}
 std::cout<<"LSC_SENSOR width="<<sensorFormat.format.width<<" height="<<sensorFormat.format.height<<std::endl;
 v4l2_control pattern{V4L2_CID_TEST_PATTERN,0};
 if(ioctl(sensor,VIDIOC_G_CTRL,&pattern)){close(sensor);return 6;}
 struct Restore{int fd;v4l2_control old;~Restore(){ioctl(fd,VIDIOC_S_CTRL,&old);close(fd);}}restore{sensor,pattern};
 pattern.value=selectedPattern;if(ioctl(sensor,VIDIOC_S_CTRL,&pattern))return 6;
 v4l2_queryctrl patternInfo{};patternInfo.id=V4L2_CID_TEST_PATTERN;
 if(ioctl(sensor,VIDIOC_QUERYCTRL,&patternInfo))return 6;
 v4l2_querymenu patternName{};patternName.id=V4L2_CID_TEST_PATTERN;patternName.index=selectedPattern;
 if(ioctl(sensor,VIDIOC_QUERYMENU,&patternName))return 6;
 std::cout<<"LSC_PATTERN index="<<selectedPattern<<" maximum="<<patternInfo.maximum<<" name="<<patternName.name<<std::endl;
 FrameBufferAllocator allocator(camera);Stream *stream=format.stream();
 if(allocator.allocate(stream)<0)return 7;
 std::vector<std::unique_ptr<Request>> requests;
 for(const auto &buffer:allocator.buffers(stream)){
  auto request=camera->createRequest();if(!request || request->addBuffer(stream,buffer.get()))return 7;
  requests.push_back(std::move(request));
 }
 camera->requestCompleted.connect(&capture,&Capture::complete);
 ControlList initial(camera->controls());
 initial.set(controls::ExposureTimeMode,controls::ExposureTimeModeManual);
 initial.set(controls::AnalogueGainMode,controls::AnalogueGainModeManual);
 initial.set(controls::ExposureTime,5000);initial.set(controls::AnalogueGain,1.0f);
 initial.set(controls::AwbEnable,false);
 initial.set(controls::ColourTemperature,6500);
 if(camera->start(&initial))return 8;
 v4l2_control activePattern{V4L2_CID_TEST_PATTERN,0};
 if(ioctl(sensor,VIDIOC_S_CTRL,&activePattern)){camera->stop();return 8;}
 activePattern.value=selectedPattern;
 if(ioctl(sensor,VIDIOC_S_CTRL,&activePattern)){camera->stop();return 8;}
 std::cout<<"LSC_PATTERN_ACTIVE toggled=1"<<std::endl;
 {std::lock_guard lock(capture.mutex);capture.running=true;for(auto &request:requests)if(camera->queueRequest(request.get()))capture.failed++;}
 auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(15);
 {std::unique_lock lock(capture.mutex);while(!capture.done && !capture.failed && !interrupted && std::chrono::steady_clock::now()<deadline)capture.condition.wait_for(lock,std::chrono::milliseconds(100));capture.running=false;}
 int stopped=camera->stop();
 bool good=!stopped && !capture.failed && capture.done && capture.images.size()==capture.targets.size();
 if(good)for(size_t i=0;i<capture.images.size();++i) {
  const auto &data=capture.images[i];
  std::string path=std::string(argv[3])+"-phase"+std::to_string(i)+"-private.nv12";
  int out=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
  if(out<0){good=false;break;}
  size_t written=0;while(written<data.size()){ssize_t n=write(out,data.data()+written,data.size()-written);if(n<=0){good=false;break;}written+=n;}
  if(close(out))good=false;
 }
 std::cout<<"CCM_RESULT frames="<<capture.frames<<" phases="<<capture.images.size()<<" failed="<<!good<<" result="<<!good<<std::endl;
 return good?0:9;
}
