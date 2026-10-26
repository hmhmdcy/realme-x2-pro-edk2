/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Exercise public libcamera RAW-only, processed-only and dual-stream requests. */
#include <chrono>
#include <condition_variable>
#include <csignal>
#include <cstring>
#include <cstdlib>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>
#include <linux/dma-buf.h>
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
static void stopSignal(int){interrupted=1;}
static bool sample(FrameBuffer *buffer,bool prefill,uint64_t *hash=nullptr) {
 if(buffer->planes().empty())return false;
 const auto &plane=buffer->planes()[0];
 dma_buf_sync sync{};sync.flags=prefill?DMA_BUF_SYNC_START|DMA_BUF_SYNC_WRITE:DMA_BUF_SYNC_START|DMA_BUF_SYNC_READ;
 if(ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync))return false;
 const size_t length=size_t(plane.offset)+plane.length;
 void *mapping=mmap(nullptr,length,prefill?PROT_READ|PROT_WRITE:PROT_READ,MAP_SHARED,plane.fd.get(),0);
 bool valid=mapping!=MAP_FAILED;
 if(valid) {
  auto *data=static_cast<unsigned char *>(mapping)+plane.offset;
  if(prefill)std::memset(data,0xa5,plane.length);
  else {
   uint64_t value=1469598103934665603ULL;unsigned changed=0;
   size_t used=std::min<size_t>(plane.length,buffer->metadata().planes()[0].bytesused);
   for(size_t i=0;i<used;i+=std::max<size_t>(1,used/4096)){value=(value^data[i])*1099511628211ULL;changed+=data[i]!=0xa5;}
   valid=changed>0;if(hash)*hash=value;
  }
  munmap(mapping,length);
 }
 sync.flags=prefill?DMA_BUF_SYNC_END|DMA_BUF_SYNC_WRITE:DMA_BUF_SYNC_END|DMA_BUF_SYNC_READ;
 return !ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync) && valid;
}
class Capture {
public:
 std::shared_ptr<Camera> camera;
 std::mutex mutex;std::condition_variable condition;
 bool running=false,done=false,hold=false,heldOnce=false;
 bool af=false,cancel=false,triggered=false,scanning=false,cancelled=false;
 int32_t afState=-1;
 std::vector<Request *> parked;
 unsigned frames=0,failed=0,stable=0,targetFrames=6;
 int32_t lastExposure=0;float lastGain=0;
 std::map<const Stream *,uint64_t> timestamps;
 void complete(Request *request) {
  std::lock_guard lock(mutex);
  if(!running || request->status()==Request::RequestCancelled)return;
  auto exposure=request->metadata().get(controls::ExposureTime);
  auto gain=request->metadata().get(controls::AnalogueGain);
  auto white=request->metadata().get(controls::ColourGains);
  bool locked=request->metadata().get(controls::AwbLocked).value_or(false);
  if(!exposure || !gain || !white || *exposure<=0 || *gain<=0)++failed;
  if(exposure && gain) {
   stable=locked && *exposure==lastExposure && *gain==lastGain?stable+1:0;
   lastExposure=*exposure;lastGain=*gain;
  }
  if(af) {
   auto state=request->metadata().get(controls::AfState);
   auto fom=request->metadata().get(controls::FocusFoM);
   if(!state || !fom || *fom<0)++failed;
   if(state) {
    afState=*state;scanning |= *state==controls::AfStateScanning;
    if(scanning && !cancel && *state==controls::AfStateFailed)++failed;
   }
  }
  for(const auto &[stream,buffer]:request->buffers()) {
   const auto &frame=buffer->metadata();unsigned bytes=0;
   for(const auto &plane:frame.planes())bytes+=plane.bytesused;
   if(frame.status!=FrameMetadata::FrameSuccess || !frame.timestamp || frame.timestamp<=timestamps[stream] || !bytes)++failed;
   if(stream->configuration().pixelFormat==formats::NV12 &&
      request->metadata().get(controls::SensorTimestamp).value_or(0)!=int64_t(frame.timestamp))++failed;
   timestamps[stream]=frame.timestamp;
   uint64_t hash=0;if(!sample(buffer,false,&hash))++failed;
   std::cout<<"RAW_IMAGE request="<<request->sequence()<<" format="<<stream->configuration().pixelFormat
    <<" sequence="<<frame.sequence<<" timestamp="<<frame.timestamp<<" bytes="<<bytes<<" status="<<frame.status<<" sample-hash="<<hash;
   if(exposure && gain)std::cout<<" exposure-us="<<*exposure<<" gain="<<*gain;
   std::cout<<" awb-locked="<<locked<<std::endl;
  }
  ++frames;
  done=failed || (af ? scanning && ((!cancel && afState==controls::AfStateFocused) ||
                 (cancel && cancelled && afState==controls::AfStateIdle)) :
                 frames>=targetFrames && (!hold || heldOnce));
  if(!done) {
   if(hold && !heldOnce) {parked.push_back(request);condition.notify_one();return;}
   request->reuse(Request::ReuseBuffers);request->controls().clear();
   if(af && !triggered && stable>=8) {
    request->controls().set(controls::AfTrigger,controls::AfTriggerStart);triggered=true;
    std::cout<<"RAW_AF_TRIGGER action=start"<<std::endl;
   } else if(af && cancel && scanning && !cancelled) {
    request->controls().set(controls::AfTrigger,controls::AfTriggerCancel);cancelled=true;
    std::cout<<"RAW_AF_TRIGGER action=cancel"<<std::endl;
   }
   if(camera->queueRequest(request)) {++failed;done=true;}
  }
  condition.notify_one();
 }
};
int main(int argc,char **argv) {
 if(argc!=3)return 2;
 std::signal(SIGINT,stopSignal);std::signal(SIGTERM,stopSignal);
 std::cout<<"APPLICATION_PROCESS pid="<<getpid()<<std::endl;
 CameraManager manager;if(manager.start())return 3;
 Capture capture;std::string model=argv[1];const std::string kind=argv[2];
 if(const char *limit=std::getenv("RAW_TARGET_FRAMES")){capture.targetFrames=std::stoul(limit);if(capture.targetFrames<6 || capture.targetFrames>256)return 2;}
 Size selectedSize;
 if(auto position=model.find('@');position!=std::string::npos) {
  const std::string size=model.substr(position+1);model.resize(position);
  auto separator=size.find('x');if(separator==std::string::npos)return 2;
  selectedSize=Size(std::stoul(size.substr(0,separator)),std::stoul(size.substr(separator+1)));
 }
 capture.hold=kind=="hold";capture.af=kind.starts_with("af");capture.cancel=kind=="afcancel";
 for(auto &camera:manager.cameras())if(camera->properties().get(properties::Model).value_or("")==model)capture.camera=camera;
 if(!capture.camera || capture.camera->acquire())return 4;
 auto camera=capture.camera;
 struct Release {std::shared_ptr<Camera> camera;~Release(){camera->release();}} release{camera};
 std::vector<StreamRole> roles;
 if(kind!="pix")roles.push_back(StreamRole::Raw);
 if(kind!="raw" && kind!="afraw")roles.push_back(StreamRole::Viewfinder);
 auto config=camera->generateConfiguration(roles);if(!config)return 5;
 if(!selectedSize.isNull()) {
  config->sensorConfig=SensorConfiguration{};
  config->sensorConfig->bitDepth=10;config->sensorConfig->outputSize=selectedSize;
 }
 for(auto &stream:*config)if(stream.pixelFormat==formats::NV12)stream.size=Size(640,480);
 if(config->validate()==CameraConfiguration::Invalid || camera->configure(config.get()))return 5;
 FrameBufferAllocator allocator(camera);std::vector<Stream *> streams;
 for(auto &configuration:*config) {
  Stream *stream=configuration.stream();streams.push_back(stream);
  std::cout<<"RAW_CONFIG "<<configuration.toString()<<std::endl;
  if(allocator.allocate(stream)<0)return 6;
  for(const auto &buffer:allocator.buffers(stream))if(!sample(buffer.get(),true))return 6;
 }
 const size_t count=allocator.buffers(streams.front()).size();
 std::vector<std::unique_ptr<Request>> requests;
 for(size_t i=0;i<count;++i) {
  auto request=camera->createRequest();if(!request)return 7;
  for(Stream *stream:streams)if(allocator.buffers(stream).size()!=count || request->addBuffer(stream,allocator.buffers(stream)[i].get()))return 7;
  requests.push_back(std::move(request));
 }
 camera->requestCompleted.connect(&capture,&Capture::complete);
 capture.running=true;int result=camera->start()?8:0;
 for(auto &request:requests)if(!result && camera->queueRequest(request.get()))result=9;
 {
  std::unique_lock lock(capture.mutex);auto end=std::chrono::steady_clock::now()+std::chrono::seconds(capture.af?45:15);
  while(!result && !capture.done && !interrupted && std::chrono::steady_clock::now()<end) {
   if(capture.hold && !capture.heldOnce && capture.parked.size()==count) {
    std::cout<<"RAW_BUFFER_HOLD count="<<count<<std::endl;
    lock.unlock();std::this_thread::sleep_for(std::chrono::milliseconds(120));lock.lock();
    capture.heldOnce=true;capture.stable=0;
    for(Request *request:capture.parked) {
     request->reuse(Request::ReuseBuffers);request->controls().clear();
     if(camera->queueRequest(request))result=9;
    }
    capture.parked.clear();
    std::cout<<"RAW_BUFFER_RESUME"<<std::endl;
   }
   capture.condition.wait_for(lock,std::chrono::milliseconds(100));
  }
  if(!capture.done || capture.failed)result=10;
  capture.running=false;
 }
 if(camera->stop() && !result)result=11;
 std::cout<<"RAW_RESULT model="<<model<<" kind="<<kind<<" frames="<<capture.frames<<" stable="<<capture.stable
  <<" failed="<<capture.failed<<" result="<<result<<" held="<<capture.heldOnce
  <<" af-state="<<capture.afState<<" af-triggered="<<capture.triggered<<" af-scanning="<<capture.scanning<<" af-cancelled="<<capture.cancelled<<std::endl;
 return result;
}
