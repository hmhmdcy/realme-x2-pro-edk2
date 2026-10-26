// Public libcamera API only. Keep streaming across request gaps; never map pixels.
#include <libcamera/libcamera.h>
#include <libcamera/formats.h>
#include <chrono>
#include <condition_variable>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

using namespace libcamera;
static void check(bool value, const char *message)
{
    if (!value) throw std::runtime_error(message);
}
struct Record {
    unsigned int request, buffer;
    uint64_t timestamp;
    int exposure;
    float gain;
};
class Capture {
public:
    explicit Capture(bool raw) : raw_(raw) {}
    void completed(Request *request)
    {
        if (request->status() == Request::RequestCancelled) return;
        std::lock_guard lock(mutex);
        const auto &buffer = request->buffers().begin()->second->metadata();
        auto exposure = request->metadata().get(controls::ExposureTime);
        auto gain = request->metadata().get(controls::AnalogueGain);
        if (buffer.status != FrameMetadata::FrameSuccess || (!raw_ && (!exposure || !gain)))
            failed = true;
        else records.push_back({ request->sequence(), buffer.sequence, buffer.timestamp, exposure.value_or(-1), gain.value_or(-1.0f) });
        ready.notify_all();
    }
    bool wait(size_t count)
    {
        std::unique_lock lock(mutex);
        return ready.wait_for(lock, std::chrono::seconds(8), [&] { return failed || records.size() >= count; }) && !failed;
    }
    std::vector<Record> records;
private:
    bool raw_;
    std::mutex mutex;
    std::condition_variable ready;
    bool failed = false;
};
int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    const bool raw = std::string(argv[1]) == "raw";
    const unsigned int width = std::stoul(argv[2]), height = std::stoul(argv[3]);
    if (!((raw && width == 1928 && height == 1088) || (raw && width == 2304 && height == 1728) || (!raw && width == 1920 && height == 1088) || (!raw && width == 2296 && height == 1728))) return 2;
    CameraManager manager;
    std::shared_ptr<Camera> camera;
    std::unique_ptr<FrameBufferAllocator> allocator;
    std::unique_ptr<CameraConfiguration> configuration;
    std::vector<std::unique_ptr<Request>> requests;
    Capture capture(raw);
    bool acquired = false, streaming = false;
    int status = 1;
    try {
        check(manager.start() == 0, "camera manager");
        camera = manager.get("/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10");
        check(camera && camera->acquire() == 0, "acquire camera"); acquired = true;
        configuration = camera->generateConfiguration({ raw ? StreamRole::Raw : StreamRole::Viewfinder });
        check(configuration && configuration->size() == 1, "configuration");
        auto &cfg = configuration->at(0);
        cfg.size = { width, height }; cfg.pixelFormat = raw ? formats::SRGGB10_CSI2P : formats::RGB888; cfg.bufferCount = 4;
        check(configuration->validate() != CameraConfiguration::Invalid && cfg.size == Size(width, height) && cfg.pixelFormat == (raw ? formats::SRGGB10_CSI2P : formats::RGB888), "native output geometry");
        check(camera->configure(configuration.get()) == 0, "configure camera");
        allocator = std::make_unique<FrameBufferAllocator>(camera);
        check(allocator->allocate(cfg.stream()) == 4, "allocate four buffers");
        for (const auto &buffer : allocator->buffers(cfg.stream())) {
            auto request = camera->createRequest();
            check(request && request->addBuffer(cfg.stream(), buffer.get()) == 0, "request buffer");
            requests.push_back(std::move(request));
        }
        camera->requestCompleted.connect(&capture, &Capture::completed);
        check(camera->start() == 0, "start camera"); streaming = true;
        for (size_t group = 0; group < 4; group++) {
            if (group) std::this_thread::sleep_for(std::chrono::milliseconds(500));
            for (auto &request : requests) {
                if (group) request->reuse(Request::ReuseBuffers);
                check(camera->queueRequest(request.get()) == 0, "queue request");
            }
            check(capture.wait((group + 1) * 4), "finite capture timeout or invalid metadata");
        }
        check(camera->stop() == 0, "stop camera"); streaming = false;
        std::cout << "{\"width\":" << width << ",\"height\":" << height << ",\"stride\":" << cfg.stride << ",\"frames\":[";
        bool first = true;
        for (const auto &r : capture.records) {
            std::cout << (first ? "" : ",") << "{\"request_sequence\":" << r.request
                      << ",\"buffer_sequence\":" << r.buffer << ",\"timestamp_ns\":" << r.timestamp << ",\"exposure_us\":" << r.exposure
                      << ",\"gain\":" << std::setprecision(9) << r.gain << "}";
            first = false;
        }
        std::cout << "]}\n"; status = 0;
    } catch (const std::exception &error) { std::cerr << error.what() << '\n'; }
    if (streaming) camera->stop();
    if (camera) camera->requestCompleted.disconnect(&capture);
    requests.clear(); allocator.reset(); configuration.reset();
    if (acquired) camera->release();
    camera.reset(); manager.stop();
    return status;
}
