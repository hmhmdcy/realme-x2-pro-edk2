// Public API only. Exercise mode transitions without mapping or storing pixels.
#include <libcamera/libcamera.h>
#include <libcamera/formats.h>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

using namespace libcamera;
static void check(bool value, const char *why) { if (!value) throw std::runtime_error(why); }
struct Frame {
    unsigned int phase, request, buffer;
    uint64_t timestamp;
    int exposure, exposureMode, gainMode;
    float gain;
};
class Observer {
public:
    void setPhase(unsigned int phase) { std::lock_guard lock(mutex_); phase_=phase; }
    void complete(Request *request) {
        std::lock_guard lock(mutex_);
        if (request->status()==Request::RequestCancelled) {bad_=true;ready_.notify_all();return;}
        const auto &buffer=request->buffers().begin()->second->metadata();
        const auto &metadata=request->metadata();
        auto exposure=metadata.get(controls::ExposureTime);
        auto gain=metadata.get(controls::AnalogueGain);
        auto exposureMode=metadata.get(controls::ExposureTimeMode);
        auto gainMode=metadata.get(controls::AnalogueGainMode);
        if (buffer.status!=FrameMetadata::FrameSuccess || !exposure || !gain || !exposureMode || !gainMode || *exposure<=0 || *gain<1)
            bad_=true;
        else frames.push_back({phase_,request->sequence(),buffer.sequence,buffer.timestamp,*exposure,*exposureMode,*gainMode,*gain});
        ready_.notify_all();
    }
    bool wait(size_t count) {std::unique_lock lock(mutex_);return ready_.wait_for(lock,std::chrono::seconds(10),[&]{return bad_ || frames.size()>=count;}) && !bad_;}
    std::vector<Frame> frames;
private:
    std::mutex mutex_;
    std::condition_variable ready_;
    unsigned int phase_=0;
    bool bad_=false;
};
int main(int argc, char **argv)
{
    if (argc!=4) return 2;
    bool raw=std::string(argv[1])=="raw";
    unsigned int width=std::stoul(argv[2]),height=std::stoul(argv[3]);
    if (!((raw && width==1928 && height==1088)||(raw && width==2304 && height==1728)||(!raw && width==1920 && height==1088)||(!raw && width==2296 && height==1728))) return 2;
    CameraManager manager;
    std::shared_ptr<Camera> camera;
    std::unique_ptr<CameraConfiguration> configuration;
    std::unique_ptr<FrameBufferAllocator> allocator;
    std::vector<std::unique_ptr<Request>> requests;
    Observer observer;
    bool acquired=false,streaming=false;
    int status=1;
    try {
        check(manager.start()==0,"manager");
        camera=manager.get("/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10");
        check(camera && camera->acquire()==0,"acquire");acquired=true;
        configuration=camera->generateConfiguration({raw?StreamRole::Raw:StreamRole::Viewfinder});
        check(configuration && configuration->size()==1,"configuration");
        auto &cfg=configuration->at(0);cfg.size={width,height};cfg.pixelFormat=raw?formats::SRGGB10_CSI2P:formats::RGB888;cfg.bufferCount=4;
        check(configuration->validate()!=CameraConfiguration::Invalid && cfg.size==Size(width,height) && cfg.pixelFormat==(raw?formats::SRGGB10_CSI2P:formats::RGB888),"native geometry");
        check(camera->configure(configuration.get())==0,"configure");
        for (const ControlId *id:std::vector<const ControlId *>{&controls::AeEnable,&controls::ExposureTimeMode,&controls::AnalogueGainMode,&controls::ExposureTime,&controls::AnalogueGain})
            check(camera->controls().count(id->id())==1,"standard control missing");
        allocator=std::make_unique<FrameBufferAllocator>(camera);check(allocator->allocate(cfg.stream())==4,"four buffers");
        for (const auto &buffer:allocator->buffers(cfg.stream())) {
            auto request=camera->createRequest();check(request && request->addBuffer(cfg.stream(),buffer.get())==0,"request");requests.push_back(std::move(request));
        }
        camera->requestCompleted.connect(&observer,&Observer::complete);
        ControlList initial(camera->controls());initial.set(controls::AeEnable,false);initial.set(controls::ExposureTime,3000);initial.set(controls::AnalogueGain,2.0f);
        check(camera->start(&initial)==0,"start with controls");streaming=true;
        bool used=false;
        auto phase=[&](unsigned int number,const ControlList &controls,unsigned int groups=4) {
            observer.setPhase(number);size_t start=observer.frames.size();
            for (unsigned int group=0;group<groups;++group) {
                if (used) std::this_thread::sleep_for(std::chrono::milliseconds(180));
                for (size_t i=0;i<requests.size();++i) {
                    auto &request=requests[i];if (used || group) request->reuse(Request::ReuseBuffers);
                    if (!group && !i) request->controls().merge(controls);
                    check(camera->queueRequest(request.get())==0,"queue");
                }
                used=true;check(observer.wait(start+(group+1)*4),"capture timeout or missing metadata");
            }
        };
        ControlList empty(camera->controls());
        phase(0,empty,2);
        for (const auto &f:observer.frames) check(f.exposureMode==controls::ExposureTimeModeManual && f.gainMode==controls::AnalogueGainModeManual && std::abs(f.exposure-3000)<=20 && std::abs(f.gain-2)<0.01,"start controls not applied before first capture");
        phase(1,empty);
        ControlList controls(camera->controls());controls.set(controls::ExposureTime,5000);controls.set(controls::AnalogueGain,3.0f);phase(2,controls);
        auto tail=[&](unsigned int number,int exposureMode,int gainMode,int exposure=-1,float gain=-1) {
            size_t count=0;
            for (auto it=observer.frames.rbegin();it!=observer.frames.rend() && it->phase==number && count<4;++it,++count) {
                check(it->exposureMode==exposureMode && it->gainMode==gainMode,"mode did not settle");
                if (exposure>0) check(std::abs(it->exposure-exposure)<=20,"manual exposure did not settle");
                if (gain>0) check(std::abs(it->gain-gain)<0.02,"manual gain did not settle");
            }
            check(count==4,"missing settled frames");
        };
        tail(2,controls::ExposureTimeModeManual,controls::AnalogueGainModeManual,5000,3);
        controls=ControlList(camera->controls());controls.set(controls::AeEnable,true);controls.set(controls::ExposureTime,15000);controls.set(controls::AnalogueGain,7.0f);phase(3,controls);
        tail(3,controls::ExposureTimeModeAuto,controls::AnalogueGainModeAuto);
        check(std::abs(observer.frames.back().gain-7)>0.2,"manual gain retained during Auto");
        controls=ControlList(camera->controls());controls.set(controls::AeEnable,false);phase(4,controls);
        tail(4,controls::ExposureTimeModeManual,controls::AnalogueGainModeManual);
        const auto frozen=observer.frames.back();
        for (size_t i=observer.frames.size()-4;i<observer.frames.size();++i) check(observer.frames[i].exposure==frozen.exposure && observer.frames[i].gain==frozen.gain,"manual freeze not stable");
        controls=ControlList(camera->controls());controls.set(controls::AeEnable,false);controls.set(controls::ExposureTimeMode,controls::ExposureTimeModeAuto);controls.set(controls::AnalogueGain,2.0f);controls.set(controls::ExposureTime,8000);phase(5,controls);
        tail(5,controls::ExposureTimeModeAuto,controls::AnalogueGainModeManual,-1,2);
        controls=ControlList(camera->controls());controls.set(controls::AeEnable,true);controls.set(controls::ExposureTimeMode,controls::ExposureTimeModeManual);controls.set(controls::ExposureTime,4000);controls.set(controls::AnalogueGain,14.0f);phase(6,controls);
        tail(6,controls::ExposureTimeModeManual,controls::AnalogueGainModeAuto,4000);
        check(std::abs(observer.frames.back().gain-14)>0.2,"manual gain retained in mixed Auto");
        controls=ControlList(camera->controls());controls.set(controls::AeEnable,true);controls.set(controls::ExposureTimeMode,controls::ExposureTimeModeManual);controls.set(controls::AnalogueGainMode,controls::AnalogueGainModeManual);controls.set(controls::ExposureTime,2500);controls.set(controls::AnalogueGain,1.5f);phase(7,controls);
        tail(7,controls::ExposureTimeModeManual,controls::AnalogueGainModeManual,2500,1.5);
        check(camera->stop()==0,"stop");streaming=false;
        check(camera->start()==0,"restart without controls");streaming=true;
        phase(8,empty,2);tail(8,controls::ExposureTimeModeAuto,controls::AnalogueGainModeAuto);
        check(camera->stop()==0,"final stop");streaming=false;
        std::cout << "{\"width\":" << width << ",\"height\":" << height << ",\"stride\":" << cfg.stride << ",\"phases\":9,\"passed\":true,\"frames\":[";
        bool first=true;
        for (const auto &f:observer.frames) {
            std::cout << (first?"":",") << "{\"phase\":" << f.phase << ",\"request_sequence\":" << f.request << ",\"buffer_sequence\":" << f.buffer << ",\"timestamp_ns\":" << f.timestamp << ",\"exposure_us\":" << f.exposure << ",\"gain\":" << std::setprecision(9) << f.gain << ",\"exposure_mode\":" << f.exposureMode << ",\"gain_mode\":" << f.gainMode << "}";first=false;
        }
        std::cout << "]}\n";status=0;
    } catch (const std::exception &error) {std::cerr << error.what() << '\n';}
    if (streaming) camera->stop();
    if (camera) camera->requestCompleted.disconnect(&observer);
    requests.clear();allocator.reset();configuration.reset();
    if (acquired) camera->release();
    camera.reset();manager.stop();return status;
}
