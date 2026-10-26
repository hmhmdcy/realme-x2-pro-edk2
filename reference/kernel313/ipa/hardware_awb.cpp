/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "hardware_awb.h"

#include <algorithm>
#include <cmath>

namespace libcamera::ipa::camss {

int HardwareAwb::initialise(const ValueNode &tuning)
{
	if (tuning["algorithm"].get<std::string>().value_or("") != "grey")
		return -EINVAL;
	const auto &black = tuning["statistics_black"];
	if (!black.isList() || black.size() != 4)
		return -EINVAL;
	for (unsigned int c = 0; c < 4; ++c) {
		auto value = black[c].get<double>();
		if (!value || !std::isfinite(*value) || *value < 0 || *value > 16383)
			return -EINVAL;
		black_[c] = *value;
	}
	minRegions_ = tuning["minimum_regions"].get<unsigned int>().value_or(16);
	minSignal_ = tuning["minimum_signal"].get<double>().value_or(32);
	if (!minRegions_ || minRegions_ > 14400 ||
	    !std::isfinite(minSignal_) || minSignal_ < 1 || minSignal_ > 8192)
		return -EINVAL;
	/* Grey-world needs no fabricated colour-temperature calibration curve. */
	return 0;
}

namespace {
struct Means final : AwbStats {
	RGB<double> value;
	explicit Means(const RGB<double> &rgb) : value(rgb) {}
	RGB<double> rgbMeans() const override { return value; }
	double computeColourError(const RGB<double> &gains) const override
	{
		const double green = value.g() * gains.g();
		return std::pow(value.r() * gains.r() - green, 2) +
		       std::pow(value.b() * gains.b() - green, 2);
	}
};
}

HardwareAwb::Result HardwareAwb::calculate(const GridStatistics &grid, double red, double blue)
{
	Result result;
	std::array<double, 4> sum{};
	std::array<uint64_t, 4> count{};
	const unsigned int maximum = unsigned(grid.width) * grid.height / 4;
	for (const auto &r : grid.regions) {
		std::array<uint32_t, 4> sums{r.r_sum,r.b_sum,r.gr_sum,r.gb_sum};
		std::array<uint16_t, 4> counts{r.r_count,r.b_count,r.gr_count,r.gb_count};
		bool valid = maximum != 0;
		std::array<double, 4> means{};
		for (unsigned int c = 0; c < 4; ++c) {
			if (!counts[c] || uint32_t(counts[c]) * 10 < maximum * 9) { valid = false; break; }
			means[c] = double(sums[c]) / counts[c] - black_[c];
			if (means[c] < minSignal_ ||
			    double(sums[c]) / counts[c] > grid.highThreshold * .9)
				valid = false;
		}
		if (!valid || *std::max_element(means.begin(), means.end()) >
			      8 * *std::min_element(means.begin(), means.end()))
			continue;
		for (unsigned int c = 0; c < 4; ++c) {
			sum[c] += double(sums[c]) - black_[c] * counts[c];
			count[c] += counts[c];
		}
		++result.regions;
	}
	if (result.regions < minRegions_) { stable_ = 0; return result; }
	result.means = {{sum[0]/count[0], (sum[2]+sum[3])/(count[2]+count[3]), sum[1]/count[1]}};
	auto calculated = algorithm_.calculateAwb(Means(result.means), 0);
	const double targetRed = std::clamp(calculated.gains.r(), minGain_, maxGain_);
	const double targetBlue = std::clamp(calculated.gains.b(), minGain_, maxGain_);
	if (!std::isfinite(targetRed) || !std::isfinite(targetBlue)) { stable_ = 0; return result; }
	result.valid = true;
	if (std::abs(targetRed - red) < tolerance_ && std::abs(targetBlue - blue) < tolerance_) {
		result.red = red; result.blue = blue;
		result.locked = ++stable_ >= 3;
	} else {
		stable_ = 0;
		result.red = std::clamp(red + speed_ * (targetRed - red), minGain_, maxGain_);
		result.blue = std::clamp(blue + speed_ * (targetBlue - blue), minGain_, maxGain_);
	}
	return result;
}
}
