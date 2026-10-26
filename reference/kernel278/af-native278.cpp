// Finite physical-camera RAM statistics. No pixels are written to files/stdout.
// Exact OF ID, Model and subdevice entity are checked before acquisition.
#include <libcamera/libcamera.h>
#include "focus_stats.h"
#include <libcamera/formats.h>
#include <linux/videodev2.h>
#include <linux/dma-buf.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <iostream>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>
#include <map>

using namespace libcamera;

static bool automaticMode = false;
static std::string scenario = "scan";
static bool finishing = false;
static unsigned int requestedFrames = 96;


static void require(bool ok, const char *message)
{
    if (!ok)
        throw std::runtime_error(message);
}

class DmaReadGuard {
public:
    explicit DmaReadGuard(int fd) : fd_(fd)
    {
        dma_buf_sync sync{};
        sync.flags = DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ;
        active_ = ioctl(fd_, DMA_BUF_IOCTL_SYNC, &sync) == 0;
    }
    bool valid() const { return active_; }
    bool finish()
    {
        if (!active_) return false;
        dma_buf_sync sync{};
        sync.flags = DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ;
        bool success = ioctl(fd_, DMA_BUF_IOCTL_SYNC, &sync) == 0;
        active_ = false;
        return success;
    }
    ~DmaReadGuard() { if (active_) finish(); }
private:
    int fd_;
    bool active_ = false;
};



static unsigned int raw10(const uint8_t *line, unsigned int x)
{
    const unsigned int group = x / 4 * 5, lane = x % 4;
    return (unsigned(line[group + lane]) << 2) | ((line[group + 4] >> (lane * 2)) & 3);
}

class ReadMapping {
public:
    explicit ReadMapping(const FrameBuffer *buffer)
        : plane_(onePlane(buffer)), sync_(plane_.fd.get())
    {
        require(buffer->planes().size() == 1 && buffer->metadata().planes().size() == 1, "one plane per paired stream");
        require(buffer->metadata().status == FrameMetadata::FrameSuccess, "paired FrameSuccess");
        require(sync_.valid(), "DMA read begin");
        bytes = buffer->metadata().planes()[0].bytesused;
        require(bytes && bytes <= plane_.length, "valid bytesused");
        map_ = mmap(nullptr, plane_.offset + plane_.length, PROT_READ, MAP_SHARED, plane_.fd.get(), 0);
        require(map_ != MAP_FAILED, "map paired buffer");
        pixels = static_cast<const uint8_t *>(map_) + plane_.offset;
    }
    void finish()
    {
        if (map_ != MAP_FAILED) {
            const bool ok = munmap(map_, plane_.offset + plane_.length) == 0;
            map_ = MAP_FAILED;
            require(ok, "unmap paired buffer");
        }
        require(sync_.finish(), "DMA read end");
    }
    ~ReadMapping() { if (map_ != MAP_FAILED) munmap(map_, plane_.offset + plane_.length); }
    const uint8_t *pixels = nullptr;
    size_t bytes = 0;
private:
    static const FrameBuffer::Plane &onePlane(const FrameBuffer *buffer)
    {
        require(buffer->planes().size() == 1, "one paired DMA plane before access");
        return buffer->planes()[0];
    }
    const FrameBuffer::Plane &plane_;
    DmaReadGuard sync_;
    void *map_ = MAP_FAILED;
};

struct Measurement {
    uint64_t count = 0, sum = 0, squares = 0;
    unsigned int minimum = 1023, maximum = 0;
    std::array<uint64_t, 1024> histogram{};
    void add(unsigned int value)
    {
        require(value < histogram.size(), "sample bit depth");
        ++count; sum += value; squares += value * value;
        minimum = std::min(minimum, value); maximum = std::max(maximum, value);
        ++histogram[value];
    }
    std::string json(bool raw) const
    {
        require(count > 0, "nonempty complete active image");
        const double mean = double(sum) / count;
        std::ostringstream out;
        out << "{\"samples\":" << count << ",\"min\":" << minimum << ",\"max\":" << maximum
            << ",\"mean\":" << mean << ",\"stddev\":"
            << std::sqrt(std::max(0.0, double(squares) / count - mean * mean))
            << ",\"all_zero\":" << (maximum == 0 ? "true" : "false") << ",\"histogram\":[";
        bool first = true;
        for (unsigned int i = 0; i < histogram.size(); ++i) {
            if (!histogram[i]) continue;
            if (!first) out << ',';
            first = false; out << '[' << i << ',' << histogram[i] << ']';
        }
        out << ']';
        if (raw) {
            out << ",\"high8_histogram\":["; first = true;
            for (unsigned int i = 0; i < 256; ++i) {
                uint64_t n = 0;
                for (unsigned int low = 0; low < 4; ++low) n += histogram[i * 4 + low];
                if (!n) continue;
                if (!first) out << ',';
                first = false; out << '[' << i << ',' << n << ']';
            }
            out << ']';
        }
        out << '}'; return out.str();
    }
};

