/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "tmc10.h"
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace libcamera::ipa {
namespace {
float mul(float a, float b)
{
	volatile float value = a * b;
	return value;
}
bool nearZero(float value)
{
	return std::abs(double(value)) < 1e-9;
}
template<std::size_t N>
bool finite(const std::array<float, N> &values)
{
	return std::all_of(values.begin(), values.end(), [](float value) { return std::isfinite(value); });
}
bool coefficients(Tmc10Curve &curve)
{
	float h1 = curve.x[1] - curve.x[0], h2 = curve.x[2] - curve.x[1], h3 = curve.x[3] - curve.x[2];
	float a = nearZero(h1) ? 0 : (curve.y[1] - curve.y[0]) / h1;
	float b = nearZero(h2) ? 0 : (curve.y[2] - curve.y[1]) / h2;
	float c = nearZero(h3) ? 0 : (curve.y[3] - curve.y[2]) / h3;
	float w1 = mul(2, h2) + h1, w2 = h2 + mul(2, h1);
	float d2 = (w1 + w2) / (w1 / a + w2 / b);
	w1 = mul(2, h3) + h2;
	w2 = h3 + mul(2, h2);
	float d3 = (w1 + w2) / (w1 / b + w2 / c);
	float endpoint = nearZero(h2 + h3) ? 0 :
		(mul(mul(2, h3) + h2, c) - mul(h3, b)) / (h2 + h3);
	float d4 = mul(b, c) < 0 && std::abs(endpoint) > std::abs(mul(3, c)) ? mul(3, c) :
		(mul(endpoint, c) < 0 ? 0 : endpoint);
	curve.coefficient = {d2,
		nearZero(h2) ? 0 : (mul(3, b) - mul(2, d2) - d3) / h2,
		nearZero(h2) ? 0 : (d2 - mul(2, b) + d3) / mul(h2, h2),
		d3,
		nearZero(h3) ? 0 : (mul(3, c) - mul(2, d3) - d4) / h3,
		nearZero(h3) ? 0 : (d3 - mul(2, c) + d4) / mul(h3, h3)};
	return finite(curve.coefficient);
}
uint32_t gainIndex(float gain)
{
	/* The retained target uses logf and rounds the float quotient. A double
	 * quotient selects a different step at some half-index boundaries. */
	return std::min(uint32_t(std::round(std::log(gain) / std::log(1.03f))), 94U);
}
} /* namespace */

bool calculateTmc10Curve(const Tmc10Parameters &in, Tmc10Curve *output)
{
	std::array<float, 7> values = {in.drcGain, in.drcGainDark, in.gtmPercentage,
		in.ltmPercentage, in.kneeOutMid, in.darkBoostRatio, in.coreReserve1};
	if (!output || !finite(values) || in.drcGain < 1 || in.drcGainDark < 1 ||
	    std::any_of(values.begin() + 2, values.end(), [](float value) { return value < 0 || value > 1; }))
		return false;
	float gain = std::pow(1.03f, float(gainIndex(in.drcGain)));
	float ratio = std::clamp(mul(in.drcGainDark - 1, in.darkBoostRatio) + 1 + in.coreReserve1, 1.0f, 16.0f);
	Tmc10Curve result{};
	result.darkGain = mul(gain, ratio);
	float maxPercentage = std::log(8.0f) / std::log(std::pow(1.03f, float(gainIndex(result.darkGain))));
	maxPercentage = std::min(maxPercentage, 1.0f);
	result.ltmPercentage = in.ltmPercentage;
	result.gtmPercentage = in.gtmPercentage;
	if (result.ltmPercentage > maxPercentage) {
		result.ltmPercentage = maxPercentage;
		result.gtmPercentage = 1 - result.ltmPercentage;
	}
	if (nearZero(ratio - 1))
		ratio = 1.0001f;
	float darkY = in.kneeOutMid / ratio;
	result.x = {0, darkY / result.darkGain, in.kneeOutMid / gain, 1};
	result.y = {0, darkY, in.kneeOutMid, 1};
	result.ltmMix = std::clamp(2 - result.darkGain, 0.0f, 1.0f);
	if (!finite(result.x) || !finite(result.y) || !coefficients(result))
		return false;
	*output = result;
	return true;
}

bool sampleTmc10LtmGain(const Tmc10Curve &curve,
		       const std::array<float, 65> &equivalent,
		       std::array<float, 65> *output)
{
	if (!output || !finite(curve.x) || !finite(curve.y) || !finite(curve.coefficient) ||
	    !finite(equivalent) || !std::isfinite(curve.darkGain) || curve.darkGain < 1 ||
	    !std::isfinite(curve.ltmPercentage) || curve.ltmPercentage < 0 || curve.ltmPercentage > 1 ||
	    equivalent[64] <= 0 || std::any_of(equivalent.begin(), equivalent.end(), [&](float value) {
		return value < 0 || value > equivalent[64];
	    }))
		return false;
	std::array<float, 65> result;
	for (std::size_t i = 1; i < 65; ++i) {
		float x = equivalent[i] / equivalent[64];
		float y;
		if (x <= curve.x[1]) {
			y = mul(x, curve.darkGain);
		} else {
			unsigned int section = x <= curve.x[2] ? 0 : 3;
			unsigned int knee = section ? 2 : 1;
			float delta = x - curve.x[knee];
			float inner = curve.coefficient[section + 1] + mul(delta, curve.coefficient[section + 2]);
			float middle = curve.coefficient[section] + mul(delta, inner);
			y = curve.y[knee] + mul(delta, middle);
		}
		y = std::clamp(y, 0.0f, 1.0f);
		result[i] = std::clamp(y / x, 0.0f, curve.darkGain);
	}
	result[0] = result[1];
	for (float &value : result)
		value = mul(std::pow(value, curve.ltmPercentage), 1024);
	if (!finite(result))
		return false;
	*output = result;
	return true;
}
} /* namespace libcamera::ipa */
