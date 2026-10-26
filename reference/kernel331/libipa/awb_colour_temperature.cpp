/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "awb_colour_temperature.h"
#include <algorithm>
#include <cmath>

namespace libcamera::ipa {
namespace {
constexpr std::array<unsigned int, 8> first{ 0, 1, 2, 3, 3, 5, 7, 8 };
constexpr std::array<unsigned int, 8> second{ 1, 2, 3, 5, 5, 7, 8, 9 };
constexpr std::array<unsigned int, 8> boundaryPoint{ 0, 1, 2, 3, 5, 7, 8, 9 };
constexpr std::array<unsigned int, 8> boundarySegment{ 0, 1, 2, 2, 3, 5, 6, 7 };
constexpr std::array<unsigned int, 10> kelvin{ 12000, 7500, 6500, 5000, 4100, 4000, 3800, 2850, 2300, 1500 };

float distanceSquared(const AwbRatio &a, const AwbRatio &b)
{
	float x = a[0] - b[0], y = a[1] - b[1];
	return x * x + y * y;
}
} /* namespace */

bool awbCalibratedReferenceRatios(const AwbIlluminantRatios &points,
				const AwbIlluminantRatios &factors,
				AwbIlluminantRatios *result)
{
	if (!result) return false;
	AwbIlluminantRatios calibrated;
	for (unsigned int i = 0; i < points.size(); ++i) {
		for (unsigned int c = 0; c < 2; ++c) {
			if (!std::isfinite(points[i][c]) || points[i][c] <= 0 ||
			    !std::isfinite(factors[i][c]) || factors[i][c] <= 0)
				return false;
			calibrated[i][c] = points[i][c] * factors[i][c];
			if (!std::isfinite(calibrated[i][c]) || calibrated[i][c] <= 0)
				return false;
		}
	}
	*result = calibrated;
	return true;
}

bool AwbColourTemperatureModel::configure(const AwbIlluminantRatios &points)
{
	configured_ = false;
	for (const auto &point : points)
		for (float value : point)
			if (!std::isfinite(value) || value <= 0)
				return false;
	points_ = points;
	for (unsigned int i = 0; i < first.size(); ++i) {
		const auto &a = points[first[i]], &b = points[second[i]];
		float dx = b[0] - a[0], dy = b[1] - a[1];
		/* The OEM slope representation requires nonzero horizontal/vertical
		 * deltas. Reject a degenerate configuration rather than creating NaNs. */
		if (dx == 0 || dy == 0)
			return false;
		float slope = dy / dx;
		locus_[i] = { slope, -1, b[1] - b[0] * slope };
		lengthsSquared_[i] = distanceSquared(a, b);
		if (!std::isfinite(slope) || !std::isfinite(locus_[i][2]) ||
		    !std::isfinite(lengthsSquared_[i]) || lengthsSquared_[i] <= 0)
			return false;
	}
	for (unsigned int i = 0; i < boundaries_.size(); ++i) {
		float slope = -1.0f / locus_[boundarySegment[i]][0];
		const auto &point = points[boundaryPoint[i]];
		boundaries_[i] = { slope, -1, point[1] - point[0] * slope };
		if (!std::isfinite(slope) || !std::isfinite(boundaries_[i][2]))
			return false;
	}
	configured_ = true;
	return true;
}

bool AwbColourTemperatureModel::estimate(const AwbRatio &ratio,
				       AwbColourTemperatureEstimate *result) const
{
	if (!configured_ || !result || !std::isfinite(ratio[0]) || !std::isfinite(ratio[1]) ||
	    ratio[0] <= 0 || ratio[1] <= 0)
		return false;
	int index = 4, direction = 0;
	while (index >= 0 && index < 8) {
		const auto &line = boundaries_[index];
		float value = line[2] + (ratio[0] * line[0] + ratio[1] * line[1]);
		if (value < 0) {
			if (direction == 2) break;
			direction = 1; --index;
		} else if (value > 0) {
			if (direction == 1) break;
			direction = 2; ++index;
		} else break;
	}
	if (index == -1 || index == 8) {
		unsigned int point = index == -1 ? 0 : 9;
		*result = { float(kelvin[point]), std::sqrt(distanceSquared(ratio, points_[point])),
			    index == -1 ? 1u : 8u };
		return std::isfinite(result->signedDistance);
	}
	unsigned int segment = index == 4 ? 3 : index;
	const auto &line = locus_[segment];
	float side = line[0] * (line[2] + (line[0] * ratio[0] + line[1] * ratio[1]));
	float da = distanceSquared(ratio, points_[first[segment]]);
	float db = distanceSquared(ratio, points_[second[segment]]);
	float length = lengthsSquared_[segment];
	float t = side != 0 ? ((da - db + length) * .5f) / length : da / length;
	float correction = length * ((t * (t + t) - (t + t)) + 1.0f);
	float distance = std::sqrt((da + db - correction) * .5f);
	if (t < 0) { distance = std::sqrt(da); t = 0; }
	if (!std::isfinite(distance)) distance = 0;
	distance *= side > 0 ? 1.0f : -1.0f;
	float weight = std::max(0.0f, std::min(t, 1.0f));
	unsigned int a = first[segment], b = second[segment];
	result->kelvin = weight * float(kelvin[b]) + (1.0f - weight) * float(kelvin[a]);
	result->signedDistance = distance;
	result->illuminant = t > .5f ? b : a;
	return std::isfinite(result->kelvin);
}

} /* namespace libcamera::ipa */
