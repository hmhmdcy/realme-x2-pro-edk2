/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Standard Auto AF requests on the hardware processed stream. */
#include <chrono>
#include <condition_variable>
#include <csignal>
#include <iostream>
#include <memory>
#include <mutex>
#include <vector>
#include <unistd.h>
#include <libcamera/camera.h>
#include <libcamera/camera_manager.h>
#include <libcamera/control_ids.h>
#include <libcamera/formats.h>
#include <libcamera/framebuffer_allocator.h>
#include <libcamera/property_ids.h>
using namespace libcamera;
static volatile sig_atomic_t interrupted;
static void stopSignal(int){interrupted=1;}
class Capture {
public:
 std::shared_ptr<Camera> camera;
 std::mutex mutex;std::condition_variable condition;
 bool running=false,done=false,triggered=false,scanning=false,cancel=false,cancelled=false;
 unsigned frames=0,failed=0,stable=0,nextRequest=4;int32_t previousExposure=0,lastState=-1;float previousGain=0;
 void complete(Request *request) {
  std::lock_guard lock(mutex);
  if (!running || request->status()==Request::RequestCancelled) return;
  auto state=request->metadata().get(controls::AfState);
  auto mode=request->metadata().get(controls::AfMode);
  auto fom=request->metadata().get(controls::FocusFoM);
  auto exposure=request->metadata().get(controls::ExposureTime);
  auto gain=request->metadata().get(controls::AnalogueGain);
  auto white=request->metadata().get(controls::ColourGains);
  const bool locked=request->metadata().get(controls::AwbLocked).value_or(false);
  if (!state || !mode || !fom || !exposure || !gain || !white || *mode!=controls::AfModeAuto || *fom<0) ++failed;
  if (exposure && gain) {
   stable=locked && *exposure==previousExposure && *gain==previousGain?stable+1:0;
   previousExposure=*exposure;previousGain=*gain;
  }
  for (const auto &[stream,buffer]:request->buffers()) {
   (void)stream;
   const auto &frame=buffer->metadata();
   if (frame.status!=FrameMetadata::FrameSuccess || !frame.timestamp) ++failed;
   std::cout<<"AF_IMAGE request="<<request->sequence()<<" sof="<<frame.sequence<<" timestamp="<<frame.timestamp;
   if(state)std::cout<<" state="<<*state;
   if(fom)std::cout<<" fom="<<*fom;
   if(exposure && gain)std::cout<<" exposure_us="<<*exposure<<" gain="<<*gain;
   if(white)std::cout<<" red="<<(*white)[0]<<" blue="<<(*white)[1];
   std::cout<<std::endl;
  }
  ++frames;
  if (state) {
   lastState=*state;
   if (*state==controls::AfStateScanning) scanning=true;
   if (scanning && ((!cancel && (*state==controls::AfStateFocused || *state==controls::AfStateFailed)) ||
                    (cancel && cancelled && *state==controls::AfStateIdle))) done=true;
  }
  if (!done && !failed) {
   request->reuse(Request::ReuseBuffers);request->controls().clear();
   if (!triggered && stable>=8) {
    request->controls().set(controls::AfMode,controls::AfModeAuto);
    request->controls().set(controls::AfTrigger,controls::AfTriggerStart);triggered=true;
    std::cout<<"AF_TRIGGER request="<<nextRequest<<" action=start"<<std::endl;
   } else if (cancel && scanning && !cancelled) {
    request->controls().set(controls::AfTrigger,controls::AfTriggerCancel);cancelled=true;
    std::cout<<"AF_TRIGGER request="<<nextRequest<<" action=cancel"<<std::endl;
   }
   ++nextRequest;
   if (camera->queueRequest(request)) ++failed;
  }
  condition.notify_one();
 }
};
int main(int argc,char **argv) {
 if (argc!=2) return 2;
 std::signal(SIGINT,stopSignal);std::signal(SIGTERM,stopSignal);
 std::cout<<"APPLICATION_PROCESS pid="<<getpid()<<std::endl;
 CameraManager manager;if(manager.start())return 3;
 Capture capture;capture.cancel=std::string(argv[1])=="cancel";
 for(auto &camera:manager.cameras())if(camera->properties().get(properties::Model).value_or("")=="s5kgw1")capture.camera=camera;
 if(!capture.camera || capture.camera->acquire())return 4;
 auto camera=capture.camera;
 struct Release {std::shared_ptr<Camera> camera;~Release(){camera->release();}} release{camera};
 auto config=camera->generateConfiguration({StreamRole::Viewfinder});if(!config)return 5;
 config->at(0).size=Size(640,480);config->at(0).pixelFormat=formats::NV12;
 if(config->validate()==CameraConfiguration::Invalid || camera->configure(config.get()))return 5;
 if(camera->controls().find(&controls::AfMode)==camera->controls().end())return 6;
 FrameBufferAllocator allocator(camera);Stream *stream=config->at(0).stream();
 if(allocator.allocate(stream)<0)return 7;
 std::vector<std::unique_ptr<Request>> requests;
 for(const auto &buffer:allocator.buffers(stream)) {
  auto request=camera->createRequest();if(!request || request->addBuffer(stream,buffer.get()))return 8;
  requests.push_back(std::move(request));
 }
 camera->requestCompleted.connect(&capture,&Capture::complete);
 capture.running=true;int result=camera->start()?9:0;
 for(const auto &request:requests)if(!result && camera->queueRequest(request.get()))result=10;
 {
  std::unique_lock lock(capture.mutex);auto end=std::chrono::steady_clock::now()+std::chrono::seconds(45);
  while(!result && !capture.done && !capture.failed && !interrupted && std::chrono::steady_clock::now()<end)
   capture.condition.wait_for(lock,std::chrono::milliseconds(100));
  if(!capture.done || capture.failed || interrupted)result=11;
  capture.running=false;
 }
 int stopped=camera->stop();if(stopped)result=12;
 requests.clear();allocator.free(stream);
 std::cout<<"AF_RESULT frames="<<capture.frames<<" failed="<<capture.failed<<" state="<<capture.lastState
          <<" triggered="<<capture.triggered<<" scanning="<<capture.scanning<<" cancelled="<<capture.cancelled<<" result="<<result<<std::endl;
 return result;
}
