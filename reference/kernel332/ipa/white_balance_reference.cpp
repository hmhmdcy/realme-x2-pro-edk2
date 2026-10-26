/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "white_balance_reference.h"
#include <cerrno>
#include <cmath>

namespace libcamera::ipa::camss {
namespace {
template<std::size_t N>
int readRow(const ValueNode &node, std::array<float, N> *values)
{
	if (!node.isList() || node.size() != N)
		return -EINVAL;
	for (unsigned int i = 0; i < N; ++i) {
		auto value = node[i].get<float>();
		if (!value || !std::isfinite(*value) || *value <= 0)
			return -EINVAL;
		(*values)[i] = *value;
	}
	return 0;
}
} /* namespace */

int WhiteBalanceReference::gains(int32_t kelvin, double *red, double *blue) const
{
	if (!red || !blue || kelvin < 1500 || kelvin > 12000)
		return -ERANGE;
	AwbRatio ratio;
	if (!awbRatiosForColourTemperature(ratios_, kelvin, &ratio))
		return -EINVAL;
	*red = 1.0 / ratio[0];
	*blue = 1.0 / ratio[1];
	return 0;
}

std::optional<int32_t> WhiteBalanceReference::temperature(double red, double blue) const
{
	if (!inverse_ || !std::isfinite(red) || !std::isfinite(blue) || red <= 0 || blue <= 0)
		return std::nullopt;
	AwbColourTemperatureEstimate estimate;
	if (!inverse_->estimate({ float(1.0 / red), float(1.0 / blue) }, &estimate))
		return std::nullopt;
	return int32_t(std::lround(estimate.kelvin));
}

int WhiteBalanceReference::configure(const ValueNode &tuning,
				   std::optional<WhiteBalanceReference> *reference)
{
	if (!reference)
		return -EINVAL;
	reference->reset();
	if (tuning.isEmpty())
		return 0;
	if (!tuning.isDictionary())
		return -EINVAL;
	if (!tuning["enabled"].isEmpty()) {
		auto enabled = tuning["enabled"].get<bool>();
		if (!enabled)
			return -EINVAL;
		if (!*enabled)
			return 0;
	}
	AwbIlluminantGains gains;
	const auto &mwb = tuning["mwb"];
	if (!mwb.isList() || mwb.size() != gains.size())
		return -EINVAL;
	for (unsigned int i = 0; i < gains.size(); ++i)
		if (readRow(mwb[i], &gains[i]))
			return -EINVAL;
	AwbIlluminantRatios factors;
	for (auto &factor : factors)
		factor = { 1, 1 };
	const auto &calibration = tuning["calibration"];
	if (!calibration.isEmpty()) {
		AwbCalibrationData data{};
		const auto &temperatures = calibration["cct"];
		const auto &golden = calibration["golden"];
		const auto &unit = calibration["unit"];
		if (!calibration.isDictionary() || !temperatures.isList() ||
		    !temperatures.size() || temperatures.size() > data.colourTemperatures.size() ||
		    !golden.isList() || !unit.isList() ||
		    golden.size() != temperatures.size() || unit.size() != temperatures.size())
			return -EINVAL;
		data.count = temperatures.size();
		for (unsigned int i = 0; i < data.count; ++i) {
			auto kelvin = temperatures[i].get<float>();
			if (!kelvin || !std::isfinite(*kelvin) || *kelvin <= 0 ||
			    readRow(golden[i], &data.golden[i]) || readRow(unit[i], &data.unit[i]))
				return -EINVAL;
			data.colourTemperatures[i] = *kelvin;
		}
		if (!awbCalibrationFactors(data, &factors))
			return -EINVAL;
	}
	WhiteBalanceReference result;
	if (!awbCalibratedMwbRatios(gains, factors, &result.ratios_))
		return -EINVAL;
	for (const auto &ratio : result.ratios_)
		if (1.0 / ratio[0] > 8 || 1.0 / ratio[1] > 8)
			return -ERANGE;
	const auto &referencePoints = tuning["reference_points"];
	if (!referencePoints.isEmpty()) {
		AwbIlluminantRatios points, calibrated;
		if (!referencePoints.isList() || referencePoints.size() != points.size())
			return -EINVAL;
		for (unsigned int i = 0; i < points.size(); ++i)
			if (readRow(referencePoints[i], &points[i]))
				return -EINVAL;
		AwbColourTemperatureModel inverse;
		if (!awbCalibratedReferenceRatios(points, factors, &calibrated) || !inverse.configure(calibrated))
			return -EINVAL;
		result.inverse_ = inverse;
	}
	*reference = result;
	return 0;
}

} /* namespace libcamera::ipa::camss */
