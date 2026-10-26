/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <cstdint>
#include <deque>
#include <map>
#include <memory>
#include <string>
#include <vector>
#include <linux/qcom-ipe-a5.h>

#include <libcamera/base/object.h>
#include <libcamera/base/signal.h>
#include <libcamera/base/timer.h>
#include "libcamera/internal/media_device.h"
#include "libcamera/internal/v4l2_videodevice.h"

namespace libcamera {

/* Own both image queues and request parameters until all three complete. */
class CamssIpe : public Object
{
public:
	explicit CamssIpe(const std::string &node, std::shared_ptr<MediaDevice> media);
	~CamssIpe();
	int start(const V4L2DeviceFormat &format, unsigned int count);
	void stop();
	int queue(FrameBuffer *input, FrameBuffer *output,
		  const qcom_ipe_a5_frame_params *params = nullptr);
	Signal<FrameBuffer *, FrameBuffer *, bool> processed;

private:
	struct Job {
		FrameBuffer *original;
		std::unique_ptr<FrameBuffer> input;
		V4L2Request *request = nullptr;
		uint64_t serial = 0;
		bool inputDone = false, outputDone = false, requestDone = true, failed = false;
	};
	void inputReady(FrameBuffer *buffer);
	void outputReady(FrameBuffer *buffer);
	void requestReady(V4L2Request *request);
	void finishRequest(FrameBuffer *output, uint64_t serial, int error);
	void complete(FrameBuffer *output);
	void timeout();
	V4L2M2MDevice device_;
	std::shared_ptr<MediaDevice> media_;
	Timer watchdog_;
	bool running_ = false, stopping_ = false, opened_ = false, failed_ = false;
	bool requestsEnabled_ = false;
	uint64_t nextSerial_ = 0;
	std::vector<std::unique_ptr<V4L2Request>> requests_;
	std::deque<V4L2Request *> freeRequests_;
	std::map<V4L2Request *, FrameBuffer *> requestOutputs_;
	std::map<FrameBuffer *, Job> jobs_;
	std::map<FrameBuffer *, FrameBuffer *> inputs_;
};

} /* namespace libcamera */
