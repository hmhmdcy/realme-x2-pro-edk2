/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <cassert>
#include <cerrno>
#include <climits>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>

#include "parameter_encoder.h"
#include "params.h"

using namespace libcamera;
using namespace libcamera::ipa::camss;

int main(int argc, char **argv)
{
	assert(argc == 2);
	constexpr size_t count = sizeof(v4l2_isp_buffer) + sizeof(camss_params_wb_gain) + sizeof(camss_params_aec_bhist);
	static_assert(count == 56);
	alignas(8) std::array<uint8_t, 80> output, expected;
	output.fill(0xa5); expected.fill(0xa5);
	ResidualBlackProfile profile{3840, 2175.0 / 2048};
	Size input{1632, 1224}; Rectangle roi{0, 0, 1632, 1224};
	size_t used = 777;
	assert(!encodeParameters(output, profile, 1, 1, input, roi, &used) && used == count);
	/* Independent wire image using the public C structures, not the builder. */
	v4l2_isp_buffer envelope{}; envelope.version = V4L2_ISP_VERSION_V1;
	envelope.data_size = sizeof(camss_params_wb_gain) + sizeof(camss_params_aec_bhist);
	camss_params_wb_gain wb{};
	wb.header = {CAMSS_PARAMS_WB_GAIN, V4L2_ISP_PARAMS_FL_BLOCK_ENABLE, sizeof(wb)};
	wb.g_gain = wb.r_gain = wb.b_gain = 1088;
	wb.g_sub = wb.r_sub = wb.b_sub = 3840;
	camss_params_aec_bhist histogram{};
	histogram.header = {CAMSS_PARAMS_AEC_BHIST, V4L2_ISP_PARAMS_FL_BLOCK_ENABLE, sizeof(histogram)};
	histogram.width = 1632; histogram.height = 1224;
	std::memcpy(expected.data(), &envelope, sizeof(envelope));
	std::memcpy(expected.data() + sizeof(envelope), &wb, sizeof(wb));
	std::memcpy(expected.data() + sizeof(envelope) + sizeof(wb), &histogram, sizeof(histogram));
	assert(output == expected);
	std::ofstream file(argv[1], std::ios::binary); file.write(reinterpret_cast<const char *>(output.data()), used); file.close(); assert(file.good());
	auto valid = output;
	auto reject = [&](Span<uint8_t> buffer, ResidualBlackProfile p, double r, double b, Rectangle rect, int error) {
		used = 777;
		assert(encodeParameters(buffer, p, r, b, input, rect, &used) == error && used == 0);
		assert(output == valid);
	};
	reject(Span<uint8_t>(output).first(count - 1), profile, 1, 1, roi, -ENOSPC);
	reject(Span<uint8_t>(output).subspan(1), profile, 1, 1, roi, -EINVAL);
	reject(Span<uint8_t>(nullptr, 80), profile, 1, 1, roi, -EINVAL);
	for (double bad : {-1., std::numeric_limits<double>::infinity(), std::numeric_limits<double>::quiet_NaN()}) {
		reject(output, profile, bad, 1, roi, -ERANGE);
		reject(output, profile, 1, bad, roi, -ERANGE);
		reject(output, {3840, bad}, 1, 1, roi, -ERANGE);
	}
	reject(output, {3840, 0}, 1, 1, roi, -ERANGE);
	reject(output, profile, 32, 1, roi, -ERANGE);
	for (Rectangle bad : {Rectangle{-2, 0, 4, 2}, Rectangle{1, 0, 4, 2}, Rectangle{0, 0, 2, 2}, Rectangle{0, 0, 4, 3}, Rectangle{1630, 0, 4, 2}, Rectangle{INT_MAX, 0, UINT_MAX, 2}})
		reject(output, profile, 1, 1, bad, -EINVAL);
	assert(encodeParameters(output, profile, 1, 1, input, roi, nullptr) == -EINVAL && output == valid);
	assert(!encodeParameters(output, {0, 1}, 0.5, 0.75, input, {0, 0, 4, 2}, &used));
	const auto *values = reinterpret_cast<const camss_params_wb_gain *>(output.data() + sizeof(envelope));
	assert(values->r_gain == 512 && values->g_gain == 1024 && values->b_gain == 768 && !values->r_sub && !values->g_add);
	std::cout << "CAMSS_ENCODER_CONTRACTS_PASSED\n";
}
