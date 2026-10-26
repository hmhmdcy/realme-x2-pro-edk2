/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/ltm_face_smoothing.h"
#include <cassert>
#include <cstring>
#include <limits>
using namespace libcamera::ipa;
int main()
{
	Ltm13CurveInput input{};
	input.scale.fill(-100);
	input.lcePositive.fill(100);
	input.lceNegative.fill(-100);
	input.strength = input.lceStrength = input.brightSuppress = 1;
	input.attenuationStart = 2;
	input.attenuationEnd = 10;
	input.exposureIndex = 6;
	input.manualCurve = 1;
	Ltm13FaceSmoothingState state{};
	state.previous.scale.fill(100);
	state.previous.lcePositive.fill(50);
	state.previous.lceNegative.fill(-50);
	auto oldState = state;
	Ltm13FaceSmoothingControl control{1, 0, 0};
	Ltm13Curves out;
	Ltm13FaceSmoothingState next;
	assert(calculateLtm13FaceCurves(input, control, state, &out, &next));
	assert(next.positiveSignal == 1 && next.updatesRemaining == 89);
	for (float value : next.previous.scale)
		assert(value == 90);
	for (float value : out.scale)
		assert(value == 45);
	for (float value : next.previous.lcePositive)
		assert(value == 52.5f);
	for (float value : out.lcePositive)
		assert(value == 26.25f);
	for (float value : next.previous.lceNegative)
		assert(value == -52.5f);
	for (float value : out.lceNegative)
		assert(value == -26.25f);
	assert(!std::memcmp(&state, &oldState, sizeof state));
	for (unsigned int skip = 0; skip < 2; ++skip) {
		auto bypass = control;
		bypass.parentIsBps = skip == 0;
		bypass.aecField140 = skip == 1;
		assert(calculateLtm13FaceCurves(input, bypass, state, &out, &next));
		assert(!std::memcmp(&next, &state, sizeof state));
		for (float value : out.scale)
			assert(value == -50);
	}
	Ltm13Curves prepared;
	assert(prepareLtm13Curves(input, &prepared));
	std::memset(&out, 0xa5, sizeof out);
	std::memset(&next, 0xa5, sizeof next);
	auto untouchedOut = out;
	auto untouchedNext = next;
	assert(!applyLtm13FaceSmoothing(prepared, control, state, nullptr, &next));
	assert(!applyLtm13FaceSmoothing(prepared, control, state, &out, nullptr));
	assert(!applyLtm13FaceSmoothing(prepared, control, state, &next.previous, &next));
	assert(!applyLtm13FaceSmoothing(prepared, control, state, &out, &state));
	assert(!applyLtm13FaceSmoothing(prepared, control, state, &state.previous, &next));
	assert(!calculateLtm13FaceCurves(input, control, state, nullptr, &next));
	assert(!calculateLtm13FaceCurves(input, control, state, &out, nullptr));
	assert(!calculateLtm13FaceCurves(input, control, state, &next.previous, &next));
	assert(!calculateLtm13FaceCurves(input, control, state, &out, &state));
	assert(!calculateLtm13FaceCurves(input, control, state, &state.previous, &next));
	input.exposureIndex = std::numeric_limits<float>::quiet_NaN();
	assert(!prepareLtm13Curves(input, &out));
	assert(!attenuateLtm13Curves(input, prepared, &out));
	assert(!calculateLtm13FaceCurves(input, control, state, &out, &next));
	assert(!std::memcmp(&out, &untouchedOut, sizeof out));
	assert(!std::memcmp(&next, &untouchedNext, sizeof next));
	assert(!std::memcmp(&state, &oldState, sizeof state));
}
