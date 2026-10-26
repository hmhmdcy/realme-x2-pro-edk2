/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "../src/libcamera/software_isp/debayer_cpu.h"
#include "libcamera/internal/dma_buf_allocator.h"
#include "libcamera/internal/framebuffer.h"
#include "libcamera/internal/software_isp/swisp_stats.h"

#include <libcamera/formats.h>
#include <linux/dma-buf.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

#include <algorithm>
#include <chrono>
#include <cstring>
#include <iostream>
#include <stdexcept>

using namespace libcamera;

static void require(bool value, const char *what)
{
	if (!value) throw std::runtime_error(what);
}

class Mapping
{
public:
	Mapping(const FrameBuffer::Plane &plane, bool write)
		: fd_(plane.fd.get()), length_(plane.length), write_(write)
	{
		dma_buf_sync sync{};
		sync.flags = DMA_BUF_SYNC_START | (write_ ? DMA_BUF_SYNC_WRITE : DMA_BUF_SYNC_READ);
		require(ioctl(fd_, DMA_BUF_IOCTL_SYNC, &sync) == 0, "dma sync start");
		data_ = mmap(nullptr, length_, PROT_READ | (write_ ? PROT_WRITE : 0), MAP_SHARED, fd_, 0);
		require(data_ != MAP_FAILED, "mmap");
	}
	~Mapping()
	{
		munmap(data_, length_);
		dma_buf_sync sync{};
		sync.flags = DMA_BUF_SYNC_END | (write_ ? DMA_BUF_SYNC_WRITE : DMA_BUF_SYNC_READ);
		if (ioctl(fd_, DMA_BUF_IOCTL_SYNC, &sync)) std::terminate();
	}

	uint8_t *data() { return static_cast<uint8_t *>(data_); }
private:
	int fd_;
	size_t length_;
	bool write_;
	void *data_;
};

