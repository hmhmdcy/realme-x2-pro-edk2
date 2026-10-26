/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Real application requests, including restart without reconfiguration. */
#include <chrono>
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
static void stopSignal(int) { interrupted = 1; }

class Capture
{
public:
	std::shared_ptr<Camera> camera;
	std::mutex mutex;
	std::condition_variable condition;
	unsigned int frames = 0, failed = 0;
	bool running = false;
	void complete(Request *request)
	{
		std::lock_guard lock(mutex);
		if (!running || request->status() == Request::RequestCancelled)
			return;
		for (const auto &[stream, buffer] : request->buffers()) {
			(void)stream;
			const auto &m = buffer->metadata();
			if (m.status != FrameMetadata::FrameSuccess || !m.timestamp)
				++failed;
			uint64_t hash = UINT64_C(14695981039346656037), total = 0;
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
						if (!i) { lowest = std::min(lowest, unsigned(data[n])); highest = std::max(highest, unsigned(data[n])); }
					}
					munmap(mapping, used + offset);
					total += used;
				}
				sync.flags = DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ;
				if (ioctl(plane.fd.get(), DMA_BUF_IOCTL_SYNC, &sync))
					++failed;
			}
			std::cout << "APPLICATION_FRAME number=" << frames << " request=" << request->sequence() << " sequence=" << m.sequence
				<< " timestamp=" << m.timestamp << " status=" << m.status
				<< " bytes=" << total << " hash=" << hash << " first_plane_min=" << lowest
				<< " first_plane_max=" << highest << std::endl;
		}
		++frames;
		if (frames < 24) {
			request->reuse(Request::ReuseBuffers);
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
	for (unsigned int epoch = 0; epoch < 3 && !result && !interrupted; ++epoch) {
		std::cout << "APPLICATION_BEGIN epoch=" << epoch << std::endl;
		ControlList controls(camera->controls());
		const std::array<float, 2> gains{ 2.22f, 1.90f };
		controls.set(controls::ColourGains, Span<const float, 2>(gains));
		{
			std::lock_guard lock(capture.mutex);
			capture.frames = capture.failed = 0;
			capture.running = true;
		}
		if (camera->start(&controls)) { result = 9; break; }
		for (const auto &request : requests) {
			if (epoch)
				request->reuse(Request::ReuseBuffers);
			if (camera->queueRequest(request.get())) { result = 10; break; }
		}
		{
			std::unique_lock lock(capture.mutex);
			auto end = std::chrono::steady_clock::now() + std::chrono::seconds(15);
			while (!result && !interrupted && capture.frames < 24 && !capture.failed &&
			       std::chrono::steady_clock::now() < end)
				capture.condition.wait_for(lock, std::chrono::milliseconds(100));
			if (capture.frames < 24 || capture.failed || interrupted)
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
