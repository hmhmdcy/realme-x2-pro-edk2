/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Actual request integration; no claim of absolute optical calibration. */
#include <array>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <csignal>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <libcamera/camera.h>
#include <libcamera/camera_manager.h>
#include <libcamera/control_ids.h>
#include <libcamera/formats.h>
#include <libcamera/framebuffer_allocator.h>
#include <libcamera/property_ids.h>
#include <linux/dma-buf.h>
#include <linux/v4l2-subdev.h>
#include <linux/videodev2.h>
#include <memory>
#include <mutex>
#include <set>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <vector>
using namespace libcamera;
static volatile sig_atomic_t interrupted;
static bool optical;
static void onSignal(int){interrupted=1;}
struct Policy {float ev;int32_t mode,period;bool awb;};
static constexpr std::array<Policy,1> policies{{{0,0,0,false}}};
static void setPolicy(ControlList &list,unsigned phase)
{
 const auto &p=policies.at(phase);list.set(controls::ExposureValue,p.ev);list.set(controls::AeFlickerMode,p.mode);
 list.set(controls::AwbEnable,optical);if(!optical)list.set(controls::ColourGains,{1.f,1.f});
}
static bool meanY(FrameBuffer *buffer,unsigned stride,unsigned width,unsigned height,double *mean)
{
 std::vector<uint8_t> data;
 if(buffer->planes().size()!=buffer->metadata().planes().size())return false;
 for(size_t index=0;index<buffer->planes().size();++index) {
  const auto &plane=buffer->planes()[index];size_t used=buffer->metadata().planes()[index].bytesused;
  if(!used||used>plane.length)return false;
  dma_buf_sync sync{};sync.flags=DMA_BUF_SYNC_START|DMA_BUF_SYNC_READ;if(ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync))return false;
  size_t size=size_t(plane.offset)+plane.length;void *map=mmap(nullptr,size,PROT_READ,MAP_SHARED,plane.fd.get(),0);
  bool ok=map!=MAP_FAILED;
  if(ok){const auto *p=static_cast<const uint8_t*>(map)+plane.offset;data.insert(data.end(),p,p+used);munmap(map,size);}
  sync.flags=DMA_BUF_SYNC_END|DMA_BUF_SYNC_READ;if(ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync)||!ok)return false;
 }
 if(stride<width||data.size()<size_t(stride)*height)return false;
 uint64_t sum=0;for(unsigned y=0;y<height;++y)for(unsigned x=0;x<width;++x)sum+=data[size_t(y)*stride+x];
 *mean=double(sum)/(uint64_t(width)*height);
 const char *folder=getenv("CAPTURE_DIR");if(!folder)return false;
 std::string path=std::string(folder)+"/frame-"+std::to_string(buffer->metadata().sequence)+".nv12";
 std::ofstream output(path,std::ios::binary);output.write(reinterpret_cast<const char*>(data.data()),data.size());
 std::cout<<"SAMPLE sequence="<<buffer->metadata().sequence<<" width="<<width<<" height="<<height<<" stride="<<stride<<" bytes="<<data.size()<<std::endl;
 return output.good();
}
class Capture {
public:
 std::shared_ptr<Camera> camera;
 std::mutex mutex;std::condition_variable condition;
 bool running=false,done=false;unsigned phase=0,matched=0,frames=0,failed=0,exposureChanges=0;
 unsigned lockedRun=0,lockedTotal=0;
 unsigned stride=0,width=0,height=0;uint64_t lastTimestamp=0;
 int32_t previousExposure=0;float previousGain=0;int sensor=-1;
 void complete(Request *request)
 {
  std::lock_guard lock(mutex);if(!running||done||request->status()==Request::RequestCancelled)return;
  auto p=policies[phase];p.awb=optical;const auto &metadata=request->metadata();
  auto ev=metadata.get(controls::ExposureValue);auto mode=metadata.get(controls::AeFlickerMode);auto period=metadata.get(controls::AeFlickerPeriod);
  auto exposure=metadata.get(controls::ExposureTime);auto gain=metadata.get(controls::AnalogueGain);auto awb=metadata.get(controls::AwbEnable);
  auto redBlue=metadata.get(controls::ColourGains);auto locked=metadata.get(controls::AwbLocked);auto kelvin=metadata.get(controls::ColourTemperature);
  auto matrix=metadata.get(controls::ColourCorrectionMatrix);
  bool applied=ev&&*ev==p.ev&&mode&&*mode==p.mode&&period&&*period==p.period&&awb&&*awb==p.awb;
  bool valid=exposure&&*exposure>0&&gain&&std::isfinite(*gain)&&*gain>0&&redBlue;
  bool next=false;
  for(const auto &[stream,buffer]:request->buffers()) {
   (void)stream;const auto &m=buffer->metadata();double mean=0;
   if(m.status!=FrameMetadata::FrameSuccess||!m.timestamp||m.timestamp<=lastTimestamp||!meanY(buffer,stride,width,height,&mean)||!valid)++failed;
   if(exposure&&gain&&previousExposure&&(*exposure!=previousExposure||*gain!=previousGain))++exposureChanges;
   previousExposure=exposure.value_or(0);previousGain=gain.value_or(0);lastTimestamp=m.timestamp;
   v4l2_control readExposure{V4L2_CID_EXPOSURE,0},readGain{V4L2_CID_ANALOGUE_GAIN,0};
   if(ioctl(sensor,VIDIOC_G_CTRL,&readExposure)||ioctl(sensor,VIDIOC_G_CTRL,&readGain))++failed;
   std::cout<<"ADAPT_FRAME phase="<<phase<<" request="<<request->sequence()<<" sequence="<<m.sequence<<" timestamp="<<m.timestamp
    <<" matched="<<applied<<" ev="<<ev.value_or(100)<<" flicker="<<mode.value_or(-1)<<" period="<<period.value_or(-1)
    <<" exposure="<<exposure.value_or(0)<<" gain="<<gain.value_or(0)<<" awb="<<awb.value_or(false)<<" locked="<<locked.value_or(false)
    <<" kelvin="<<kelvin.value_or(0)<<" read-lines="<<readExposure.value<<" read-code="<<readGain.value<<" mean-y="<<mean;
   if(redBlue)std::cout<<" red="<<(*redBlue)[0]<<" blue="<<(*redBlue)[1];
   if(matrix){std::cout<<" matrix=";for(unsigned i=0;i<9;++i)std::cout<<(i?",":"")<<(*matrix)[i];}
   std::cout<<std::endl;
   if(applied)++matched;else matched=0;
   if(applied && locked.value_or(false)){++lockedRun;++lockedTotal;}else lockedRun=0;
   if(matched>=240 || (matched>=24 && lockedRun>=8)){std::cout<<"ADAPT_PHASE phase="<<phase<<" request="<<request->sequence()<<" sequence="<<m.sequence<<std::endl;matched=0;if(++phase==policies.size())done=true;else next=true;}
  }
  ++frames;done|=failed!=0;
  if(!done) {
   request->reuse(Request::ReuseBuffers);request->controls().clear();if(next)setPolicy(request->controls(),phase);
   if(camera->queueRequest(request)){++failed;done=true;}
  }
  condition.notify_one();
 }
};
int main(int argc,char **argv)
{
 if(argc!=5 && argc!=6)return 2;
 unsigned ow=640,oh=480;if(argc==6 && std::sscanf(argv[5],"%ux%u",&ow,&oh)!=2)return 2;
 const Size requestedOutput(ow,oh);
 unsigned sw=0,sh=0;int patternIndex=0;
 if(std::sscanf(argv[3],"%ux%u",&sw,&sh)!=2||std::sscanf(argv[4],"%d",&patternIndex)!=1||patternIndex<0)return 2;
 optical=patternIndex==0;std::signal(SIGINT,onSignal);std::signal(SIGTERM,onSignal);std::cout<<std::setprecision(9)<<"ADAPT_PID value="<<getpid()<<std::endl;
 std::ifstream maps("/proc/self/maps");std::set<std::string> libraries;std::string mapLine;
 while(std::getline(maps,mapLine))if(mapLine.find("/libcamera")!=std::string::npos)libraries.insert(mapLine.substr(mapLine.find_last_of(' ')+1));
 for(const auto &library:libraries)std::cout<<"ADAPT_LIBRARY path="<<library<<std::endl;
 CameraManager manager;if(manager.start())return 3;
 Capture capture;
 for(auto &camera:manager.cameras())if(camera->properties().get(properties::Model).value_or("")==argv[1])capture.camera=camera;
 if(!capture.camera||capture.camera->acquire())return 4;
 auto camera=capture.camera;
 struct Release {std::shared_ptr<Camera> camera;~Release(){camera->release();}}release{camera};
 auto config=camera->generateConfiguration({StreamRole::Viewfinder});if(!config)return 5;
 config->at(0).pixelFormat=formats::NV12;config->at(0).size=requestedOutput;
 SensorConfiguration sensorConfig;sensorConfig.bitDepth=10;sensorConfig.outputSize=Size(sw,sh);config->sensorConfig=sensorConfig;
 if(config->validate()==CameraConfiguration::Invalid||camera->configure(config.get()))return 5;
 const auto &format=config->at(0);if(format.size!=requestedOutput||format.pixelFormat!=formats::NV12)return 5;
 for(const ControlId *id:{static_cast<const ControlId*>(&controls::ExposureValue),static_cast<const ControlId*>(&controls::AeFlickerMode),static_cast<const ControlId*>(&controls::AeFlickerPeriod),static_cast<const ControlId*>(&controls::AwbEnable)}) {
  const auto numeric=camera->controls().count(id->id()),pointer=camera->controls().count(id);
  std::cout<<"ADAPT_CONTROL name="<<id->name()<<" id="<<id->id()<<" numeric="<<numeric<<" pointer="<<pointer<<std::endl;
  if(!numeric)return 5;
 }
 capture.width=format.size.width;capture.height=format.size.height;capture.stride=format.stride;
 int sensor=open(argv[2],O_RDWR|O_CLOEXEC);if(sensor<0)return 6;
 capture.sensor=sensor;
 v4l2_subdev_format sensorFormat{};sensorFormat.which=V4L2_SUBDEV_FORMAT_ACTIVE;
 if(ioctl(sensor,VIDIOC_SUBDEV_G_FMT,&sensorFormat)||Size(sensorFormat.format.width,sensorFormat.format.height)!=Size(sw,sh))return 6;
 v4l2_queryctrl exposureInfo{},gainInfo{};exposureInfo.id=V4L2_CID_EXPOSURE;gainInfo.id=V4L2_CID_ANALOGUE_GAIN;
 v4l2_control blank{V4L2_CID_HBLANK,0},vertical{V4L2_CID_VBLANK,0},pattern{V4L2_CID_TEST_PATTERN,0};
 v4l2_ext_control pixel{};pixel.id=V4L2_CID_PIXEL_RATE;v4l2_ext_controls controlsInfo{};controlsInfo.count=1;controlsInfo.controls=&pixel;
 if(ioctl(sensor,VIDIOC_QUERYCTRL,&exposureInfo)||ioctl(sensor,VIDIOC_QUERYCTRL,&gainInfo)||ioctl(sensor,VIDIOC_G_CTRL,&blank)||ioctl(sensor,VIDIOC_G_CTRL,&vertical)||ioctl(sensor,VIDIOC_G_EXT_CTRLS,&controlsInfo)||ioctl(sensor,VIDIOC_G_CTRL,&pattern))return 6;
 struct Restore {int fd;v4l2_control old;~Restore(){ioctl(fd,VIDIOC_S_CTRL,&old);close(fd);}}restore{sensor,pattern};
 std::cout<<"ADAPT_SENSOR width="<<sw<<" height="<<sh<<" line-length="<<sw+blank.value<<" pixel-rate="<<pixel.value64<<" frame-length="<<sh+vertical.value
  <<" min-lines="<<exposureInfo.minimum<<" max-lines="<<exposureInfo.maximum<<" min-code="<<gainInfo.minimum<<" max-code="<<gainInfo.maximum<<std::endl;
 pattern.value=patternIndex;if(ioctl(sensor,VIDIOC_S_CTRL,&pattern))return 6;
 FrameBufferAllocator allocator(camera);Stream *stream=format.stream();if(allocator.allocate(stream)<0)return 7;
 std::vector<std::unique_ptr<Request>> requests;
 for(const auto &buffer:allocator.buffers(stream)){auto request=camera->createRequest();if(!request||request->addBuffer(stream,buffer.get()))return 7;requests.push_back(std::move(request));}
 camera->requestCompleted.connect(&capture,&Capture::complete);ControlList initial(camera->controls());
 initial.set(controls::ExposureTimeMode,optical?controls::ExposureTimeModeAuto:controls::ExposureTimeModeManual);initial.set(controls::AnalogueGainMode,optical?controls::AnalogueGainModeAuto:controls::AnalogueGainModeManual);
 initial.set(controls::ExposureTime,5000);initial.set(controls::AnalogueGain,1.f);setPolicy(initial,0);
 int started=camera->start(&initial);std::cout<<"START_STATUS status="<<started<<std::endl;if(started)return 8;
 v4l2_control activePattern{V4L2_CID_TEST_PATTERN,0};
 if(ioctl(sensor,VIDIOC_S_CTRL,&activePattern)){camera->stop();return 8;}activePattern.value=patternIndex;
 if(ioctl(sensor,VIDIOC_S_CTRL,&activePattern)){camera->stop();return 8;}
 {std::lock_guard lock(capture.mutex);capture.running=true;for(auto &request:requests)if(camera->queueRequest(request.get()))++capture.failed;}
 auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(20);
 {std::unique_lock lock(capture.mutex);while(!capture.done&&!capture.failed&&!interrupted&&std::chrono::steady_clock::now()<deadline)capture.condition.wait_for(lock,std::chrono::milliseconds(100));capture.running=false;}
 int stopped=camera->stop();bool good=!stopped&&!capture.failed&&capture.done&&capture.phase==policies.size();
 std::cout<<"AWB_STEADY_RESULT locked-frames="<<capture.lockedTotal<<" final-locked-run="<<capture.lockedRun<<std::endl;
 std::cout<<"ADAPT_RESULT frames="<<capture.frames<<" phases="<<capture.phase<<" exposure-changes="<<capture.exposureChanges<<" failed="<<!good<<" result="<<!good<<std::endl;
 return good?0:9;
}
