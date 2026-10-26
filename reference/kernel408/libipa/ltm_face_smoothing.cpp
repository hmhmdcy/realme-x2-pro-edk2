/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ltm_face_smoothing.h"
#include <algorithm>
#include <cmath>

namespace libcamera::ipa {
namespace {
bool valid(const Ltm13Curves &curves)
{
	auto table = [](const auto &values) {
		return std::all_of(values.begin(), values.end(), [](float value) {
			return std::isfinite(value) && std::abs(value) <= 1048576.0f;
		});
	};
	return table(curves.scale) && table(curves.lcePositive) && table(curves.lceNegative);
}

template<std::size_t N>
void smooth(std::array<float, N> &values, const std::array<float, N> &previous)
{
	for (std::size_t i = 0; i < N; ++i) {
		/* Separate rounding matches the target's FSUB, FMUL, FADD sequence. */
		volatile float step = (values[i] - previous[i]) * 0.05f;
		values[i] = previous[i] + step;
	}
}
} /* namespace */

bool applyLtm13FaceSmoothing(const Ltm13Curves &curves,
			     const Ltm13FaceSmoothingControl &control,
			     const Ltm13FaceSmoothingState &state,
			     Ltm13Curves *output, Ltm13FaceSmoothingState *nextState)
{
	if (!output || !nextState || nextState == &state ||
	    output == &state.previous || output == &nextState->previous ||
	    !std::isfinite(control.transitionSignal) || std::abs(control.transitionSignal) > 1048576.0f ||
	    control.parentIsBps > 1 || state.positiveSignal > 1 || state.updatesRemaining > 90 ||
	    !valid(curves) || !valid(state.previous))
		return false;
	Ltm13Curves result = curves;
	Ltm13FaceSmoothingState next = state;
	if (!control.parentIsBps && control.aecField140 != 1) {
		uint32_t positive = control.transitionSignal > 0;
		if (positive != next.positiveSignal) {
			next.positiveSignal = positive;
			next.updatesRemaining = 90;
		}
		if (next.updatesRemaining) {
			smooth(result.scale, state.previous.scale);
			smooth(result.lcePositive, state.previous.lcePositive);
			smooth(result.lceNegative, state.previous.lceNegative);
			--next.updatesRemaining;
		}
		next.previous = result;
	}
	*output = result;
	*nextState = next;
	return true;
}

bool calculateLtm13FaceCurves(const Ltm13CurveInput &input,
			     const Ltm13FaceSmoothingControl &control,
			     const Ltm13FaceSmoothingState &state,
			     Ltm13Curves *output, Ltm13FaceSmoothingState *nextState)
{
	if (!output || !nextState || nextState == &state ||
	    output == &state.previous || output == &nextState->previous)
		return false;
	Ltm13Curves prepared, smoothed, result;
	Ltm13FaceSmoothingState next;
	if (!prepareLtm13Curves(input, &prepared) ||
	    !applyLtm13FaceSmoothing(prepared, control, state, &smoothed, &next) ||
	    !attenuateLtm13Curves(input, smoothed, &result))
		return false;
	*output = result;
	*nextState = next;
	return true;
}
} /* namespace libcamera::ipa */
