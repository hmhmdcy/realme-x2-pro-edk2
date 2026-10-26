/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include "ltm13_static.h"
#include "../../kernel352/libipa/ltm_inverse_gamma.h"
#include "../../kernel408/libipa/ltm_face_smoothing.h"
#include "../../kernel413/libipa/tmc11_generation.h"

namespace libcamera::ipa {
struct Ltm13UnsignedSegment { uint16_t base; int16_t delta; };
struct Ltm13SignedSegment { int16_t base, delta; };
/* Matches the existing typed kernel LTM payload; not hardware command words. */
struct Ltm13Program {
	uint32_t reverseGamma, localAdaptation, maskFilter, binInitialCount;
	std::array<uint32_t, 4> rgb2y;
	uint32_t lceThreshold, yRatioMaximum;
	std::array<uint32_t, 6> maskKernel;
	uint32_t maskShift, maskScale, horizontalTermination, verticalTermination;
	uint32_t dataCollection, imageProcessing;
	std::array<uint16_t, 12> weights;
	std::array<std::array<Ltm13UnsignedSegment, 64>, 2> la;
	std::array<Ltm13UnsignedSegment, 64> curve;
	std::array<Ltm13SignedSegment, 64> scale;
	std::array<Ltm13UnsignedSegment, 64> mask;
	std::array<std::array<Ltm13SignedSegment, 16>, 2> lce;
	std::array<std::array<Ltm13UnsignedSegment, 64>, 5> reverse;
};
static_assert(sizeof(Ltm13Program) == 2800);
struct Ltm13FrameInput {
	Ltm13StaticInput constants;
	Ltm13CurveInput curves;
	Ltm13FaceSmoothingControl smoothing;
	std::array<int32_t, 65> reserveCurve;
	IfeGammaBaseNodes ifeGreen;
	/* The actual published IFE forward nodes, including its endpoint. */
	std::array<float, 65> forwardGamma;
};
/* The caller supplies the selected, freshly generated TMC11 result and its
 * matching axis. No fabricated HDR/DRC/face inputs or root selection here.
 * A null ADRC result follows the explicit non-ADRC LTM path. The proposed
 * history is pre-attenuation and pre-ADRC, and is committed by the caller
 * only on successful completion of the matching image request. */
bool prepareLtm13Frame(const Ltm13FrameInput &input,
		      const Ltm13FaceSmoothingState &history,
		      const Tmc11GenerationResult *adrc,
		      const std::array<float, 1024> *axis,
		      Ltm13Program *output, Ltm13FaceSmoothingState *nextHistory);
} /* namespace libcamera::ipa */
