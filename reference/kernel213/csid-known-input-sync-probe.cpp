// Finite, ambient-independent test of the real sensor -> CAMSS -> CPU ISP path.
// The sensor test-pattern control is restored by RAII, including error exits.
#include <libcamera/libcamera.h>
#include <libcamera/formats.h>
#include <linux/videodev2.h>
#include <linux/dma-buf.h>
#include <linux/media.h>
#include <cstring>
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

// Detach only the configured CSIPHY2 -> CSID0 data link for the known-input
// generator. Restore the exact saved flags after the generator is disabled.
class LinkGuard {
public:
    LinkGuard()
    {
        fd_ = open("/dev/media0", O_RDWR | O_CLOEXEC);
        require(fd_ >= 0, "open camera media graph");
        try {
            media_entity_desc entity{};
            unsigned int source = 0, sink = 0;
            for (entity.id = MEDIA_ENT_ID_FLAG_NEXT; ioctl(fd_, MEDIA_IOC_ENUM_ENTITIES, &entity) == 0; entity.id |= MEDIA_ENT_ID_FLAG_NEXT) {
                if (std::strcmp(entity.name, "msm_csiphy2") == 0) source = entity.id;
                if (std::strcmp(entity.name, "msm_csid0") == 0) sink = entity.id;
            }
            require(source && sink, "find exact CSIPHY2 and CSID0 entities");
            entity = {};
            entity.id = source;
            require(ioctl(fd_, MEDIA_IOC_ENUM_ENTITIES, &entity) == 0, "get CSIPHY2 entity");
            std::vector<media_pad_desc> pads(entity.pads);
            std::vector<media_link_desc> links(entity.links);
            media_links_enum enumeration{};
            enumeration.entity = source;
            enumeration.pads = pads.data();
            enumeration.links = links.data();
            require(ioctl(fd_, MEDIA_IOC_ENUM_LINKS, &enumeration) == 0, "read CSIPHY2 links");
            bool found = false;
            for (const auto &link : links) {
                if (link.source.entity == source && link.source.index == 1 && link.sink.entity == sink && link.sink.index == 0) {
                    require(!found, "unique configured data link");
                    saved_ = link;
                    found = true;
                }
            }
            require(found && (saved_.flags & MEDIA_LNK_FL_ENABLED) && !(saved_.flags & MEDIA_LNK_FL_IMMUTABLE), "configured link must be mutable and enabled");
            media_link_desc disabled = saved_;
            disabled.flags &= ~MEDIA_LNK_FL_ENABLED;
            require(ioctl(fd_, MEDIA_IOC_SETUP_LINK, &disabled) == 0, "detach physical input for CSID generator");
            detached_ = true;
        } catch (...) {
            close(fd_);
            fd_ = -1;
            throw;
        }
    }
    ~LinkGuard()
    {
        if (fd_ >= 0) {
            if (detached_ && ioctl(fd_, MEDIA_IOC_SETUP_LINK, &saved_) != 0)
                std::cerr << "ERROR: original CSIPHY2 link restore failed\n";
            close(fd_);
        }
    }
private:
    int fd_ = -1;
    bool detached_ = false;
    media_link_desc saved_{};
};

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
};

class Capture {
public:
    Capture(std::shared_ptr<Camera> camera, bool raw, const StreamConfiguration &cfg)
        : camera_(camera), raw_(raw), width_(cfg.size.width), height_(cfg.size.height), stride_(cfg.stride) {}

    void completed(Request *request)
    {
        if (request->status() == Request::RequestCancelled)
            return;
        const FrameBuffer *buffer = request->buffers().begin()->second;
        const auto &meta = buffer->metadata();
        if (buffer->planes().empty() || meta.planes().empty()) {
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
            if (width_ != 1928 || height_ != 1088 || stride_ != 2416 || bytes != stride_ * height_) {
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
            active.assign(pixels, pixels + bytes);
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
                const unsigned int channel = (row % 2) * 2 + column % 2;
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
        previous_ = std::move(active);
        bool again;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (frames_.size() >= 6)
                return;
            frames_.push_back(stats);
            again = frames_.size() < 6;
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
        return ready_.wait_for(lock, std::chrono::seconds(10), [this] {
            return frames_.size() == 6 || failed_;
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
            std::cout << "]}";
        }
        std::cout << "]}\n";
    }

private:
    std::shared_ptr<Camera> camera_;
    bool raw_;
    unsigned int width_, height_, stride_;
    std::vector<uint16_t> previous_;
    std::mutex mutex_;
    std::condition_variable ready_;
    std::vector<FrameStats> frames_;
    bool failed_ = false;
};

int main(int argc, char **argv)
{
    if (argc != 4 || (std::string(argv[2]) != "raw" && std::string(argv[2]) != "rgb") || std::string(argv[3]) != "4")
        return 2;
    const bool raw = std::string(argv[2]) == "raw";
    const int selected = std::stoi(argv[3]);
    CameraManager manager;
    std::shared_ptr<Camera> camera;
    bool acquired = false, started = false;
    std::unique_ptr<LinkGuard> link;
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
        streamConfiguration.size = {raw ? 1928U : 1920U, 1088};
        streamConfiguration.pixelFormat = raw ? formats::SRGGB10_CSI2P : formats::RGB888;
        streamConfiguration.bufferCount = 4;
        require(configuration->validate() != CameraConfiguration::Invalid, "validate configuration");
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
        link = std::make_unique<LinkGuard>();
        pattern = std::make_unique<PatternGuard>(argv[1], selected);
        capture = std::make_unique<Capture>(camera, raw, streamConfiguration);
        camera->requestCompleted.connect(capture.get(), &Capture::completed);
        require(camera->start() == 0, "start color bar capture");
        started = true;
        for (auto &request : requests)
            require(camera->queueRequest(request.get()) == 0, "queue initial request");
        require(capture->wait(), "wait for six frames");
        camera->stop();
        started = false;
        camera->requestCompleted.disconnect(capture.get());
        pattern.reset();
        link.reset();
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
    link.reset();
    requests.clear();
    allocator.reset();
    if (acquired)
        camera->release();
    capture.reset();
    camera.reset();
    manager.stop();
    return status;
}
