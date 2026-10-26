/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "exposure_program.h"

#include <algorithm>
#include <cerrno>
#include <charconv>
#include <cmath>
#include <string>

#include "../libipa/aec_lux.h"

namespace libcamera::ipa::camss {
namespace {
bool integer(const ValueNode &value, uint64_t *result)
{
	auto text = value.get<std::string>();
	if (!text)
		return false;
	auto [end, error] = std::from_chars(text->data(), text->data() + text->size(), *result);
	return error == std::errc() && end == text->data() + text->size();
}
}

int ExposureProgram::configure(const ValueNode &tuning, uint64_t minimumNs,
			       uint64_t maximumNs, uint64_t frameNs, float minimumGain,
			       std::optional<ExposureProgram> *program)
{
	if (!program)
		return -EINVAL;
	program->reset();
	if (tuning.isEmpty())
		return 0;
	if (!tuning.isDictionary())
		return -EINVAL;
	auto enabled = tuning["enabled"].get<bool>();
	if (!enabled)
		return -EINVAL;
	if (!*enabled)
		return 0;
	if (!minimumNs || maximumNs < minimumNs || frameNs < maximumNs ||
	    !std::isfinite(minimumGain) || minimumGain <= 0)
		return -ERANGE;

	ExposureProgram result;
	const auto &table = tuning["knees"];
	if (!table.isList())
		return -EINVAL;
	std::vector<AecExposureKnee> knees;
	for (const auto &point : table.asList()) {
		AecExposureKnee knee{};
		auto gain = point["gain"].get<float>();
		auto index = point["index"].get<float>();
		auto priority = point["priority"].get<unsigned int>();
		if (!gain || !index || !priority || *priority > 2 ||
		    !integer(point["exposure_time_ns"], &knee.exposureTimeNs))
			return -EINVAL;
		knee.gain = *gain; knee.index = *index;
		knee.priority = static_cast<AecExposurePriority>(*priority);
		knees.push_back(knee);
	}
	if (!result.source_.configure(knees))
		return -ERANGE;
	result.anchor_ = knees.front();
	const auto &ev = tuning["ev_adjustment"];
	auto adjust = ev["enabled"].get<bool>();
	auto cap = ev["cap_gain"].get<bool>();
	auto maximumGain = ev["maximum_gain"].get<float>();
	const auto &banding = tuning["antibanding"];
	auto threshold = banding["minimum_period_fraction"].get<float>();
	auto method = banding["fps_method"].get<unsigned int>();
	uint64_t blanking;
	if (!adjust || !cap || !maximumGain || !threshold || !method || *method > 2 ||
	    !std::isfinite(*maximumGain) || *maximumGain <= 0 ||
	    !std::isfinite(*threshold) || *threshold < 0 ||
	    !integer(banding["minimum_preview_vertical_blanking_ns"], &blanking))
		return -EINVAL;
	/* As in the original FPS setter, subtract preview blanking only when
	 * it fits. The configured sensor exposure range remains an absolute cap.
	 */
	uint64_t budget = frameNs - (blanking < frameNs ? blanking : 0);
	budget = std::clamp(budget, minimumNs, maximumNs);
	result.adjustEv_ = *adjust;
	result.adjustment_ = { budget, 0, *cap, *maximumGain, false };
	result.banding_ = { false, 0, *threshold, minimumGain, minimumNs,
			    budget, blanking, static_cast<AecAntibandingFpsMethod>(*method) };
	if (!result.adjust(0))
		return -ERANGE;
	*program = std::move(result);
	return 0;
}

bool ExposureProgram::adjust(float evStops)
{
	auto adjustment = adjustment_;
	adjustment.evStops = adjustEv_ ? evStops : 0;
	AecExposureProgram program;
	if (!source_.activeProgram(adjustment, &program))
		return false;
	AecExposureTable active;
	if (!active.configure(program.knees))
		return false;
	active_ = std::move(active);
	adjustment_ = adjustment;
	return true;
}

bool ExposureProgram::allocate(double exposureNsGain, uint64_t flickerPeriodNs,
			       AecExposureAllocation *allocation) const
{
	if (!allocation || !std::isfinite(exposureNsGain) || exposureNsGain <= 0)
		return false;
	/* The controller passes time*analogue-gain in nanoseconds. It has not
	 * applied the factory sensitivity correction, so this conversion uses
	 * unity correction rather than applying that factor a second time.
	 */
	float index;
	if (!aecSensitivityExposureIndex({ anchor_.gain, anchor_.exposureTimeNs, anchor_.index },
					1.f, float(exposureNsGain), &index))
		return false;
	AecExposureAllocation selected;
	if (!active_.allocate(index, &selected))
		return false;
	auto banding = banding_;
	banding.enabled = flickerPeriodNs != 0;
	banding.periodNs = flickerPeriodNs;
	return aecApplyAntibanding(banding, selected, allocation);
}

} /* namespace libcamera::ipa::camss */
