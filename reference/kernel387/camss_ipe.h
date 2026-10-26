/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <map>
#include <memory>
#include <string>

#include <libcamera/base/object.h>
#include <libcamera/base/signal.h>
#include <libcamera/base/timer.h>
#include "libcamera/internal/v4l2_videodevice.h"

namespace libcamera {

/* Own both m2m queues until each side returns, including cancellation. */
class CamssIpe : public Object
{
public:
	explicit CamssIpe(const std::string &node);
	~CamssIpe();
	int start(const V4L2DeviceFormat &format, unsigned int count);
	void stop();
	int queue(FrameBuffer *input, FrameBuffer *output);
	Signal<FrameBuffer *, FrameBuffer *, bool> processed;

private:
	struct Job {
		FrameBuffer *original;
		std::unique_ptr<FrameBuffer> input;
		bool inputDone = false, outputDone = false, failed = false;
	};
	void inputReady(FrameBuffer *buffer);
	void outputReady(FrameBuffer *buffer);
	void complete(FrameBuffer *output);
	void timeout();
	V4L2M2MDevice device_;
	Timer watchdog_;
	bool running_ = false, stopping_ = false, opened_ = false, failed_ = false;
	std::map<FrameBuffer *, Job> jobs_;
	std::map<FrameBuffer *, FrameBuffer *> inputs_;
};

} /* namespace libcamera */