int main(int argc, char **)
try {
	CameraManager cm; /* Deliberately do not enumerate or start any camera. */
	auto stats = std::make_unique<SwStatsCpu>(cm);
	require(stats->isValid(), "stats shared memory");
	const int statsFd = stats->getStatsFD().get();
	DebayerCpu debayer(std::move(stats), cm, true);
	const Size full(4608, 3456);
	if (argc == 1) {
		require(debayer.sizes(formats::SRGGB10_CSI2P, full).max.isNull(), "full mode must be opt-in");
		std::cout << "{\"default_full_mode_rejected\":true}\n";
		return 0;
	}
	if (access("/dev/dma_heap/system", R_OK | W_OK)) return 77;
	require(debayer.sizes(formats::SRGGB10_CSI2P, full).max == full, "native size retained");
	DmaBufAllocator heap(DmaBufAllocator::DmaBufAllocatorFlag::SystemHeap);
	require(heap.isValid(), "system heap");
	std::vector<std::unique_ptr<FrameBuffer>> inputs, outputs;
	const unsigned int rawBytes = 5760 * 3456;
	const unsigned int outBytes = 4608 * 3456 * 4 + 4096;
	require(heap.exportBuffers(4, { rawBytes }, &inputs) == 4, "four full RAW buffers");
	require(heap.exportBuffers(4, { outBytes }, &outputs) == 4, "four full RGBA buffers");
	const std::array<PixelFormat, 4> formatsIn = {
		formats::SRGGB10_CSI2P, formats::SGRBG10_CSI2P,
		formats::SGBRG10_CSI2P, formats::SBGGR10_CSI2P
	};
	const std::array<PixelFormat, 6> formatsOut = {
		formats::RGB888, formats::BGR888, formats::XRGB8888,
		formats::XBGR8888, formats::ARGB8888, formats::ABGR8888
	};
	unsigned int cases = 0;
	uint64_t checked = 0;
	auto run = [&](PixelFormat inputFormat, PixelFormat outputFormat,
		       unsigned int rx, unsigned int ry, bool ccm, bool quad) {
		StreamConfiguration input, output;
		input.pixelFormat = inputFormat;
		input.size = quad ? full : Size(24, 16);
		input.stride = quad ? 5760 : 32;
		input.bufferCount = 4;
		output.pixelFormat = outputFormat;
		output.size = quad ? full : Size(16, 16);
		std::tie(output.stride, output.frameSize) = debayer.strideAndFrameSize(outputFormat, output.size);
		output.bufferCount = 4;
		require(debayer.configure(input, { std::cref(output) }, ccm) == 0, "configure CPU ISP");
		if (quad) {
			auto smaller = output;
			smaller.size = Size(2304, 1728);
			std::tie(smaller.stride, smaller.frameSize) = debayer.strideAndFrameSize(outputFormat, smaller.size);
			require(debayer.configure(input, { std::cref(smaller) }, ccm) != 0, "no hidden half-size output");
			require(debayer.configure(input, { std::cref(output) }, ccm) == 0, "reconfigure after rejection");
		}
		{
			Mapping in(inputs[0]->planes()[0], true);
			for (unsigned int y = 0; y < input.size.height; y++) {
				uint8_t *row = in.data() + size_t(y) * input.stride;
				for (unsigned int x = 0; x < input.size.width; x += 4) {
					row[x / 4 * 5 + 4] = 0;
					for (unsigned int i = 0; i < 4; i++) {
						const bool redColumn = (((x + i) / (quad ? 2 : 1)) % 2) == rx;
						const bool redRow = ((y / (quad ? 2 : 1)) % 2) == ry;
						const uint16_t value = redColumn != redRow ? 512 : (redColumn ? 128 : 896);
						row[x / 4 * 5 + i] = value >> 2;
					}
				}
			}
		}
		{
			Mapping out(outputs[0]->planes()[0], true);
			std::memset(out.data(), 0xa5, outBytes);
		}
		DebayerParams parameters;
		if (ccm)
			parameters.combinedMatrix = { { 0.0, 0.0, 1.0,
						       0.0, 1.0, 0.0,
						       1.0, 0.0, 0.0 } };
		auto &meta = inputs[0]->_d()->metadata();
		meta.status = FrameMetadata::FrameSuccess;
		meta.sequence = cases;
		meta.timestamp = 123456 + cases;
		meta.planes()[0].bytesused = input.stride * input.size.height;
		require(debayer.start() == 0, "start CPU workers");
		debayer.process(0, inputs[0].get(), outputs[0].get(), parameters);
		debayer.stop();
		require(outputs[0]->metadata().status == FrameMetadata::FrameSuccess, "CPU metadata success");
		require(outputs[0]->metadata().sequence == meta.sequence &&
			outputs[0]->metadata().timestamp == meta.timestamp, "metadata preserved");
		if (quad)
			require(outputs[0]->metadata().planes()[0].bytesused == output.frameSize, "actual output bytes used");
		{
			Mapping out(outputs[0]->planes()[0], false);
			const bool bgr = outputFormat == formats::RGB888 || outputFormat == formats::XRGB8888 || outputFormat == formats::ARGB8888;
			const unsigned int bpp = outputFormat == formats::RGB888 || outputFormat == formats::BGR888 ? 3 : 4;
			for (unsigned int y = 0; y < output.size.height; y++)
				for (unsigned int x = 0; x < output.size.width; x++) {
					const uint8_t *pixel = out.data() + size_t(y) * output.stride + x * bpp;
					const unsigned int red = ccm ? 223 : 31;
					const unsigned int blue = ccm ? 31 : 223;
					require(pixel[0] == (bgr ? blue : red) && pixel[1] == 127 && pixel[2] == (bgr ? red : blue), "RGB order/LUT/CCM/border");
					if (bpp == 4) require(pixel[3] == 255, "alpha byte");
					checked++;
				}
			require(out.data()[output.frameSize] == 0xa5 && out.data()[outBytes - 1] == 0xa5, "output guard bytes");
		}
		const auto *s = static_cast<SwIspStats *>(mmap(nullptr, sizeof(SwIspStats), PROT_READ, MAP_SHARED, statsFd, 0));
		require(s != MAP_FAILED && s->valid && s->sum_.r() > 0 &&
			s->sum_.g() == s->sum_.r() * 4 && s->sum_.b() == s->sum_.r() * 7, "quad/ordinary statistics");
		munmap(const_cast<SwIspStats *>(s), sizeof(SwIspStats));
		cases++;
	};
	const auto started = std::chrono::steady_clock::now();
	for (unsigned int order = 0; order < formatsIn.size(); order++)
		for (const auto &format : formatsOut)
			for (bool ccm : { false, true })
				run(formatsIn[order], format, order & 1, order >> 1, ccm, true);
	/* Reuse the same object across full -> ordinary -> full configuration. */
	run(formats::SRGGB10_CSI2P, formats::RGB888, 0, 0, false, false);
	run(formats::SRGGB10_CSI2P, formats::BGR888, 0, 0, true, true);
	std::cout << "{\"cpu_isp_cases\":" << cases << ",\"pixels_checked\":" << checked
		  << ",\"four_raw_and_four_rgba_buffers_bytes\":" << uint64_t(4) * (rawBytes + outBytes)
		  << ",\"all_four_orders_six_formats_ccm_on_off\":true,\"non_identity_ccm\":true,\"statistics_verified\":true"
		  << ",\"full_ordinary_full_transition\":true,\"elapsed_seconds\":"
		  << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count()
		  << ",\"passed\":true}\n";
	return 0;
} catch (const std::exception &e) {
	std::cerr << e.what() << '\n';
	return 1;
}
