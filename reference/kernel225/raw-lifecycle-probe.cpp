// Public API: reconfigure one camera; cancel pending RAW/RGB requests.
#include <libcamera/libcamera.h>
#include <libcamera/formats.h>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <tuple>
#include <vector>
using namespace libcamera;
static void check(bool ok, const char *why) { if (!ok) throw std::runtime_error(why); }
struct Value { int exposure; float gain; };
struct Phase { bool raw; unsigned int width, height, cancelled; std::vector<Value> values; };
class Observer {
public:
    void reset() { std::lock_guard lock(mutex_); check(!pending_, "pending request before configure"); values.clear(); cancelled=0; bad_=false; }
    void expect(unsigned int count) { std::lock_guard lock(mutex_); pending_+=count; }
    void complete(Request *request) {
        std::lock_guard lock(mutex_);
        if (!pending_) { bad_=true; ready_.notify_all(); return; }
        --pending_;
        if (request->status()==Request::RequestCancelled) ++cancelled;
        else {
            const auto &buffer=request->buffers().begin()->second->metadata();
            auto exposure=request->metadata().get(controls::ExposureTime);
            auto gain=request->metadata().get(controls::AnalogueGain);
            if (buffer.status!=FrameMetadata::FrameSuccess || !exposure || !gain || *exposure<=0 || *gain<1) bad_=true;
            else values.push_back({*exposure,*gain});
        }
        ready_.notify_all();
    }
    bool wait() { std::unique_lock lock(mutex_); return ready_.wait_for(lock,std::chrono::seconds(10),[&]{return !pending_ || bad_;}) && !bad_; }
    bool stopped() { std::lock_guard lock(mutex_); return !pending_ && !bad_ && cancelled>0; }
    unsigned int cancelled=0;
    std::vector<Value> values;
private:
    std::mutex mutex_;
    std::condition_variable ready_;
    unsigned int pending_=0;
    bool bad_=false;
};
int main()
{
    CameraManager manager;
    std::shared_ptr<Camera> camera;
    std::unique_ptr<CameraConfiguration> configuration;
    std::unique_ptr<FrameBufferAllocator> allocator;
    std::vector<std::unique_ptr<Request>> requests;
    std::vector<Phase> phases;
    Observer observer;
    bool acquired=false,streaming=false;
    int result=1;
    try {
        check(manager.start()==0,"manager");
        camera=manager.get("/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10");
        check(camera && camera->acquire()==0,"camera acquire");acquired=true;
        camera->requestCompleted.connect(&observer,&Observer::complete);
        for (const auto &[raw,width,height] : std::vector<std::tuple<bool,unsigned int,unsigned int>>{{true,1928,1088},{false,1920,1088},{true,2304,1728},{false,2296,1728},{true,1928,1088}}) {
            observer.reset();
            configuration=camera->generateConfiguration({raw?StreamRole::Raw:StreamRole::Viewfinder});
            check(configuration && configuration->size()==1,"configuration");
            auto &cfg=configuration->at(0);cfg.size={width,height};cfg.pixelFormat=raw?formats::SRGGB10_CSI2P:formats::RGB888;cfg.bufferCount=4;
            check(configuration->validate()!=CameraConfiguration::Invalid && cfg.size==Size(width,height) && cfg.pixelFormat==(raw?formats::SRGGB10_CSI2P:formats::RGB888),"native format");
            check(camera->configure(configuration.get())==0,"configure");
            allocator=std::make_unique<FrameBufferAllocator>(camera);check(allocator->allocate(cfg.stream())==4,"allocate");
            for (const auto &buffer:allocator->buffers(cfg.stream())) {
                auto request=camera->createRequest();check(request && request->addBuffer(cfg.stream(),buffer.get())==0,"request");requests.push_back(std::move(request));
            }
            check(camera->start()==0,"start");streaming=true;
            observer.expect(4);for (auto &request:requests) check(camera->queueRequest(request.get())==0,"queue");
            check(observer.wait() && observer.values.size()==4,"metadata completion");
            observer.expect(4);for (auto &request:requests) {request->reuse(Request::ReuseBuffers);check(camera->queueRequest(request.get())==0,"requeue");}
            check(camera->stop()==0,"stop");streaming=false;check(observer.stopped(),"cancelled requests not drained");
            phases.push_back({raw,width,height,observer.cancelled,observer.values});
            requests.clear();allocator.reset();configuration.reset();
        }
        std::cout << "{\"width\":0,\"height\":0,\"stride\":0,\"phases\":[";
        bool first=true;
        for (const auto &p:phases) {
            std::cout << (first?"":",") << "{\"raw\":" << (p.raw?"true":"false") << ",\"width\":" << p.width << ",\"height\":" << p.height << ",\"completed\":" << p.values.size() << ",\"cancelled\":" << p.cancelled << "}";first=false;
        }
        std::cout << "],\"frames\":[";first=true;
        for (const auto &p:phases) for (const auto &v:p.values) {
            std::cout << (first?"":",") << "{\"exposure_us\":" << v.exposure << ",\"gain\":" << v.gain << "}";first=false;
        }
        std::cout << "]}\n";result=0;
    } catch (const std::exception &error) {std::cerr << error.what() << '\n';}
    if (streaming) camera->stop();
    if (camera) camera->requestCompleted.disconnect(&observer);
    requests.clear();allocator.reset();configuration.reset();
    if (acquired) camera->release();
    camera.reset();manager.stop();return result;
}
