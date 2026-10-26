// Finite, ambient-independent test of the real sensor -> CAMSS -> CPU ISP path.
// The sensor test-pattern control is restored by RAII, including error exits.
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
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

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

    ~PatternGuard()
    {
        if (fd_ < 0)
            return;
        v4l2_control control{};
        control.id = V4L2_CID_TEST_PATTERN;
        control.value = original_;
        if (ioctl(fd_, VIDIOC_S_CTRL, &control) != 0)
            std::cerr << "ERROR: sensor pattern restore failed\n";
        close(fd_);
    }

private:
    int fd_ = -1;
    int original_ = 0;
};

struct FrameStats {
    unsigned int sequence;
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
    std::array<double, 3> byteChannelMean{};
    std::array<double, 3> byteChannelStddev{};
    std::array<unsigned int, 3> byteChannelMin{};
    std::array<unsigned int, 3> byteChannelMax{};
    double differingChannelsFraction = -1.0;
    double clippedPixelsFraction = -1.0;
    int exposureUs = -1;
    float analogueGain = -1.0f;
};

class Capture {
public:
    Capture(std::shared_ptr<Camera> camera, bool raw, const StreamConfiguration &cfg, unsigned int cfaCell)
        : camera_(camera), raw_(raw), width_(cfg.size.width), height_(cfg.size.height), stride_(cfg.stride), cfaCell_(cfaCell) {}

