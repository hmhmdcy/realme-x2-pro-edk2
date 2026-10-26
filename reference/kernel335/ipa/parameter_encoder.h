/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <cstddef>
#include <cstdint>
#include <linux/qcom-camss-config.h>

#include <libcamera/base/span.h>
#include <libcamera/geometry.h>

namespace libcamera::ipa::camss {

/* Residual BLS at this ISP stage, not sensor black metadata for software ISP. */
struct ResidualBlackProfile {
	uint16_t subtraction;
	double normalization;
};

int effectiveColourGains(const ResidualBlackProfile &profile, double red, double blue,
			 double *effectiveRed, double *effectiveBlue);

/* Serialize only supported blocks through the shared libipa V4L2Params helper. */
int encodeParameters(Span<uint8_t> output, const ResidualBlackProfile &profile,
		     double redGain, double blueGain, const Size &input,
		     const Rectangle &roi, size_t *bytesused,
		     const camss_params_lsc *lsc = nullptr,
		     const camss_params_color_correct *ccm = nullptr);

} /* namespace libcamera::ipa::camss */
