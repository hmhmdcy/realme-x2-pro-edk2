/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include "../../kernel412/libipa/tmc11_ltm.h"
#include <cstdint>

namespace libcamera::ipa {
/* Numerical TMC11 model2 -> IFE GTM primitive. Axes and histogram-derived
 * contrast data stay caller-owned. This does not select a factory mode,
 * apply IFE parameters, acknowledge a version, or advance frame history. */
bool calculateTmc11Gtm(const Tmc11PchipCurve &curve,
		      const Tmc11LtmContrast &controls,
		      const std::array<float, 65> &normalized,
		      const std::array<uint32_t, 65> &domain,
		      const std::array<float, 1024> &contrastAxis,
		      const std::array<float, 1024> &contrastCurve,
		      bool swapWords,
		      std::array<uint64_t, 64> *output);
} /* namespace libcamera::ipa */
