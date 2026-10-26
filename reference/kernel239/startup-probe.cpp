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

struct FrameStats {
    unsigned int sequence;
    unsigned int queuedIndex;
    int exposure, exposureMode, gainMode;
    float gain;
    std::array<unsigned int, 3> quantiles;
    double saturatedFraction;
    uint64_t timestamp;
    int64_t sensorTimestamp;
    uint64_t bytesUsed;
    unsigned int minimum;
    unsigned int maximum;
    double mean;
    double standardDeviation;
    bool allZero;
    unsigned int occupiedBins;
    double belowBlack64Fraction;
    double changedFraction;
    std::array<double, 4> bayerMean;
    std::array<double, 8> horizontalMean;
    std::string ipaMetadataJson;
};

class Capture {
public:
    Capture(std::shared_ptr<Camera> camera, bool raw, const StreamConfiguration &cfg, unsigned int cfaCell)
        : camera_(camera), raw_(raw), width_(cfg.size.width), height_(cfg.size.height), stride_(cfg.stride), cfaCell_(cfaCell), stream_(cfg.stream()) {}

    static void manual(ControlList &list, [[maybe_unused]] unsigned int phase)
    {
        list.set(controls::AeEnable, false);
        list.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
        list.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
        list.set(controls::ExposureTime, 2000);
        list.set(controls::AnalogueGain, 1.0f);
    }
    int queue(Request *request)
    {
        {
            std::lock_guard lock(queueMutex_);
            if (nextQueued_ >= 12) return 0;
            requestIndex_[request] = nextQueued_++;
            manual(request->controls(), requestIndex_[request] / 12);
        }
        return camera_->queueRequest(request);
    }
    void completed(Request *request)
    {
        try { completedChecked(request); }
        catch (const std::exception &error) {
            std::cerr << "ERROR: callback: " << error.what() << '\n';
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true; ready_.notify_all();
        }
    }
    void completedChecked(Request *request)
    {
        { std::lock_guard<std::mutex> lock(mutex_); if (frames_.size() >= 12 || failed_) return; }
        if (request->status() == Request::RequestCancelled)
            return;
        if (request->status() != Request::RequestComplete || request->buffers().size() != 1 || request->buffers().begin()->first != stream_) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true; ready_.notify_all(); return;
        }
        const FrameBuffer *buffer = request->buffers().begin()->second;
        const auto &meta = buffer->metadata();
        if (meta.status != FrameMetadata::FrameSuccess || buffer->planes().size() != 1 || meta.planes().size() != 1) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true;
            ready_.notify_all();
            return;
        }
        unsigned int queuedIndex;
        { std::lock_guard lock(queueMutex_); queuedIndex = requestIndex_.at(request); }
        auto exposure = request->metadata().get(controls::ExposureTime);
        auto gain = request->metadata().get(controls::AnalogueGain);
        auto exposureMode = request->metadata().get(controls::ExposureTimeMode);
        auto gainMode = request->metadata().get(controls::AnalogueGainMode);
        require(exposure && gain && exposureMode && gainMode, "capture controls metadata present");
        require(*exposureMode == controls::ExposureTimeModeManual && *gainMode == controls::AnalogueGainModeManual, "both captured modes manual");
        if (queuedIndex % 12 >= 6) {
            unsigned int phase = queuedIndex / 12;
            int target = phase == 0 || phase == 3 ? 2000 : 32000;
            float targetGain = phase == 2 ? 8.0f : 1.0f;
            require(std::abs(*exposure - target) <= 20 && std::abs(*gain - targetGain) < 0.03f, "settled captured exposure and gain match targets");
        }
        const auto &plane = buffer->planes()[0];
        DmaReadGuard sync(plane.fd.get());
        if (!sync.valid()) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true;
            ready_.notify_all();
            return;
        }
        void *mapping = mmap(nullptr, plane.offset + plane.length, PROT_READ,
                             MAP_SHARED, plane.fd.get(), 0);
        if (mapping == MAP_FAILED) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true;
            ready_.notify_all();
            return;
        }
        const auto *pixels = static_cast<const uint8_t *>(mapping) + plane.offset;
        const size_t bytes = meta.planes()[0].bytesused;
        if (!bytes || bytes > plane.length) {
            munmap(mapping, plane.offset + plane.length);
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true;
            ready_.notify_all();
            return;
        }
        std::vector<uint16_t> active;
        if (raw_) {
            if (width_ % 4 || stride_ < width_ / 4 * 5 || bytes != size_t(stride_) * height_) {
                munmap(mapping, plane.offset + plane.length);
                std::lock_guard<std::mutex> lock(mutex_);
                failed_ = true;
                ready_.notify_all();
                return;
            }
            active.reserve(width_ * height_);
            for (unsigned int row = 0; row < height_; ++row) {
                const uint8_t *line = pixels + row * stride_;
                for (unsigned int column = 0; column < width_ * 5 / 4; column += 5) {
                    const unsigned int lowBits = line[column + 4];
                    for (unsigned int index = 0; index < 4; ++index)
                        active.push_back((unsigned(line[column + index]) << 2) | ((lowBits >> (index * 2)) & 3));
                }
            }
        } else {
            require(stride_ >= width_ * 3 && bytes == size_t(stride_) * height_, "RGB geometry and bytesused");
            active.reserve(size_t(width_) * height_ * 3);
            for (unsigned int row = 0; row < height_; ++row) {
                const uint8_t *line = pixels + size_t(row) * stride_;
                active.insert(active.end(), line, line + width_ * 3);
            }
        }
        uint64_t sum = 0, sumSquares = 0;
        unsigned int low = raw_ ? 1023 : 255, high = 0;
        std::array<uint64_t, 1024> histogram{};
        std::array<uint64_t, 4> channelSum{}, channelCount{};
        std::array<uint64_t, 8> segmentSum{}, segmentCount{};
        size_t changed = 0, belowBlack = 0;
        for (size_t index = 0; index < active.size(); ++index) {
            const unsigned int value = active[index];
            sum += value;
            sumSquares += value * value;
            low = std::min(low, value);
            high = std::max(high, value);
            ++histogram[value];
            belowBlack += value < 64;
            if (previous_.size() == active.size())
                changed += previous_[index] != value;
            if (raw_) {
                const unsigned int column = index % width_, row = index / width_;
                const unsigned int channel = ((row / cfaCell_) % 2) * 2 + (column / cfaCell_) % 2;
                channelSum[channel] += value;
                ++channelCount[channel];
                const unsigned int segment = column * 8 / width_;
                segmentSum[segment] += value;
                ++segmentCount[segment];
            }
        }
        munmap(mapping, plane.offset + plane.length);
        if (!sync.finish()) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true;
            ready_.notify_all();
            return;
        }
        const double mean = double(sum) / active.size();
        FrameStats stats{meta.sequence, queuedIndex, *exposure, *exposureMode, *gainMode, *gain, {}, double(histogram[raw_ ? 1023 : 255]) / active.size(), meta.timestamp, request->metadata().get(controls::SensorTimestamp).value_or(-1), bytes, low, high, mean,
                         std::sqrt(std::max(0.0, double(sumSquares) / active.size() - mean * mean)),
                         high == 0, unsigned(std::count_if(histogram.begin(), histogram.end(), [](uint64_t n) { return n != 0; })),
                         double(belowBlack) / active.size(), previous_.size() == active.size() ? double(changed) / active.size() : -1.0,
                         {}, {}, {}};
        auto black = request->metadata().get(controls::SensorBlackLevels);
        auto colour = request->metadata().get(controls::ColourGains);
        auto gamma = request->metadata().get(controls::Gamma);
        std::ostringstream extra;
        extra << ",\"ipa_sensor_black_levels\":";
        if (black) {
            require(black->size() == 4, "four IPA black levels");
            extra << '[';
            for (unsigned int i = 0; i < 4; ++i) { if (i) extra << ','; extra << (*black)[i]; }
            extra << ']';
        } else extra << "null";
        extra << ",\"ipa_colour_gains\":";
        if (colour) {
            require(colour->size() == 2, "two IPA colour gains");
            extra << '[' << (*colour)[0] << ',' << (*colour)[1] << ']';
        } else extra << "null";
        extra << ",\"ipa_gamma\":";
        if (gamma) extra << *gamma; else extra << "null";
        stats.ipaMetadataJson = extra.str();
        for (unsigned int index = 0; index < 4; ++index)
            stats.bayerMean[index] = channelCount[index] ? double(channelSum[index]) / channelCount[index] : 0.0;
        for (unsigned int index = 0; index < 8; ++index)
            stats.horizontalMean[index] = segmentCount[index] ? double(segmentSum[index]) / segmentCount[index] : 0.0;
        for (unsigned int q = 0; q < 3; ++q) {
            uint64_t cumulative = 0, wanted = (active.size() * (q == 0 ? 10 : q == 1 ? 50 : 90) + 99) / 100;
            for (unsigned int value = 0; value < histogram.size(); ++value) {
                cumulative += histogram[value];
                if (cumulative >= wanted) { stats.quantiles[q] = value; break; }
            }
        }
        previous_ = std::move(active);
        bool again;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (frames_.size() >= 12)
                return;
            if (!frames_.empty() && (stats.sequence <= frames_.back().sequence || stats.timestamp <= frames_.back().timestamp)) {
                failed_ = true; ready_.notify_all(); return;
            }
            frames_.push_back(stats);
            again = frames_.size() < 12;
            ready_.notify_all();
        }
        if (again) {
            request->reuse(Request::ReuseBuffers);
            if (queue(request) != 0) {
                std::lock_guard<std::mutex> lock(mutex_);
                failed_ = true;
                ready_.notify_all();
            }
        }
    }

    bool wait()
    {
        std::unique_lock<std::mutex> lock(mutex_);
        return ready_.wait_for(lock, std::chrono::seconds(45), [this] {
            return frames_.size() == 12 || failed_;
        }) && !failed_;
    }

    std::string json() const
    {
        std::ostringstream out;
        out << "{\"raw\":" << (raw_ ? "true" : "false") << ",\"width\":" << width_ << ",\"height\":" << height_ << ",\"stride\":" << stride_ << ",\"frames\":[";
        bool first = true;
        for (const auto &frame : frames_) {
            if (!first)
                out << ',';
            first = false;
            out << "{\"sequence\":" << frame.sequence
                      << ",\"queued_index\":" << frame.queuedIndex
                      << ",\"phase\":" << frame.queuedIndex / 12
                      << ",\"settled\":" << (frame.queuedIndex % 12 >= 6 ? "true" : "false")
                      << ",\"exposure_us\":" << frame.exposure
                      << ",\"analogue_gain\":" << frame.gain
                      << ",\"exposure_mode\":" << frame.exposureMode
                      << ",\"gain_mode\":" << frame.gainMode
                      << frame.ipaMetadataJson
                      << ",\"quantiles_p10_p50_p90\":[" << frame.quantiles[0] << ',' << frame.quantiles[1] << ',' << frame.quantiles[2] << ']'
                      << ",\"saturated_fraction\":" << frame.saturatedFraction
                      << ",\"timestamp_ns\":" << frame.timestamp
                      << ",\"sensor_timestamp_ns\":" << frame.sensorTimestamp
                      << ",\"bytesused\":" << frame.bytesUsed
                      << ",\"byte_min\":" << frame.minimum
                      << ",\"byte_max\":" << frame.maximum
                      << ",\"mean\":" << frame.mean
                      << ",\"stddev\":" << frame.standardDeviation
                      << ",\"all_zero\":" << (frame.allZero ? "true" : "false")
                      << ",\"occupied_bins\":" << frame.occupiedBins
                      << ",\"below_black64_fraction\":" << frame.belowBlack64Fraction
                      << ",\"changed_fraction\":" << frame.changedFraction
                      << ",\"bayer_mean_rg_gb\":[";
            for (unsigned int index = 0; index < 4; ++index) {
                if (index) out << ',';
                out << frame.bayerMean[index];
            }
            out << "],\"horizontal_eighth_means\":[";
            for (unsigned int index = 0; index < 8; ++index) {
                if (index) out << ',';
                out << frame.horizontalMean[index];
            }
            out << "]}";
        }
        out << "]}";
        return out.str();
    }