class PairedCapture {
public:
    PairedCapture(std::shared_ptr<Camera> camera, const StreamConfiguration &rgb, const StreamConfiguration &raw)
        : camera_(camera), rgb_(rgb), raw_(raw) {}
    static void manual(ControlList &controls, unsigned int index = 0)
    {
        controls.set(controls::AeEnable, false);
        controls.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
        controls.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
        controls.set(controls::ExposureTime, 32000);
        controls.set(controls::AnalogueGain, 1.0f);
        controls.set(controls::AfMode, controls::AfModeAuto);
        if (scenario != "idle" && (index == 8 || (scenario == "retrigger" && index == 60)))
            controls.set(controls::AfTrigger, controls::AfTriggerStart);
        if ((scenario == "cancel" || scenario == "retrigger") && index == 24)
            controls.set(controls::AfTrigger, controls::AfTriggerCancel);
    }
    int queue(Request *request)
    {
        { std::lock_guard lock(queueMutex_);
          if (nextQueued_ >= requestedFrames) return 0;
          indices_[request] = nextQueued_++; manual(request->controls(), indices_[request]); }
        return camera_->queueRequest(request);
    }
    void completed(Request *request)
    {
        try { checked(request); }
        catch (const std::exception &error) {
            std::cerr << "ERROR: paired callback: " << error.what() << '\n';
            std::lock_guard lock(mutex_); failed_ = true; ready_.notify_all();
        }
    }
    void checked(Request *request)
    {
        if (request->status() == Request::RequestCancelled) return;
        { std::lock_guard lock(mutex_); if (failed_ || frames_.size() >= requestedFrames) return; }
        require(request->status() == Request::RequestComplete && request->buffers().size() == 2, "two complete paired buffers");
        auto rawIt = request->buffers().find(raw_.stream()), rgbIt = request->buffers().find(rgb_.stream());
        require(rawIt != request->buffers().end() && rgbIt != request->buffers().end(), "exact paired stream identities");
        const auto &rm = rawIt->second->metadata(), &cm = rgbIt->second->metadata();
        require(rm.sequence == cm.sequence && rm.timestamp == cm.timestamp, "same source sequence and timestamp");
        unsigned int index;
        { std::lock_guard lock(queueMutex_); index = indices_.at(request); }
        auto exposure = request->metadata().get(controls::ExposureTime);
        auto gain = request->metadata().get(controls::AnalogueGain);
        auto exposureMode = request->metadata().get(controls::ExposureTimeMode);
        auto gainMode = request->metadata().get(controls::AnalogueGainMode);
        require(exposure && gain && exposureMode && gainMode, "paired captured metadata");
        require(*exposure > 0 && *gain >= 1.0f && *gain <= 32.0f, "bounded physical controls");
        require(*exposureMode == (automaticMode ? controls::ExposureTimeModeAuto : controls::ExposureTimeModeManual) &&
                *gainMode == (automaticMode ? controls::AnalogueGainModeAuto : controls::AnalogueGainModeManual),
                "captured control modes");
        if (index >= 12)
            require(std::abs(*exposure - 32000) <= 40 && std::abs(*gain - 1) < .03f,
                    "fixed AF test exposure/gain");
        auto afState = request->metadata().get(controls::AfState);
        auto afMode = request->metadata().get(controls::AfMode);
        require(afState && afMode && *afMode == controls::AfModeAuto, "standard AF state/mode metadata");
        if (scenario == "idle" || index < 8 || ((scenario == "cancel" || scenario == "retrigger") && index >= 24 && index < 60))
            require(*afState == controls::AfStateIdle, "no scan before trigger or after cancel");
        ReadMapping rawMap(rawIt->second), rgbMap(rgbIt->second);
        require(rawMap.bytes == size_t(raw_.stride) * raw_.size.height && raw_.stride >= raw_.size.width / 4 * 5,
                "packed RAW10 active rows and padding");
        require(rgbMap.bytes == size_t(rgb_.stride) * rgb_.size.height && rgb_.stride >= rgb_.size.width * 3,
                "RGB active rows and padding");
        auto begin = std::chrono::steady_clock::now();
        auto focus = measureBayerFocus(rawMap.pixels, rawMap.bytes, raw_.size.width, raw_.size.height,
                                      raw_.stride, (raw_.size.width-rgb_.size.width)/2,
                                      (raw_.size.height-rgb_.size.height)/2, rgb_.size.width,
                                      rgb_.size.height, {10,true,true,false});
        auto fom = focus.figureOfMerit();
        require(focus.valid && fom.has_value(), "valid RAW focus statistics");
        auto microseconds = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-begin).count();
        rawMap.finish(); rgbMap.finish();
        std::ostringstream out;
        out << "{\"queued_index\":" << index << ",\"sequence\":" << cm.sequence << ",\"timestamp_ns\":" << cm.timestamp
            << ",\"raw_sequence\":" << rm.sequence << ",\"raw_timestamp_ns\":" << rm.timestamp
            << ",\"exposure_us\":" << *exposure << ",\"analogue_gain\":" << *gain
            << ",\"focus_fom\":" << *fom << ",\"measurement_us\":" << microseconds << ",\"regions\":[";
        bool first = true;
        for (const auto &region : focus.regions) {
            if (!first) out << ',';
            first = false;
            out << "{\"energy\":" << region.energy << ",\"sum\":" << region.sum << ",\"samples\":" << region.samples << '}';
        }
        out << "],\"metadata_focus_fom\":";
        if (auto value = request->metadata().get(controls::FocusFoM)) out << *value;
        else out << "null";
        out << ",\"af_state\":" << *afState << ",\"af_mode\":" << *afMode << '}';
        if ((scenario == "scan" || (scenario == "retrigger" && index >= 60)) &&
            (*afState == controls::AfStateFocused || *afState == controls::AfStateFailed)) {
            std::scoped_lock lock(queueMutex_,mutex_);
            if (!finishing) { requestedFrames = std::min(requestedFrames,index+13); finishing = true; }
        }        bool again;
        { std::lock_guard lock(mutex_);
          require(index == frames_.size(), "paired request order is contiguous");
          require(frames_.empty() || (cm.sequence > lastSequence_ && cm.timestamp > lastTimestamp_), "paired metadata increases");
          lastSequence_ = cm.sequence; lastTimestamp_ = cm.timestamp;
          frames_.push_back(out.str()); again = frames_.size() < requestedFrames; ready_.notify_all(); }
        if (again) { request->reuse(Request::ReuseBuffers); require(queue(request) == 0, "queue next paired request"); }
    }
    bool wait()
    {
        std::unique_lock lock(mutex_);
        return ready_.wait_for(lock, std::chrono::seconds(180), [this] { return frames_.size() == requestedFrames || failed_; }) && !failed_;
    }
    void print() const
    {
        std::cout << "{\"width\":" << rgb_.size.width << ",\"height\":" << rgb_.size.height << ",\"stride\":" << rgb_.stride
                  << ",\"raw_width\":" << raw_.size.width << ",\"raw_height\":" << raw_.size.height << ",\"raw_stride\":" << raw_.stride
                  << ",\"frames\":[";
        for (size_t i = 0; i < frames_.size(); ++i) { if (i) std::cout << ','; std::cout << frames_[i]; }
        std::cout << "]}\n";
    }
