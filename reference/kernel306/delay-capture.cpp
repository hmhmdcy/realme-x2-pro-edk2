/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Test-only SOF-timed exposure/gain measurement; normal libcamera requests. */
#include <chrono>
#include <cerrno>
#include <fcntl.h>
#include <poll.h>
#include <sys/prctl.h>
#include <sys/wait.h>
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
static void stopSignal(int) { interrupted = 1; }

/* Child uses only async-signal-safe operations between fork and exec. */
class Stepper
{
public:
	pid_t pid = -1;
	int status = -1;
	bool start(const char *path)
	{
		int fds[2];
		if (pipe2(fds, O_CLOEXEC)) return false;
		const pid_t parent = getpid();
		std::string descriptor = std::to_string(fds[1]);
		pid = fork();
		if (!pid) {
			close(fds[0]);
			if (prctl(PR_SET_PDEATHSIG, SIGTERM) || getppid() != parent ||
			    fcntl(fds[1], F_SETFD, 0)) _exit(126);
			execl(path, path, descriptor.c_str(), nullptr);
			_exit(127);
		}
		close(fds[1]);
		bool ready = false;
		const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
		while (pid > 0 && !interrupted && std::chrono::steady_clock::now() < deadline) {
			pollfd item{ fds[0], POLLIN, 0 };
			int ret = poll(&item, 1, 100);
			if (ret < 0 && errno == EINTR) continue;
			if (ret < 0) break;
			if (!ret) continue;
			char byte = 0;
			ready = read(fds[0], &byte, 1) == 1 && byte == 'R';
			break;
		}
		close(fds[0]);
		return ready;
	}
	bool finish()
	{
		for (unsigned int n = 0; pid > 0 && n < 200; ++n) {
			pid_t ret = waitpid(pid, &status, WNOHANG);
			if (ret == pid) { pid = -1; return WIFEXITED(status) && !WEXITSTATUS(status); }
			if (ret < 0 && errno != EINTR) { pid = -1; return false; }
			usleep(10000);
		}
		return false;
	}
	~Stepper()
	{
		if (pid > 0) {
			kill(pid, SIGTERM);
			if (!finish() && pid > 0) {
				kill(pid, SIGKILL);
				while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
			}
		}
	}
};

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
			auto gains = request->metadata().get(controls::ColourGains);
			if (!gains || std::abs((*gains)[0] - 1.0f) > 0.0001f || std::abs((*gains)[1] - 1.0f) > 0.0001f)
				++failed;
			else std::cout << "APPLICATION_IPA_METADATA request=" << request->sequence() << " colour_gains_valid=1" << std::endl;
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
		if (frames < 240) {
			request->reuse(Request::ReuseBuffers);
			if (camera->queueRequest(request))
				++failed;
		}
		condition.notify_one();
	}
};

int main(int argc, char **argv)
{
	if (argc != 3)
		return 2;
	std::signal(SIGINT, stopSignal);
	std::signal(SIGTERM, stopSignal);
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
	Stepper stepper;
	if (!stepper.start(argv[2])) { std::cout << "APPLICATION_FAILURE stage=stepper-ready" << std::endl; return 13; }
	int result = 0;
	for (unsigned int epoch = 0; epoch < 1 && !result && !interrupted; ++epoch) {
		std::cout << "APPLICATION_BEGIN epoch=" << epoch << std::endl;
		ControlList controls(camera->controls());
		const std::array<float, 2> gains{ 1.0f, 1.0f };
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
			auto end = std::chrono::steady_clock::now() + std::chrono::seconds(20);
			while (!result && !interrupted && capture.frames < 240 && !capture.failed &&
			       std::chrono::steady_clock::now() < end)
				capture.condition.wait_for(lock, std::chrono::milliseconds(100));
			if (capture.frames < 240 || capture.failed || interrupted)
				result = 11;
			capture.running = false;
		}
		int ret = camera->stop();
		if (ret)
			result = 12;
		std::cout << "APPLICATION_EPOCH epoch=" << epoch << " frames=" << capture.frames
			<< " failed=" << capture.failed << " stop=" << ret << std::endl;
	}
	if (!stepper.finish()) result = 14;
	requests.clear();
	allocator.free(stream);
	std::cout << "APPLICATION_RESULT result=" << result << std::endl;
	return result;
}
