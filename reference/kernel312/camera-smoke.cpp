/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Real application requests, including restart without reconfiguration. */
#include <chrono>
#include <cstdio>
#include <thread>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <array>
#include <algorithm>
#include <condition_variable>
#include <csignal>
#include <iostream>
#include <memory>
#include <mutex>
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
#include <libcamera/request.h>
#include <libcamera/property_ids.h>

using namespace libcamera;
static volatile std::sig_atomic_t interrupted;
static bool automaticAe=false;
static void stopSignal(int) { interrupted = 1; }

static void setRequestControls(Request *request, unsigned int sequence, unsigned int epoch)
{
 request->controls().clear();
 (void)sequence; (void)epoch;
}

class Capture
{
public:
	std::shared_ptr<Camera> camera;
	std::mutex mutex;
	std::condition_variable condition;
	unsigned int frames = 0, failed = 0, nextRequest = 4, epoch = 0, lockedRun = 0, stableSensorRun=0;
    int32_t previousExposure=0; float previousGain=0; float maximumGain=1;
	bool finished() const { return frames >= 120 || (lockedRun >= 8 && (!automaticAe || stableSensorRun >= 8)); }
	bool running = false;
	bool holdEnabled=false, holdResumed=false;
	std::vector<Request *> heldRequests;
	void complete(Request *request)
	{
		std::lock_guard lock(mutex);
		if (!running || request->status() == Request::RequestCancelled)
			return;
		for (const auto &[stream, buffer] : request->buffers()) {
			(void)stream;
			const auto &m = buffer->metadata();
   auto exposure = request->metadata().get(controls::ExposureTime);
   auto analogue = request->metadata().get(controls::AnalogueGain);
   auto exposureMode = request->metadata().get(controls::ExposureTimeMode);
   auto gainMode = request->metadata().get(controls::AnalogueGainMode);
   if (!exposure || !analogue || !exposureMode || !gainMode || *exposureMode != (automaticAe ? controls::ExposureTimeModeAuto : controls::ExposureTimeModeManual) || *gainMode != (automaticAe ? controls::AnalogueGainModeAuto : controls::AnalogueGainModeManual) || *exposure <= 0 || !std::isfinite(*analogue) || *analogue < 1 || *analogue > maximumGain + .0001f) ++failed;
   else std::cout << "APPLICATION_SENSOR_METADATA epoch=" << epoch << " request=" << request->sequence()
    << " exposure_us=" << *exposure << " analogue_gain=" << *analogue
    << " exposure_mode=" << *exposureMode << " gain_mode=" << *gainMode << std::endl;

            if (exposure && analogue) {
                stableSensorRun = *exposure==previousExposure && *analogue==previousGain ? stableSensorRun+1 : 0;
                previousExposure=*exposure;previousGain=*analogue;
            }
			auto gains = request->metadata().get(controls::ColourGains);
			if (!gains || !std::isfinite((*gains)[0]) || !std::isfinite((*gains)[1]) ||
			    (*gains)[0] < .125f || (*gains)[0] > 8 || (*gains)[1] < .125f || (*gains)[1] > 8 ||
			    !request->metadata().get(controls::AwbEnable).value_or(false)) ++failed;
			const bool locked = request->metadata().get(controls::AwbLocked).value_or(false);
			lockedRun = locked ? lockedRun + 1 : 0;
			if (gains) std::cout << "APPLICATION_WB epoch=" << epoch << " request=" << request->sequence()
			    << " red=" << (*gains)[0] << " blue=" << (*gains)[1] << " locked=" << locked << std::endl;
			if (m.status != FrameMetadata::FrameSuccess || !m.timestamp)
				++failed;
			uint64_t hash = UINT64_C(14695981039346656037), total = 0;
			std::array<uint64_t, 4> lumaBands{};
			std::array<std::array<double,3>,4> colourBands{};
            std::array<uint8_t,115200> colourFrame{};
			unsigned int lowest = 255, highest = 0;
			for (unsigned int i = 0; i < buffer->planes().size(); ++i) {
				const auto &plane = buffer->planes()[i];
				unsigned int used = m.planes()[i].bytesused;
				if (!used || used > plane.length) { ++failed; continue; }
				unsigned long pageSize = sysconf(_SC_PAGESIZE);
				unsigned int offset = plane.offset % pageSize;
				dma_buf_sync sync{ DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ };
				if (ioctl(plane.fd.get(), DMA_BUF_IOCTL_SYNC, &sync)) { ++failed; continue; }
				void *mapping = mmap(nullptr, used + offset, PROT_READ, MAP_SHARED,
						     plane.fd.get(), plane.offset - offset);
				if (mapping == MAP_FAILED) {
					++failed;
				} else {
					const uint8_t *data = static_cast<uint8_t *>(mapping) + offset;
					for (unsigned int n = 0; n < used; ++n) {
						hash = (hash ^ data[n]) * UINT64_C(1099511628211);
						if (!i && n < 320 * 240) lumaBands[n / (320 * 60)] += data[n];
						if (!i) { lowest = std::min(lowest, unsigned(data[n])); highest = std::max(highest, unsigned(data[n])); }
					}
                    if (total + used <= colourFrame.size()) std::memcpy(colourFrame.data()+total,data,used);
                    else ++failed;
					munmap(mapping, used + offset);
					total += used;
				}
				sync.flags = DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ;
				if (ioctl(plane.fd.get(), DMA_BUF_IOCTL_SYNC, &sync))
					++failed;
			}
   if (total != 115200) ++failed;
   else for (unsigned int y=0;y<240;++y) for (unsigned int x=0;x<320;++x) {
       const double c=double(colourFrame[y*320+x]);
       const unsigned int chroma=320*240+(y/2)*320+(x&~1U);
       const double u=double(colourFrame[chroma])-128,v=double(colourFrame[chroma+1])-128;
       colourBands[y/60][0]+=c+1.402*v;
       colourBands[y/60][1]+=c-.344136*u-.714136*v;
       colourBands[y/60][2]+=c+1.772*u;
   }
   std::cout << "APPLICATION_RGB epoch=" << epoch << " request=" << request->sequence();
   for (const auto &band : colourBands) for (double value : band) std::cout << " " << value/(320*60);
   std::cout << std::endl;
   std::cout << "APPLICATION_LUMA epoch=" << epoch << " request=" << request->sequence();
   for (auto sum : lumaBands) std::cout << " " << double(sum) / (320 * 60);
   std::cout << std::endl;
			std::cout << "APPLICATION_FRAME number=" << frames << " request=" << request->sequence() << " sequence=" << m.sequence
				<< " timestamp=" << m.timestamp << " status=" << m.status
				<< " bytes=" << total << " hash=" << hash << " first_plane_min=" << lowest
				<< " first_plane_max=" << highest << std::endl;
		}
		++frames;
		if (holdEnabled && !holdResumed && frames>=8) {
			heldRequests.push_back(request);
			condition.notify_one();
			return;
		}
		if (!finished()) {
			request->reuse(Request::ReuseBuffers);
			setRequestControls(request, nextRequest++, epoch);
			if (camera->queueRequest(request))
				++failed;
		}
		condition.notify_one();
	}
};