    void completed(Request *request)
    {
        if (request->status() == Request::RequestCancelled)
            return;
        const FrameBuffer *buffer = request->buffers().begin()->second;
        const auto &meta = buffer->metadata();
        if (meta.status != FrameMetadata::FrameSuccess || buffer->planes().empty() || meta.planes().empty()) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true;
            ready_.notify_all();
            return;
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
            if (stride_ < width_ * 3 || bytes != size_t(stride_) * height_) {
                munmap(mapping, plane.offset + plane.length);
                std::lock_guard<std::mutex> lock(mutex_);
                failed_ = true;
                ready_.notify_all();
                return;
            }
            active.reserve(size_t(width_) * height_ * 3);
            for (unsigned int row = 0; row < height_; ++row)
                active.insert(active.end(), pixels + row * stride_, pixels + row * stride_ + width_ * 3);
        }
        uint64_t sum = 0, sumSquares = 0;
        unsigned int low = raw_ ? 1023 : 255, high = 0;
        std::array<uint64_t, 1024> histogram{};
        std::array<uint64_t, 4> channelSum{}, channelCount{};
        std::array<uint64_t, 8> segmentSum{}, segmentCount{};
        size_t changed = 0, belowBlack = 0;
        std::array<uint64_t, 3> rgbSum{}, rgbSquares{}, rgbCount{};
        std::array<unsigned int, 3> rgbMin{255, 255, 255}, rgbMax{};
        size_t differing = 0, clipped = 0;
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
            if (!raw_) {
                const unsigned int channel = index % 3;
                rgbSum[channel] += value;
                rgbSquares[channel] += value * value;
                ++rgbCount[channel];
                rgbMin[channel] = std::min(rgbMin[channel], value);
                rgbMax[channel] = std::max(rgbMax[channel], value);
                if (channel == 0) {
                    const auto lo = std::min({active[index], active[index + 1], active[index + 2]});
                    const auto hi = std::max({active[index], active[index + 1], active[index + 2]});
                    differing += hi >= 24 && hi - lo >= 12;
                    clipped += hi >= 250;
                }
            }
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
        FrameStats stats{meta.sequence, low, high, mean,
                         std::sqrt(std::max(0.0, double(sumSquares) / active.size() - mean * mean)),
                         high == 0, unsigned(std::count_if(histogram.begin(), histogram.end(), [](uint64_t n) { return n != 0; })),
                         double(belowBlack) / active.size(), previous_.size() == active.size() ? double(changed) / active.size() : -1.0,
                         {}, {}};
        for (unsigned int index = 0; index < 4; ++index)
            stats.bayerMean[index] = channelCount[index] ? double(channelSum[index]) / channelCount[index] : 0.0;
        for (unsigned int index = 0; index < 8; ++index)
            stats.horizontalMean[index] = segmentCount[index] ? double(segmentSum[index]) / segmentCount[index] : 0.0;
        if (!raw_) {
            for (unsigned int channel = 0; channel < 3; ++channel) {
                const double m = double(rgbSum[channel]) / rgbCount[channel];
                stats.byteChannelMean[channel] = m;
                stats.byteChannelStddev[channel] = std::sqrt(std::max(0.0, double(rgbSquares[channel]) / rgbCount[channel] - m * m));
                stats.byteChannelMin[channel] = rgbMin[channel];
                stats.byteChannelMax[channel] = rgbMax[channel];
            }
            stats.differingChannelsFraction = double(differing) / (size_t(width_) * height_);
            stats.clippedPixelsFraction = double(clipped) / (size_t(width_) * height_);
        }
        stats.exposureUs = request->metadata().get(controls::ExposureTime).value_or(-1);
        stats.analogueGain = request->metadata().get(controls::AnalogueGain).value_or(-1.0f);
        previous_ = std::move(active);
        bool again;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (frames_.size() >= 32)
                return;
            frames_.push_back(stats);
            again = frames_.size() < 32;
            ready_.notify_all();
        }
        if (again) {
            request->reuse(Request::ReuseBuffers);
            if (camera_->queueRequest(request) != 0) {
                std::lock_guard<std::mutex> lock(mutex_);
                failed_ = true;
                ready_.notify_all();
            }
        }
    }

    bool wait()
    {
        std::unique_lock<std::mutex> lock(mutex_);
        return ready_.wait_for(lock, std::chrono::seconds(35), [this] {
            return frames_.size() == 32 || failed_;
        }) && !failed_;
    }

    void print() const
    {
        std::cout << "{\"raw\":" << (raw_ ? "true" : "false") << ",\"width\":" << width_ << ",\"height\":" << height_ << ",\"stride\":" << stride_ << ",\"frames\":[";
        bool first = true;
        for (const auto &frame : frames_) {
            if (!first)
                std::cout << ',';
            first = false;
            std::cout << "{\"sequence\":" << frame.sequence
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
                if (index) std::cout << ',';
                std::cout << frame.bayerMean[index];
            }
            std::cout << "],\"horizontal_eighth_means\":[";
            for (unsigned int index = 0; index < 8; ++index) {
                if (index) std::cout << ',';
                std::cout << frame.horizontalMean[index];
            }
            std::cout << "],\"byte_channel_means_012\":[";
            for (unsigned int channel = 0; channel < 3; ++channel) {
                if (channel) std::cout << ',';
                std::cout << frame.byteChannelMean[channel];
            }
            std::cout << "],\"byte_channel_stddevs_012\":[";
            for (unsigned int channel = 0; channel < 3; ++channel) {
                if (channel) std::cout << ',';
                std::cout << frame.byteChannelStddev[channel];
            }
            std::cout << "],\"byte_channel_mins_012\":[";
            for (unsigned int channel = 0; channel < 3; ++channel) {
                if (channel) std::cout << ',';
                std::cout << frame.byteChannelMin[channel];
            }
            std::cout << "],\"byte_channel_maxs_012\":[";
            for (unsigned int channel = 0; channel < 3; ++channel) {
                if (channel) std::cout << ',';
                std::cout << frame.byteChannelMax[channel];
            }
            std::cout << "],\"differing_channels_fraction\":" << frame.differingChannelsFraction
                      << ",\"clipped_pixels_fraction\":" << frame.clippedPixelsFraction
                      << ",\"exposure_us\":" << frame.exposureUs
                      << ",\"analogue_gain\":" << frame.analogueGain << "}";
        }
        std::cout << "]}\n";
    }

private:
    std::shared_ptr<Camera> camera_;
    bool raw_;
    unsigned int width_, height_, stride_, cfaCell_;
    std::vector<uint16_t> previous_;
    std::mutex mutex_;
    std::condition_variable ready_;
    std::vector<FrameStats> frames_;
    bool failed_ = false;
};

