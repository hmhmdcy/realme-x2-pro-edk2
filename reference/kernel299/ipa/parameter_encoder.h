/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <cstddef>
#include <cstdint>

#include <libcamera/base/span.h>
#include <libcamera/geometry.h>

namespace libcamera::ipa::camss {

/* Residual BLS at this ISP stage, not sensor black metadata for software ISP. */
struct ResidualBlackProfile {
	uint16_t subtraction;
	double normalization;
};

/* Serialize only supported blocks through the shared libipa V4L2Params helper. */
int encodeParameters(Span<uint8_t> output, const ResidualBlackProfile &profile,
		     double redGain, double blueGain, const Size &input,
		     const Rectangle &roi, size_t *bytesused);

} /* namespace libcamera::ipa::camss */
