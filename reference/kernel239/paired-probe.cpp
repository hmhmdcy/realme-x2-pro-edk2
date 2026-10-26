// Finite physical-camera RAM statistics. No pixels are written to files/stdout.
// Exact OF ID, Model and subdevice entity are checked before acquisition.
#include <libcamera/libcamera.h>
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

class PatternGuard {
public:
    explicit PatternGuard(const char *path, int selected)
    {
        fd_ = open(path, O_RDWR | O_CLOEXEC);
        require(fd_ >= 0, "open sensor subdev");
        v4l2_control control{};
        control.id = V4L2_CID_TEST_PATTERN;
        if (ioctl(fd_, VIDIOC_G_CTRL, &control) != 0) {
            close(fd_);
            fd_ = -1;
            throw std::runtime_error("read original sensor pattern");
        }
        original_ = control.value;
        try {
            require(original_ == 0, "sensor pattern must initially be disabled");
            control.value = selected;
            require(ioctl(fd_, VIDIOC_S_CTRL, &control) == 0, "enable sensor color bars");
            control.value = -1;
            require(ioctl(fd_, VIDIOC_G_CTRL, &control) == 0 && control.value == selected,
                    "sensor color bars readback");
        } catch (...) {
            control.value = original_;
            ioctl(fd_, VIDIOC_S_CTRL, &control);
            close(fd_);
            fd_ = -1;
            throw;
        }
    }

