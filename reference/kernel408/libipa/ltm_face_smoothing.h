/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include "../../kernel407/libipa/ltm_curves.h"

namespace libcamera::ipa {
struct Ltm13FaceSmoothingControl {
	/* Source tag identity is not inferred from the newer reference headers.
	 * These are the observed AEC field at byte124 and bypass field at140. */
	float transitionSignal;
	uint32_t parentIsBps;
	uint32_t aecField140;
};

/* The OEM stores these globally. The portable API takes explicit state so
 * each future pipeline can own and commit its own history. Zero state
 * matches BSS initialization; skipped requests leave the state untouched. */
struct Ltm13FaceSmoothingState {
	uint32_t positiveSignal;
	uint32_t updatesRemaining;
	Ltm13Curves previous;
};

/* Produce a proposed next state. The caller controls committing it; input
 * state is never modified. Output and nextState must be separate from each
 * other and from the input state.
 * Failure preserves both outputs. No camera selection or policy is implied. */
bool applyLtm13FaceSmoothing(const Ltm13Curves &curves,
			     const Ltm13FaceSmoothingControl &control,
			     const Ltm13FaceSmoothingState &state,
			     Ltm13Curves *output, Ltm13FaceSmoothingState *nextState);

/* The target order is strength -> smoothing -> save history -> attenuation.
 * History must not contain exposure-attenuated curves. ADRC is separate. */
bool calculateLtm13FaceCurves(const Ltm13CurveInput &input,
			     const Ltm13FaceSmoothingControl &control,
			     const Ltm13FaceSmoothingState &state,
			     Ltm13Curves *output, Ltm13FaceSmoothingState *nextState);
} /* namespace libcamera::ipa */