int main(int argc, char **argv)
{
	if (argc != 2)
		return 2;
	std::signal(SIGINT, stopSignal);
	std::signal(SIGTERM, stopSignal);
	const char *ae=std::getenv("CAMSS_AE_ENABLE");
    automaticAe=ae && !std::strcmp(ae,"1");
    std::cout << "APPLICATION_PROCESS pid=" << getpid() << std::endl;
	CameraManager manager;
	if (manager.start())
		return 3;
	Capture capture;
	for (auto &camera : manager.cameras()) {
		const auto model = camera->properties().get(properties::Model).value_or("");
		std::cout << "APPLICATION_CAMERA id=" << camera->id() << " model=" << model << std::endl;
		if (camera->id().find(argv[1]) != std::string::npos || model == argv[1])
			capture.camera = camera;
	}
	if (!capture.camera) {
		std::cout << "APPLICATION_FAILURE stage=select" << std::endl;
		return 4;
	}
	int acquired = capture.camera->acquire();
	if (acquired) {
		std::cout << "APPLICATION_FAILURE stage=acquire error=" << acquired << std::endl;
		return 4;
	}
	auto &camera = capture.camera;
	struct Release {
		std::shared_ptr<Camera> camera;
		~Release() { camera->release(); }
	} release{ camera };
	auto config = camera->generateConfiguration({ StreamRole::Viewfinder });
	if (!config) {
		std::cout << "APPLICATION_FAILURE stage=generate" << std::endl;
		return 5;
	}
	const char *size=std::getenv("CAMSS_SENSOR_SIZE");
    if (size) {
        unsigned int width=0,height=0;
        if (std::sscanf(size,"%ux%u",&width,&height)!=2) return 6;
        SensorConfiguration sensor;sensor.bitDepth=10;sensor.outputSize=Size(width,height);
        config->sensorConfig=sensor;
    }
    config->at(0).size = Size(320, 240);
	config->at(0).pixelFormat = formats::NV12;
	if (config->validate() == CameraConfiguration::Invalid) {
		std::cout << "APPLICATION_FAILURE stage=validate" << std::endl;
		return 6;
	}
	int configured = camera->configure(config.get());
	if (configured) {
		std::cout << "APPLICATION_FAILURE stage=configure error=" << configured << std::endl;
		return 6;
	}
	if (config->at(0).stride != 320) return 6;
    capture.holdEnabled=std::getenv("CAMSS_TEST_HOLD_BUFFERS")!=nullptr;
    capture.maximumGain=camera->controls().at(&controls::AnalogueGain).max().get<float>();
	FrameBufferAllocator allocator(camera);
	Stream *stream = config->at(0).stream();
	if (allocator.allocate(stream) < 0)
		return 7;
	std::vector<std::unique_ptr<Request>> requests;
	for (const auto &buffer : allocator.buffers(stream)) {
		auto request = camera->createRequest();
		if (!request || request->addBuffer(stream, buffer.get()))
			return 8;
		requests.push_back(std::move(request));
	}
	camera->requestCompleted.connect(&capture, &Capture::complete);
	int result = 0;
	const char *count = std::getenv("CAMSS_AWB_EPOCHS");
    const unsigned int epochCount = count && !std::strcmp(count,"1") ? 1 : 2;
    for (unsigned int epoch = 0; epoch < epochCount && !result && !interrupted; ++epoch) {
		std::cout << "APPLICATION_BEGIN epoch=" << epoch << std::endl;

		{
			std::lock_guard lock(capture.mutex);
			capture.frames = capture.failed = capture.lockedRun = capture.stableSensorRun = 0;
			capture.nextRequest = 4; capture.epoch = epoch;
			capture.running = true;
		}
		if (camera->start()) { result = 9; break; }
		for (const auto &request : requests) {
			if (epoch)
				request->reuse(Request::ReuseBuffers);
			request->controls().clear();
			if (camera->queueRequest(request.get())) { result = 10; break; }
		}
		{
			std::unique_lock lock(capture.mutex);
			auto end = std::chrono::steady_clock::now() + std::chrono::seconds(20);
			while (!result && !interrupted && !capture.finished() && !capture.failed &&
			       std::chrono::steady_clock::now() < end) {
				if (capture.holdEnabled && !capture.holdResumed && capture.heldRequests.size()==requests.size()) {
					lock.unlock();std::this_thread::sleep_for(std::chrono::milliseconds(120));lock.lock();
					capture.holdResumed=true;
					for (Request *request:capture.heldRequests) {
						request->reuse(Request::ReuseBuffers);
						setRequestControls(request,capture.nextRequest++,epoch);
						if (camera->queueRequest(request)) result=10;
					}
					capture.heldRequests.clear();
					std::cout << "APPLICATION_BUFFER_RESUMED after_hold_ms=120" << std::endl;
				}
				capture.condition.wait_for(lock, std::chrono::milliseconds(100));
			}
			if (!capture.finished() || capture.failed || interrupted)
				result = 11;
			capture.running = false;
		}
		int ret = camera->stop();
		if (ret)
			result = 12;
		std::cout << "APPLICATION_EPOCH epoch=" << epoch << " frames=" << capture.frames
			<< " failed=" << capture.failed << " stop=" << ret << std::endl;
	}
	requests.clear();
	allocator.free(stream);
	std::cout << "APPLICATION_RESULT result=" << result << std::endl;
	return result;
}
