/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "aec_antibanding.h"

#include <cmath>
#include <limits>

namespace libcamera::ipa {

bool aecApplyAntibanding(const AecAntibandingConfiguration &configuration,
			const AecExposureAllocation &input,
			AecExposureAllocation *output)
{
	if (!output || !std::isfinite(input.gain) || input.gain <= 0 ||
	    !input.exposureTimeNs)
		return false;
	if (!configuration.enabled) {
		*output = input;
		return true;
	}
	if (!configuration.periodNs ||
	    !std::isfinite(configuration.minimumPeriodFraction) ||
	    configuration.minimumPeriodFraction < 0 ||
	    !std::isfinite(configuration.minimumGain) ||
	    configuration.minimumGain <= 0 ||
	    configuration.minimumExposureTimeNs > configuration.maximumExposureTimeNs ||
	    configuration.fpsMethod > AecAntibandingFpsMethod::MaximizeExposureTime)
		return false;

	const uint64_t period = configuration.periodNs;
	const float time = input.exposureTimeNs;
	const float threshold = configuration.minimumPeriodFraction * float(period);
	if (configuration.maximumExposureTimeNs < period || threshold >= time) {
		*output = input;
		return true;
	}

	uint64_t maximum = configuration.maximumExposureTimeNs;
	if (configuration.fpsMethod != AecAntibandingFpsMethod::StrictlyEnforceFps) {
		if (configuration.minimumPreviewVerticalBlankingNs >
		    std::numeric_limits<uint64_t>::max() - maximum)
			return false;
		maximum += configuration.minimumPreviewVerticalBlankingNs;
	}
	const uint64_t periods = input.exposureTimeNs / period;
	/* The original candidate calculation uses signed 32-bit period counts.
	 * Reject values outside that useful domain instead of reproducing signed
	 * overflow or wrapped multiplication for impossible sensor exposures.
	 */
	if (periods >= uint64_t(std::numeric_limits<int32_t>::max()) ||
	    period > std::numeric_limits<uint64_t>::max() / (periods + 1))
		return false;

	const uint64_t upperTime = (periods + 1) * period;
	const uint64_t lowerTime = periods * period;
	/* Division then multiplication matches the ordinary compensation path. */
	const float upperGain = input.gain * (time / float(upperTime));
	const float lowerGain = periods ? input.gain * (time / float(lowerTime)) : input.gain;
	const bool upperValid = upperGain >= configuration.minimumGain &&
		upperTime >= configuration.minimumExposureTimeNs && upperTime <= maximum;
	const bool lowerValid = periods && lowerGain >= configuration.minimumGain &&
		lowerTime >= configuration.minimumExposureTimeNs && lowerTime <= maximum;

	AecExposureAllocation result = input;
	if (upperValid || lowerValid) {
		/* Equal distances select the upper period. Neither the shorter time
		 * nor the smaller gain is an unconditional preference.
		 */
		const bool lower = lowerValid && (!upperValid ||
			input.exposureTimeNs - lowerTime < upperTime - input.exposureTimeNs);
		result.exposureTimeNs = lower ? lowerTime : upperTime;
		result.gain = lower ? lowerGain : upperGain;
		if (configuration.fpsMethod == AecAntibandingFpsMethod::MaximizeExposureTime &&
		    result.exposureTimeNs > configuration.maximumExposureTimeNs) {
			result.exposureTimeNs = configuration.maximumExposureTimeNs;
			/* This separate path multiplies before division in the OEM. */
			const float sensitivity = input.gain * time;
			result.gain = sensitivity / float(result.exposureTimeNs);
		}
	}
	if (!std::isfinite(result.gain) || result.gain <= 0)
		return false;
	*output = result;
	return true;
}

} /* namespace libcamera::ipa */
