/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <optional>

#include "../libipa/awb_grey.h"
#include "statistics.h"

namespace libcamera::ipa::camss {

/* Adapt pre-WB hardware grids to libipa's existing grey-world algorithm. */
class HardwareAwb {
public:
	int initialise(const ValueNode &tuning);
	struct Result {
		unsigned int regions = 0;
		RGB<double> means{{0, 0, 0}};
		bool valid = false, locked = false;
		double red = 1, blue = 1;
	};
	Result calculate(const GridStatistics &grid, double red, double blue);
	void reset() { stable_ = 0; }
private:
	AwbGrey algorithm_;
	std::array<double, 4> black_{};
	unsigned int minRegions_ = 16, stable_ = 0;
	double minSignal_ = 32, minGain_ = .25, maxGain_ = 4;
	double speed_ = .3, tolerance_ = .015;
};
}