int main(int argc, char **argv)
{
    if (argc != 7 || (std::string(argv[2]) != "raw" && std::string(argv[2]) != "rgb") || (std::string(argv[3]) != "0" && std::string(argv[3]) != "2"))
        return 2;
    const bool raw = std::string(argv[2]) == "raw";
    const int selected = std::stoi(argv[3]);
    const unsigned int wantedWidth = std::stoul(argv[4]);
    const unsigned int wantedHeight = std::stoul(argv[5]);
    const unsigned int cfaCell = std::stoul(argv[6]);
    require(wantedWidth >= 4 && wantedWidth <= 4608 && wantedWidth % 4 == 0 && wantedHeight >= 4 && wantedHeight <= 3456 && wantedHeight % 4 == 0 && (cfaCell == 1 || cfaCell == 2), "supported probe dimensions/CFA");
    CameraManager manager;
    std::shared_ptr<Camera> camera;
    bool acquired = false, started = false;
    std::unique_ptr<PatternGuard> pattern;
    std::unique_ptr<Capture> capture;
    std::unique_ptr<FrameBufferAllocator> allocator;
    std::vector<std::unique_ptr<Request>> requests;
    int status = 1;
    try {
        require(manager.start() == 0, "start camera manager");
        for (auto candidate : manager.cameras()) {
            if (candidate->id().find("cci@ac4b000") != std::string::npos) {
                require(!camera, "unique physical front camera");
                camera = candidate;
            }
        }
        require(bool(camera), "find physical front camera");
        require(camera->acquire() == 0, "acquire front camera");
        acquired = true;
        auto configuration = camera->generateConfiguration({raw ? StreamRole::Raw : StreamRole::Viewfinder});
        require(bool(configuration), "generate front camera configuration");
        auto &streamConfiguration = configuration->at(0);
        streamConfiguration.size = { wantedWidth, wantedHeight };
        streamConfiguration.pixelFormat = raw ? formats::SRGGB10_CSI2P : formats::RGB888;
        streamConfiguration.bufferCount = 4;
        require(configuration->validate() != CameraConfiguration::Invalid, "validate configuration");
        require(streamConfiguration.size == Size(wantedWidth, wantedHeight), "requested native dimensions retained");
        require(camera->configure(configuration.get()) == 0, "configure front camera");
        require(streamConfiguration.pixelFormat == (raw ? formats::SRGGB10_CSI2P : formats::RGB888), "require packed RGB888 output");
        Stream *stream = streamConfiguration.stream();
        allocator = std::make_unique<FrameBufferAllocator>(camera);
        require(allocator->allocate(stream) >= 0, "allocate output buffers");
        require(!allocator->buffers(stream).empty(), "output buffers present");
        for (const auto &buffer : allocator->buffers(stream)) {
            auto request = camera->createRequest();
            require(bool(request) && request->addBuffer(stream, buffer.get()) == 0, "create request");
            requests.push_back(std::move(request));
        }
        pattern = std::make_unique<PatternGuard>(argv[1], selected);
        capture = std::make_unique<Capture>(camera, raw, streamConfiguration, cfaCell);
        camera->requestCompleted.connect(capture.get(), &Capture::completed);
        require(camera->start() == 0, "start color bar capture");
        started = true;
        for (auto &request : requests)
            require(camera->queueRequest(request.get()) == 0, "queue initial request");
        require(capture->wait(), "wait for 32 frames");
        camera->stop();
        started = false;
        camera->requestCompleted.disconnect(capture.get());
        pattern.reset();
        capture->print();
        status = 0;
    } catch (const std::exception &error) {
        std::cerr << "ERROR: " << error.what() << '\n';
    }
    if (started)
        camera->stop();
    if (camera && capture)
        camera->requestCompleted.disconnect(capture.get());
    pattern.reset();
    requests.clear();
    allocator.reset();
    if (acquired)
        camera->release();
    capture.reset();
    camera.reset();
    manager.stop();
    return status;
}
