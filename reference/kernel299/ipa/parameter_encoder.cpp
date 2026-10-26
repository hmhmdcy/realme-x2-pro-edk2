/* SPDX-License-Identifier: LGPL-2.1-or-later */

#include "parameter_encoder.h"

#include <cerrno>
#include <cmath>
#include <limits>

#include "params.h"

namespace libcamera::ipa::camss {

static int gainQ10(double value, uint16_t *encoded)
{
	if (!std::isfinite(value) || value < 0 || value > 32767.0 / 1024)
		return -ERANGE;

	*encoded = std::lround(value * 1024);
	return 0;
}

int encodeParameters(Span<uint8_t> output, const ResidualBlackProfile &profile,
		     double redGain, double blueGain, const Size &input,
		     const Rectangle &roi, size_t *bytesused)
{
	if (!bytesused)
		return -EINVAL;
	*bytesused = 0;

	constexpr size_t required = sizeof(v4l2_isp_buffer) +
				    sizeof(camss_params_wb_gain) +
				    sizeof(camss_params_aec_bhist);
	if (output.size() < required)
		return -ENOSPC;
	if (!output.data() ||
	    reinterpret_cast<uintptr_t>(output.data()) % alignof(v4l2_isp_buffer))
		return -EINVAL;

	if (!std::isfinite(profile.normalization) || profile.normalization <= 0 ||
	    !std::isfinite(redGain) || redGain < 0 ||
	    !std::isfinite(blueGain) || blueGain < 0)
		return -ERANGE;

	if (roi.x < 0 || roi.y < 0 || roi.width < 4 || roi.height < 2 ||
	    ((roi.x | roi.y | roi.width | roi.height) & 1) ||
	    static_cast<uint64_t>(roi.x) + roi.width > input.width ||
	    static_cast<uint64_t>(roi.y) + roi.height > input.height ||
	    roi.x > 65535 || roi.y > 65535 ||
	    roi.width > 65535 || roi.height > 65535)
		return -EINVAL;

	uint16_t red, green, blue;
	if (gainQ10(redGain * profile.normalization, &red) ||
	    gainQ10(profile.normalization, &green) ||
	    gainQ10(blueGain * profile.normalization, &blue))
		return -ERANGE;

	CamssParams params(output);
	auto wb = params.block<CamssBlocks::AwbGains>();
	wb.setEnabled(true);
	wb->r_gain = red;
	wb->g_gain = green;
	wb->b_gain = blue;
	wb->r_sub = wb->g_sub = wb->b_sub = profile.subtraction;

	auto bhist = params.block<CamssBlocks::AecBhist>();
	bhist.setEnabled(true);
	bhist->left = roi.x;
	bhist->top = roi.y;
	bhist->width = roi.width;
	bhist->height = roi.height;

	*bytesused = params.bytesused();
	return 0;
}

} /* namespace libcamera::ipa::camss */
