/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/lens_shading.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <limits>
using namespace libcamera::ipa;

int main()
{
	LscMesh golden, unit, factors, base, calibrated;
	for (unsigned int c = 0; c < LscChannels; ++c) {
		golden[c].fill(128.0f); unit[c].fill(64.0f);
		base[c].fill(1.0f);
	}
	assert(lscCalibrationFactors(golden, unit, &factors));
	assert(factors[LscR][0] == 2.0f);
	base[LscGr][23] = 1.25f; base[LscGb][23] = 2.75f;
	assert(lscApplyCalibration(base, factors, &calibrated));
	assert(calibrated[LscR][23] == 2.0f);
	assert(calibrated[LscGr][23] == 4.0f && calibrated[LscGb][23] == 4.0f);
	LscMesh saved = factors;
	unit[LscB][220] = 0.0f;
	assert(!lscCalibrationFactors(golden, unit, &factors) && factors == saved);
	unit[LscB][220] = std::numeric_limits<float>::quiet_NaN();
	assert(!lscCalibrationFactors(golden, unit, &factors) && factors == saved);
	for (unsigned int c = 0; c < LscChannels; ++c)
		base[c].fill(static_cast<float>(c + 2));
	LscPackedMesh packed;
	assert(lscPackTitan17x(base, &packed));
	assert(packed.grr[42] == (2048u | 3072u << 13));
	assert(packed.gbb[42] == (5120u | 4096u << 13));
	base[LscR][0] = 0.5f; base[LscGr][0] = 50.0f;
	assert(lscPackTitan17x(base, &packed));
	assert(packed.grr[0] == (1024u | 8191u << 13));
	auto previous = packed.grr;
	base[LscR][0] = std::numeric_limits<float>::infinity();
	assert(!lscPackTitan17x(base, &packed) && packed.grr == previous);
	std::puts("LSC_TEST golden/unit, green averaging, channel packing, Q10 limits and invalid-node rejection passed");
}
