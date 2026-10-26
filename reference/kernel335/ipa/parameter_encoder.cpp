/* SPDX-License-Identifier: LGPL-2.1-or-later */

#include "parameter_encoder.h"

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstring>
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

int effectiveColourGains(const ResidualBlackProfile &profile, double red, double blue,
			 double *effectiveRed, double *effectiveBlue)
{
	uint16_t r, g, b;
	if (!effectiveRed || !effectiveBlue ||
	    gainQ10(red * profile.normalization, &r) ||
	    gainQ10(profile.normalization, &g) ||
	    gainQ10(blue * profile.normalization, &b))
		return -ERANGE;
	/* VFE175 converts the common U15Q10 fields to U12Q7. */
	const unsigned int rq7 = std::min<unsigned int>((r + 4) >> 3, 4095);
	const unsigned int gq7 = std::min<unsigned int>((g + 4) >> 3, 4095);
	const unsigned int bq7 = std::min<unsigned int>((b + 4) >> 3, 4095);
	if (!gq7)
		return -ERANGE;
	*effectiveRed = double(rq7) / gq7;
	*effectiveBlue = double(bq7) / gq7;
	return 0;
}

int encodeParameters(Span<uint8_t> output, const ResidualBlackProfile &profile,
		     double redGain, double blueGain, const Size &input,
		     const Rectangle &roi, size_t *bytesused,
		     const camss_params_lsc *lsc, const camss_params_color_correct *ccm)
{
	if (!bytesused)
		return -EINVAL;
	*bytesused = 0;

	const size_t required = sizeof(v4l2_isp_buffer) +
				    sizeof(camss_params_wb_gain) +
				    sizeof(camss_params_aec_bhist) + (lsc ? sizeof(*lsc) : 0) + (ccm ? sizeof(*ccm) : 0);
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


 if (lsc) {
  auto block = params.block<CamssBlocks::LensShading>();
  block.setEnabled(true);
  std::memcpy(&block->cell_width, &lsc->cell_width, sizeof(*lsc) - sizeof(lsc->header));
 }
 if (ccm) {
  auto block = params.block<CamssBlocks::ColorCorrect>();
  block.setEnabled(true);
  std::memcpy(&block->a, &ccm->a, sizeof(*ccm) - sizeof(ccm->header));
 }
	*bytesused = params.bytesused();
	return 0;
}

} /* namespace libcamera::ipa::camss */