private:
    std::shared_ptr<Camera> camera_;
    StreamConfiguration rgb_, raw_;
    std::mutex queueMutex_, mutex_;
    std::condition_variable ready_;
    std::map<Request *, unsigned int> indices_;
    unsigned int nextQueued_ = 0, lastSequence_ = 0;
    uint64_t lastTimestamp_ = 0;
    bool failed_ = false;
    std::vector<std::string> frames_;
};

int main(int argc, char **argv)
{
    if (argc == 2 && std::string(argv[1]) == "--support") {
        CameraManager manager; if (manager.start()) return 1;
        auto camera=manager.get("/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10");
        if (!camera) return 2;
        std::cout << "{\"af_mode\":" << (camera->controls().count(&controls::AfMode)?"true":"false")
                  << ",\"af_trigger\":" << (camera->controls().count(&controls::AfTrigger)?"true":"false")
                  << ",\"af_state\":" << (camera->controls().count(&controls::AfState)?"true":"false") << "}\n";
        camera.reset(); manager.stop(); return 0;
    }

    if (argc == 2 && std::string(argv[1]) == "--self-test") {
        const uint8_t wire[] = {0x00, 0x01, 0x02, 0xff, 0xe4};
        const std::array<unsigned int, 4> expected = {0, 5, 10, 1023};
        for (unsigned int i = 0; i < 4; ++i) require(raw10(wire, i) == expected[i], "MIPI RAW10 known wire vector");
        std::cout << "{\"raw10_known_wire_vector_passed\":true}\n"; return 0;
    }
    if (argc != 10 || std::string(argv[2]) != "/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10" ||
        std::string(argv[3]) != "s5kgw1" || std::string(argv[4]) != "s5kgw1 6-0010" ||
        std::string(argv[5]) != "rgb" || std::string(argv[6]) != "2048" ||
        std::string(argv[7]) != "1536" || (std::string(argv[8]) != "manual" && std::string(argv[8]) != "auto")) return 2;
    automaticMode = std::string(argv[8]) == "auto";
    scenario = argv[9];
    if (scenario != "idle" && scenario != "scan" && scenario != "cancel" && scenario != "retrigger" && scenario != "stop") return 2;
    requestedFrames = scenario == "idle" ? 48 : scenario == "cancel" ? 72 : scenario == "stop" ? 36 : 900;
    CameraManager manager;
    std::shared_ptr<Camera> camera;
    std::unique_ptr<FrameBufferAllocator> allocator;
    std::unique_ptr<PairedCapture> capture;
    std::vector<std::unique_ptr<Request>> requests;
    bool acquired = false, started = false;
    int status = 1;
    try {
        const auto node = std::filesystem::path(argv[1]).filename();
        require(std::string(argv[1]) == "/dev/" + node.string() && node.string().starts_with("v4l-subdev"), "paired subdevice path");
        std::ifstream entityFile(std::filesystem::path("/sys/class/video4linux") / node / "name");
        std::string entity; std::getline(entityFile, entity);
        require(entity == argv[4], "paired exact physical sensor entity");
        require(std::filesystem::canonical(std::filesystem::path("/sys/class/video4linux") / node / "device/of_node").string() ==
                "/sys/firmware/devicetree" + std::string(argv[2]), "paired exact OF path");
        require(manager.start() == 0, "start paired camera manager");
        for (auto candidate : manager.cameras()) if (candidate->id() == argv[2]) {
            require(!camera && candidate->properties().get(properties::Model).value_or("") == "s5kgw1", "unique paired physical model");
            camera = candidate;
        }
        require(bool(camera) && camera->acquire() == 0, "acquire paired physical camera"); acquired = true;
        auto config = camera->generateConfiguration({StreamRole::Viewfinder, StreamRole::Raw});
        require(config && config->size() == 2, "generate processed and RAW streams together");
        auto &rgb = config->at(0), &raw = config->at(1);
        rgb.size = {2048, 1536}; rgb.pixelFormat = formats::RGB888; rgb.bufferCount = 4;
        raw.size = {4608, 3456}; raw.pixelFormat = formats::SGBRG10_CSI2P; raw.bufferCount = 4;
        require(config->validate() != CameraConfiguration::Invalid && config->size() == 2 &&
                rgb.size == Size(2048,1536) && raw.size == Size(4608,3456) &&
                rgb.pixelFormat == formats::RGB888 && raw.pixelFormat == formats::SGBRG10_CSI2P,
                "exact paired format and dimensions retained");
        require(camera->configure(config.get()) == 0, "configure paired streams");
        require(camera->controls().count(&controls::FocusFoM) == 1, "standard FocusFoM advertised");
        allocator = std::make_unique<FrameBufferAllocator>(camera);
        require(allocator->allocate(rgb.stream()) >= 0 && allocator->allocate(raw.stream()) >= 0, "allocate both paired streams");
        const auto &rgbBuffers = allocator->buffers(rgb.stream()), &rawBuffers = allocator->buffers(raw.stream());
        require(rgbBuffers.size() >= 4 && rawBuffers.size() >= 4, "four matched buffer pairs");
        for (unsigned int i = 0; i < 4; ++i) {
            auto request = camera->createRequest();
            require(request && request->addBuffer(rgb.stream(), rgbBuffers[i].get()) == 0 &&
                    request->addBuffer(raw.stream(), rawBuffers[i].get()) == 0, "same request paired buffers");
            requests.push_back(std::move(request));
        }
        capture = std::make_unique<PairedCapture>(camera, rgb, raw);
        camera->requestCompleted.connect(capture.get(), &PairedCapture::completed);
        ControlList initial(camera->controls()); PairedCapture::manual(initial);
        require(camera->start(&initial) == 0, "start fixed paired streams"); started = true;
        for (auto &request : requests) require(capture->queue(request.get()) == 0, "queue initial paired request");
        const bool complete = capture->wait();
        require(camera->stop() == 0, "stop paired capture"); started = false;
        camera->requestCompleted.disconnect(capture.get());
        require(complete, "all planned same-request RAW/RGB pairs"); status = 0;
    } catch (const std::exception &error) { std::cerr << "ERROR: " << error.what() << '\n'; }
    if (started && camera->stop() != 0) status = 1;
    if (camera && capture) camera->requestCompleted.disconnect(capture.get());
    requests.clear(); allocator.reset();
    if (acquired && camera->release() != 0) status = 1;
    if (capture) capture->print();
    capture.reset(); camera.reset(); manager.stop(); return status;
}
