// Finite, ambient-independent test of the real sensor -> CAMSS -> CPU ISP path.
// The sensor test-pattern control is restored by RAII, including error exits.
#include <libcamera/libcamera.h>
#include <libcamera/formats.h>
#include <linux/videodev2.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <algorithm>
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

class PatternGuard {
public:
    explicit PatternGuard(const char *path)
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
            control.value = 2;
            require(ioctl(fd_, VIDIOC_S_CTRL, &control) == 0, "enable sensor color bars");
            control.value = -1;
            require(ioctl(fd_, VIDIOC_G_CTRL, &control) == 0 && control.value == 2,
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
};

class Capture {
public:
    explicit Capture(std::shared_ptr<Camera> camera) : camera_(camera) {}

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
        uint64_t sum = 0, sumSquares = 0;
        unsigned int low = 255, high = 0;
        for (size_t index = 0; index < bytes; ++index) {
            unsigned int value = pixels[index];
            sum += value;
            sumSquares += value * value;
            low = std::min(low, value);
            high = std::max(high, value);
        }
        munmap(mapping, plane.offset + plane.length);
        const double mean = bytes ? double(sum) / bytes : 0;
        FrameStats stats{meta.sequence, low, high, mean,
                         std::sqrt(std::max(0.0, bytes ? double(sumSquares) / bytes - mean * mean : 0.0)),
                         high == 0};
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
        std::cout << "{\"sensor_internal_pattern\":2,\"ambient_independent\":true,\"frames\":[";
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
                      << ",\"all_zero\":" << (frame.allZero ? "true" : "false") << '}';
        }
        std::cout << "]}\n";
    }

private:
    std::shared_ptr<Camera> camera_;
    std::mutex mutex_;
    std::condition_variable ready_;
    std::vector<FrameStats> frames_;
    bool failed_ = false;
};

int main(int argc, char **argv)
{
    if (argc != 2)
        return 2;
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
        auto configuration = camera->generateConfiguration({StreamRole::Viewfinder});
        require(bool(configuration), "generate front camera configuration");
        auto &streamConfiguration = configuration->at(0);
        streamConfiguration.size = {1920, 1088};
        streamConfiguration.pixelFormat = formats::RGB888;
        streamConfiguration.bufferCount = 4;
        require(configuration->validate() != CameraConfiguration::Invalid, "validate configuration");
        require(camera->configure(configuration.get()) == 0, "configure front camera");
        require(streamConfiguration.pixelFormat == formats::RGB888, "require packed RGB888 output");
        Stream *stream = streamConfiguration.stream();
        allocator = std::make_unique<FrameBufferAllocator>(camera);
        require(allocator->allocate(stream) >= 0, "allocate output buffers");
        require(!allocator->buffers(stream).empty(), "output buffers present");
        for (const auto &buffer : allocator->buffers(stream)) {
            auto request = camera->createRequest();
            require(bool(request) && request->addBuffer(stream, buffer.get()) == 0, "create request");
            requests.push_back(std::move(request));
        }
        pattern = std::make_unique<PatternGuard>(argv[1]);
        capture = std::make_unique<Capture>(camera);
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
    manager.stop();
    return status;
}
