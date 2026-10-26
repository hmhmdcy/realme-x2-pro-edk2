/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "camss_ipe.h"

#include <cerrno>
#include <chrono>
#include <vector>
#include <libcamera/base/log.h>
#include "libcamera/internal/framebuffer.h"

namespace libcamera {

LOG_DECLARE_CATEGORY(CamssVfe)

CamssIpe::CamssIpe(const std::string &node) : device_(node)
{
	device_.output()->bufferReady.connect(this, &CamssIpe::inputReady);
	device_.capture()->bufferReady.connect(this, &CamssIpe::outputReady);
	/* The string-based V4L2M2MDevice construction in this libcamera version
	 * does not connect the video-device watchdog. Own the job timer here.
	 */
	watchdog_.timeout.connect(this, &CamssIpe::timeout);
}

CamssIpe::~CamssIpe()
{
	stop();
}

int CamssIpe::start(const V4L2DeviceFormat &format, unsigned int count)
{
	if (running_ || stopping_ || !jobs_.empty())
		return -EBUSY;
	/* A failed STREAMOFF leaves the library queue bookkeeping unresolved.
	 * close has joined the kernel work, but this object must not reopen it.
	 */
	if (failed_)
		return -EIO;
	int ret = device_.open();
	if (ret)
		return ret;
	opened_ = true;
	for (V4L2VideoDevice *queue : { device_.output(), device_.capture() }) {
		V4L2DeviceFormat negotiated = format;
		ret = queue->setFormat(&negotiated);
		if (!ret && (negotiated.fourcc != format.fourcc ||
			     negotiated.size != format.size ||
			     negotiated.planesCount != format.planesCount ||
			     negotiated.planes[0].bpl != format.planes[0].bpl ||
			     negotiated.planes[0].size != format.planes[0].size))
			ret = -EINVAL;
		if (ret) {
			stop();
			return ret;
		}
	}
	/* Geometry is shared by both queues. Finish both S_FMT calls before
	 * either REQBUFS: this driver rejects format changes once buffers exist.
	 */
	for (V4L2VideoDevice *queue : { device_.output(), device_.capture() }) {
		ret = queue->importBuffers(count);
		if (ret) {
			stop();
			return ret;
		}
	}
	for (V4L2VideoDevice *queue : { device_.output(), device_.capture() }) {
		ret = queue->streamOn();
		if (ret) {
			stop();
			return ret;
		}
	}
	running_ = true;
	LOG(CamssVfe, Info) << "IPE enabled " << format.toString();
	return 0;
}

int CamssIpe::queue(FrameBuffer *input, FrameBuffer *output)
{
	if (!running_ || stopping_)
		return -EPIPE;
	if (!input || !output || input == output || jobs_.count(output))
		return -EINVAL;
	auto planes = input->planes();
	Job job{ input, std::make_unique<FrameBuffer>(
		std::vector<FrameBuffer::Plane>(planes.begin(), planes.end())) };
	/* OUTPUT DQBUF writes sequence/timestamp. Preserve the IFE SOF by using
	 * a wrapper with shared plane FDs, not the original camera buffer.
	 */
	job.input->_d()->metadata() = input->metadata();
	FrameBuffer *wrapped = job.input.get();
	inputs_.emplace(wrapped, output);
	jobs_.emplace(output, std::move(job));
	if (jobs_.size() == 1)
		watchdog_.start(std::chrono::seconds(3));
	int ret = device_.capture()->queueBuffer(output);
	if (!ret)
		ret = device_.output()->queueBuffer(wrapped);
	if (ret) {
		LOG(CamssVfe, Error) << "IPE queue failed: " << ret;
		/* A one-sided QBUF must never shift the FIFO pairing. Once adopted,
		 * the job always completes via the signal, including this failure.
		 */
		stop();
	}
	return 0;
}

void CamssIpe::inputReady(FrameBuffer *buffer)
{
	auto it = inputs_.find(buffer);
	if (it == inputs_.end())
		return;
	FrameBuffer *output = it->second;
	Job &job = jobs_.at(output);
	job.inputDone = true;
	job.failed |= buffer->metadata().status != FrameMetadata::FrameSuccess;
	complete(output);
}

void CamssIpe::outputReady(FrameBuffer *buffer)
{
	auto it = jobs_.find(buffer);
	if (it == jobs_.end())
		return;
	it->second.outputDone = true;
	it->second.failed |= buffer->metadata().status != FrameMetadata::FrameSuccess;
	complete(buffer);
}

void CamssIpe::complete(FrameBuffer *output)
{
	auto it = jobs_.find(output);
	if (it == jobs_.end() || !it->second.inputDone || !it->second.outputDone)
		return;
	Job job = std::move(it->second);
	inputs_.erase(job.input.get());
	jobs_.erase(it);
	if (!running_ || jobs_.empty())
		watchdog_.stop();
	else
		watchdog_.start(std::chrono::seconds(3));
	processed.emit(job.original, output, !job.failed && running_);
}

void CamssIpe::stop()
{
	running_ = false;
	watchdog_.stop();
	if (stopping_ || !opened_)
		return;
	stopping_ = true;
	int inputError = device_.output()->streamOff();
	int outputError = device_.capture()->streamOff();
	failed_ |= inputError || outputError;
	/* close() also joins the driver's work when STREAMOFF itself failed.
	 * Keep all imported FDs and original IFE buffers alive until then.
	 */
	device_.close();
	opened_ = false;
	while (!jobs_.empty()) {
		FrameBuffer *output = jobs_.begin()->first;
		Job &job = jobs_.begin()->second;
		job.inputDone = job.outputDone = job.failed = true;
		complete(output);
	}
	stopping_ = false;
}

void CamssIpe::timeout()
{
	LOG(CamssVfe, Error) << "IPE dequeue timeout";
	stop();
}

} /* namespace libcamera */
