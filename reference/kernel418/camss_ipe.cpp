/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "camss_ipe.h"

#include <cerrno>
#include <chrono>
#include <vector>
#include <libcamera/base/log.h>
#include "libcamera/internal/framebuffer.h"

namespace libcamera {

LOG_DECLARE_CATEGORY(CamssVfe)

CamssIpe::CamssIpe(const std::string &node, std::shared_ptr<MediaDevice> media)
	: device_(node), media_(std::move(media))
{
	device_.output()->bufferReady.connect(this, &CamssIpe::inputReady);
	device_.capture()->bufferReady.connect(this, &CamssIpe::outputReady);
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
	if (!count)
		return -EINVAL;
	if (failed_)
		return -EIO;
	int ret = device_.open();
	if (ret)
		return ret;
	opened_ = true;
	const auto *info = device_.output()->controlInfo(V4L2_CID_QCOM_IPE_A5_FRAME_PARAMS);
	requestsEnabled_ = info;
	if (requestsEnabled_) {
		if (info->type != V4L2_CTRL_TYPE_U8 || info->elem_size != 1 ||
		    info->elems != sizeof(qcom_ipe_a5_frame_params) ||
		    info->nr_of_dims != 1 || info->dims[0] != sizeof(qcom_ipe_a5_frame_params)) {
			stop();
			return -EINVAL;
		}
		if (!media_ || !media_->supportsRequests()) {
			stop();
			return -ENOTSUP;
		}
		ret = media_->allocateRequests(count, &requests_);
		if (ret) {
			stop();
			return ret;
		}
		for (auto &request : requests_) {
			request->requestDone.connect(this, &CamssIpe::requestReady);
			freeRequests_.push_back(request.get());
		}
	}
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
	/* Both formats must precede either REQBUFS for shared geometry. */
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
	LOG(CamssVfe, Info) << "IPE enabled " << format.toString()
		<< " requests=" << requestsEnabled_;
	return 0;
}

int CamssIpe::queue(FrameBuffer *input, FrameBuffer *output,
		    const qcom_ipe_a5_frame_params *params)
{
	if (!running_ || stopping_)
		return -EPIPE;
	if (!input || !output || input == output || jobs_.count(output))
		return -EINVAL;
	for (const auto &[buffer, job] : jobs_) {
		(void)buffer;
		if (job.original == input)
			return -EBUSY;
	}
	if (params && !requestsEnabled_)
		return -ENOTSUP;
	V4L2Request *request = nullptr;
	if (requestsEnabled_) {
		if (freeRequests_.empty())
			return -ENOBUFS;
		request = freeRequests_.front();
		const qcom_ipe_a5_frame_params bypass{};
		const auto *packet = params ? params : &bypass;
		ControlList controls(device_.output()->controls());
		ControlValue value;
		value.set(Span<const uint8_t>(reinterpret_cast<const uint8_t *>(packet), sizeof(*packet)));
		controls.set(V4L2_CID_QCOM_IPE_A5_FRAME_PARAMS, value);
		int ret = device_.output()->setControls(&controls, request);
		if (ret) {
			if (request->reinit())
				stop();
			return ret;
		}
	}
	auto planes = input->planes();
	Job job{ input, std::make_unique<FrameBuffer>(
		std::vector<FrameBuffer::Plane>(planes.begin(), planes.end())) };
	/* OUTPUT DQBUF must not overwrite the original IFE SOF metadata. */
	job.input->_d()->metadata() = input->metadata();
	job.request = request;
	job.requestDone = !request;
	job.serial = ++nextSerial_;
	FrameBuffer *wrapped = job.input.get();
	inputs_.emplace(wrapped, output);
	jobs_.emplace(output, std::move(job));
	if (request) {
		freeRequests_.pop_front();
		requestOutputs_.emplace(request, output);
	}
	if (jobs_.size() == 1)
		watchdog_.start(std::chrono::seconds(3));
	int ret = device_.capture()->queueBuffer(output);
	if (!ret)
		ret = device_.output()->queueBuffer(wrapped, request);
	if (!ret && request)
		ret = request->queue();
	if (ret) {
		LOG(CamssVfe, Error) << "IPE queue failed: " << ret;
		/* Once adopted, partial submission completes through processed. */
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

void CamssIpe::requestReady(V4L2Request *request)
{
	auto it = requestOutputs_.find(request);
	if (it == requestOutputs_.end())
		return;
	Job &job = jobs_.at(it->second);
	int ret = request->reinit(); /* Also disables the level-triggered notifier. */
	if (!ret)
		job.requestDone = true;
	/* A completion callback may stop and destroy the request pool. Defer
	 * that possibility until V4L2Request::requestReady() has unwound.
	 */
	invokeMethod(&CamssIpe::finishRequest, ConnectionTypeQueued,
		     it->second, job.serial, ret);
}

void CamssIpe::finishRequest(FrameBuffer *output, uint64_t serial, int error)
{
	auto it = jobs_.find(output);
	if (it == jobs_.end() || it->second.serial != serial)
		return;
	if (error) {
		LOG(CamssVfe, Error) << "IPE request reinit failed: " << error;
		stop();
		return;
	}
	complete(output);
}

void CamssIpe::complete(FrameBuffer *output)
{
	auto it = jobs_.find(output);
	if (it == jobs_.end() || !it->second.inputDone || !it->second.outputDone ||
	    !it->second.requestDone)
		return;
	Job job = std::move(it->second);
	inputs_.erase(job.input.get());
	jobs_.erase(it);
	if (job.request) {
		requestOutputs_.erase(job.request);
		if (running_)
			freeRequests_.push_back(job.request);
	}
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
	/* Keep image wrappers, plane FDs and request FDs through the driver's
	 * close/join, even when one of the STREAMOFF calls failed.
	 */
	device_.close();
	opened_ = false;
	freeRequests_.clear();
	requestOutputs_.clear();
	requests_.clear();
	requestsEnabled_ = false;
	while (!jobs_.empty()) {
		FrameBuffer *output = jobs_.begin()->first;
		Job &job = jobs_.begin()->second;
		job.request = nullptr;
		job.inputDone = job.outputDone = job.requestDone = job.failed = true;
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