    bool restore()
    {
        if (fd_ < 0) return true;
        v4l2_control control{};
        control.id = V4L2_CID_TEST_PATTERN;
        control.value = original_;
        bool ok = ioctl(fd_, VIDIOC_S_CTRL, &control) == 0;
        control.value = -1;
        ok = ioctl(fd_, VIDIOC_G_CTRL, &control) == 0 && control.value == original_ && ok;
        if (ok) { close(fd_); fd_ = -1; }
        return ok;
    }
    ~PatternGuard() { if (!restore()) std::cerr << "ERROR: sensor pattern restore failed\n"; if (fd_ >= 0) close(fd_); }

private:
    int fd_ = -1;
    int original_ = 0;
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
    static void manual(ControlList &controls)
    {
        controls.set(controls::AeEnable, false);
        controls.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
        controls.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
        controls.set(controls::ExposureTime, 2000);
        controls.set(controls::AnalogueGain, 1.0f);
    }
    int queue(Request *request)
    {
        { std::lock_guard lock(queueMutex_);
          if (nextQueued_ >= 12) return 0;
          indices_[request] = nextQueued_++; manual(request->controls()); }
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
        { std::lock_guard lock(mutex_); if (failed_ || frames_.size() >= 12) return; }
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
        require(std::abs(*exposure - 2000) <= 20 && std::abs(*gain - 1.0f) < 0.03f &&
                *exposureMode == controls::ExposureTimeModeManual && *gainMode == controls::AnalogueGainModeManual,
                "paired fixed physical controls");
        ReadMapping rawMap(rawIt->second), rgbMap(rgbIt->second);
        require(rawMap.bytes == size_t(raw_.stride) * raw_.size.height && raw_.stride >= raw_.size.width / 4 * 5,
                "packed RAW10 active rows and padding");
        require(rgbMap.bytes == size_t(rgb_.stride) * rgb_.size.height && rgb_.stride >= rgb_.size.width * 3,
                "RGB active rows and padding");
        Measurement rawStats, rgbStats;
        for (unsigned int y = 0; y < raw_.size.height; ++y) {
            const auto *line = rawMap.pixels + size_t(y) * raw_.stride;
            for (unsigned int x = 0; x < raw_.size.width; ++x) rawStats.add(raw10(line, x));
        }
        for (unsigned int y = 0; y < rgb_.size.height; ++y) {
            const auto *line = rgbMap.pixels + size_t(y) * rgb_.stride;
            for (unsigned int x = 0; x < rgb_.size.width * 3; ++x) rgbStats.add(line[x]);
        }
        rawMap.finish(); rgbMap.finish();
        std::ostringstream out;
        out << "{\"queued_index\":" << index << ",\"sequence\":" << cm.sequence << ",\"timestamp_ns\":" << cm.timestamp
            << ",\"raw_sequence\":" << rm.sequence << ",\"raw_timestamp_ns\":" << rm.timestamp
            << ",\"sensor_timestamp_ns\":" << request->metadata().get(controls::SensorTimestamp).value_or(-1)
            << ",\"exposure_us\":" << *exposure << ",\"analogue_gain\":" << *gain
            << ",\"exposure_mode\":" << *exposureMode << ",\"gain_mode\":" << *gainMode
            << ",\"all_zero\":" << (rgbStats.maximum == 0 ? "true" : "false")
            << ",\"raw\":" << rawStats.json(true) << ",\"rgb\":" << rgbStats.json(false) << '}';
        bool again;
        { std::lock_guard lock(mutex_);
          require(index == frames_.size(), "paired request order is contiguous");
          require(frames_.empty() || (cm.sequence > lastSequence_ && cm.timestamp > lastTimestamp_), "paired metadata increases");
          lastSequence_ = cm.sequence; lastTimestamp_ = cm.timestamp;
          frames_.push_back(out.str()); again = frames_.size() < 12; ready_.notify_all(); }
        if (again) { request->reuse(Request::ReuseBuffers); require(queue(request) == 0, "queue next paired request"); }
    }
    bool wait()
    {
        std::unique_lock lock(mutex_);
        return ready_.wait_for(lock, std::chrono::seconds(45), [this] { return frames_.size() == 12 || failed_; }) && !failed_;
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
    if (argc == 2 && std::string(argv[1]) == "--self-test") {
        const uint8_t wire[] = {0x00, 0x01, 0x02, 0xff, 0xe4};
        const std::array<unsigned int, 4> expected = {0, 5, 10, 1023};
        for (unsigned int i = 0; i < 4; ++i) require(raw10(wire, i) == expected[i], "MIPI RAW10 known wire vector");
        std::cout << "{\"raw10_known_wire_vector_passed\":true}\n"; return 0;
    }
    if (argc != 9 || std::string(argv[2]) != "/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10" ||
        std::string(argv[3]) != "imx319" || std::string(argv[4]) != "imx319 7-0010" ||
        std::string(argv[5]) != "rgb" || std::string(argv[6]) != "1624" ||
        std::string(argv[7]) != "1224" || std::string(argv[8]) != "1") return 2;
    CameraManager manager;
    std::shared_ptr<Camera> camera;
    std::unique_ptr<FrameBufferAllocator> allocator;
    std::unique_ptr<PairedCapture> capture;
    std::unique_ptr<PatternGuard> pattern;
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
            require(!camera && candidate->properties().get(properties::Model).value_or("") == "imx319", "unique paired physical model");
            camera = candidate;
        }
        require(bool(camera) && camera->acquire() == 0, "acquire paired physical camera"); acquired = true;
        auto config = camera->generateConfiguration({StreamRole::Viewfinder, StreamRole::Raw});
        require(config && config->size() == 2, "generate processed and RAW streams together");
        auto &rgb = config->at(0), &raw = config->at(1);
        rgb.size = {1624, 1224}; rgb.pixelFormat = formats::RGB888; rgb.bufferCount = 4;
        raw.size = {1632, 1224}; raw.pixelFormat = formats::SRGGB10_CSI2P; raw.bufferCount = 4;
        require(config->validate() != CameraConfiguration::Invalid && config->size() == 2 &&
                rgb.size == Size(1624,1224) && raw.size == Size(1632,1224) &&
                rgb.pixelFormat == formats::RGB888 && raw.pixelFormat == formats::SRGGB10_CSI2P,
                "exact paired format and dimensions retained");
        require(camera->configure(config.get()) == 0, "configure paired streams");
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
        pattern = std::make_unique<PatternGuard>(argv[1], 0);
        capture = std::make_unique<PairedCapture>(camera, rgb, raw);
        camera->requestCompleted.connect(capture.get(), &PairedCapture::completed);
        ControlList initial(camera->controls()); PairedCapture::manual(initial);
        require(camera->start(&initial) == 0, "start fixed paired streams"); started = true;
        for (auto &request : requests) require(capture->queue(request.get()) == 0, "queue initial paired request");
        const bool complete = capture->wait();
        require(camera->stop() == 0, "stop paired capture"); started = false;
        camera->requestCompleted.disconnect(capture.get());
        require(pattern->restore(), "restore paired sensor pattern"); pattern.reset();
        require(complete, "twelve complete same-request RAW/RGB pairs"); status = 0;
    } catch (const std::exception &error) { std::cerr << "ERROR: " << error.what() << '\n'; }
    if (started && camera->stop() != 0) status = 1;
    if (camera && capture) camera->requestCompleted.disconnect(capture.get());
    if (pattern && !pattern->restore()) status = 1;
    pattern.reset(); requests.clear(); allocator.reset();
    if (acquired && camera->release() != 0) status = 1;
    if (capture) capture->print();
    capture.reset(); camera.reset(); manager.stop(); return status;
}