private:
    std::shared_ptr<Camera> camera_;
    bool raw_;
    unsigned int width_, height_, stride_, cfaCell_;
    Stream *stream_;
    std::mutex queueMutex_;
    std::map<Request *, unsigned int> requestIndex_;
    unsigned int nextQueued_ = 0;
    std::vector<uint16_t> previous_;
    std::mutex mutex_;
    std::condition_variable ready_;
    std::vector<FrameStats> frames_;
    bool failed_ = false;
};

int main(int argc, char **argv)
{
    if (argc != 9 || (std::string(argv[5]) != "raw" && std::string(argv[5]) != "rgb"))
        return 2;
    const std::string expectedId = argv[2], expectedModel = argv[3], expectedEntity = argv[4];
    const bool rear = expectedId == "/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10" && expectedModel == "imx319" && expectedEntity == "imx319 7-0010";
    const bool front = expectedId == "/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10" && expectedModel == "imx471" && expectedEntity == "imx471 9-0010";
    if (!rear || front) return 2;
    const bool raw = std::string(argv[5]) == "raw";
    const int selected = 0;
    const unsigned int wantedWidth = std::stoul(argv[6]);
    const unsigned int wantedHeight = std::stoul(argv[7]);
    const unsigned int cfaCell = std::stoul(argv[8]);
    require(wantedWidth >= 4 && wantedWidth <= 4608 && wantedWidth % 4 == 0 && wantedHeight >= 4 && wantedHeight <= 3456 && wantedHeight % 4 == 0 && (cfaCell == 1 || cfaCell == 2), "supported probe dimensions/CFA");
    CameraManager manager;
    std::shared_ptr<Camera> camera;
    bool acquired = false, started = false;
    std::unique_ptr<PatternGuard> pattern;
    std::unique_ptr<Capture> capture;
    std::unique_ptr<FrameBufferAllocator> allocator;
    std::vector<std::unique_ptr<Request>> requests;
    int status = 1;
    std::vector<std::string> runSummaries;
    try {
        const auto node = std::filesystem::path(argv[1]).filename();
        require(std::string(argv[1]) == "/dev/" + node.string() && node.string().starts_with("v4l-subdev"), "sensor device path");
        std::ifstream entityFile(std::filesystem::path("/sys/class/video4linux") / node / "name");
        std::string entity; std::getline(entityFile, entity);
        require(entityFile.good() || entityFile.eof(), "read sensor entity");
        require(entity == expectedEntity, "exact sensor entity");
        const auto ofNode = std::filesystem::canonical(std::filesystem::path("/sys/class/video4linux") / node / "device/of_node");
        require(ofNode.string() == "/sys/firmware/devicetree" + expectedId, "exact sensor OF node");
        require(manager.start() == 0, "start camera manager");
        for (auto candidate : manager.cameras()) {
            if (candidate->id() == expectedId) {
                require(!camera, "unique exact physical camera");
                require(candidate->properties().get(properties::Model).value_or("") == expectedModel, "exact camera Model");
                camera = candidate;
            }
        }
        require(bool(camera), "find physical physical camera");
        require(camera->acquire() == 0, "acquire physical camera");
        acquired = true;
        auto configuration = camera->generateConfiguration({raw ? StreamRole::Raw : StreamRole::Viewfinder});
        require(bool(configuration) && configuration->size() == 1, "generate single physical stream");
        auto &streamConfiguration = configuration->at(0);
        streamConfiguration.size = { wantedWidth, wantedHeight };
        streamConfiguration.pixelFormat = raw ? formats::SRGGB10_CSI2P : formats::RGB888;
        streamConfiguration.bufferCount = 4;
        require(configuration->validate() != CameraConfiguration::Invalid, "validate configuration");
        require(streamConfiguration.size == Size(wantedWidth, wantedHeight), "requested native dimensions retained");
        require(camera->configure(configuration.get()) == 0, "configure physical camera");
        require(streamConfiguration.pixelFormat == (raw ? formats::SRGGB10_CSI2P : formats::RGB888), "require packed RGB888 output");
        Stream *stream = streamConfiguration.stream();
        allocator = std::make_unique<FrameBufferAllocator>(camera);
        require(allocator->allocate(stream) >= 0, "allocate output buffers");
        require(!allocator->buffers(stream).empty(), "output buffers present");
        pattern = std::make_unique<PatternGuard>(argv[1], selected);
        for (unsigned int run = 0; run < 2; ++run) {
            requests.clear();
        for (const auto &buffer : allocator->buffers(stream)) {
            auto request = camera->createRequest();
            require(bool(request) && request->addBuffer(stream, buffer.get()) == 0, "create request");
            requests.push_back(std::move(request));
        }
        capture = std::make_unique<Capture>(camera, raw, streamConfiguration, cfaCell);
        camera->requestCompleted.connect(capture.get(), &Capture::completed);
        auto gainInfo = camera->controls().find(controls::AnalogueGain.id());
        require(gainInfo != camera->controls().end() && gainInfo->second.min().get<float>() == 1.0f && gainInfo->second.max().get<float>() == 16.0f && gainInfo->second.def().get<float>() == 1.0f, "IMX319 public gain range 1..16 default1");
        ControlList initial(camera->controls()); Capture::manual(initial, 0);
        require(camera->start(&initial) == 0, "start physical capture with explicit controls");
        started = true;
        for (auto &request : requests)
            require(capture->queue(request.get()) == 0, "queue initial controlled request");
        const bool complete = capture->wait();
        require(camera->stop() == 0, "stop physical camera");
        started = false;
        camera->requestCompleted.disconnect(capture.get());
            runSummaries.push_back(capture->json());
            require(complete, "twelve complete startup frames");
            capture.reset();
        }
        require(pattern->restore(), "restore sensor pattern after both runs");
        pattern.reset();
        status = 0;
    } catch (const std::exception &error) {
        std::cerr << "ERROR: " << error.what() << '\n';
    }
    if (started && camera->stop() != 0) status = 1;
    if (camera && capture)
        camera->requestCompleted.disconnect(capture.get());
    if (pattern && !pattern->restore()) { std::cerr << "ERROR: pattern recovery\n"; status = 1; }
    pattern.reset();
    requests.clear();
    allocator.reset();
    if (acquired && camera->release() != 0) { std::cerr << "ERROR: release camera\n"; status = 1; }
    if (capture) runSummaries.push_back(capture->json());
    std::cout << "{\"runs\":[";
    for (size_t i = 0; i < runSummaries.size(); ++i) { if (i) std::cout << ','; std::cout << runSummaries[i]; }
    std::cout << "]}\n";
    capture.reset();
    camera.reset();
    manager.stop();
    return status;
}
