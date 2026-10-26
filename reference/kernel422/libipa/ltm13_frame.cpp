/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ltm13_frame.h"
#include "../../kernel409/libipa/ltm_adrc.h"
#include <algorithm>
#include <cmath>

namespace libcamera::ipa {
namespace {
int16_t signedField(uint32_t value, unsigned bits)
{
	value &= (1U << bits) - 1;
	int32_t result = value & (1U << (bits - 1)) ? int32_t(value) - (1 << bits) : int32_t(value);
	return int16_t(result);
}
template<size_t N> void unpackUnsigned(const std::array<uint32_t, N> &in,
				      std::array<Ltm13UnsignedSegment, N> &out, unsigned bits)
{
	for (size_t i = 0; i < N; ++i)
		out[i] = { uint16_t(in[i] & ((1U << bits) - 1)), signedField(in[i] >> bits, bits) };
}
template<size_t N> void unpackSigned(const std::array<uint32_t, N> &in,
				    std::array<Ltm13SignedSegment, N> &out)
{
	for (size_t i = 0; i < N; ++i)
		out[i] = { signedField(in[i], 12), signedField(in[i] >> 12, 12) };
}
} /* namespace */
bool prepareLtm13Frame(const Ltm13FrameInput &in, const Ltm13FaceSmoothingState &history,
		      const Tmc11GenerationResult *adrc, const std::array<float, 1024> *axis,
		      Ltm13Program *output, Ltm13FaceSmoothingState *nextHistory)
{
	if (!output || !nextHistory || nextHistory == &history || (adrc && !axis)) return false;
	Ltm13StaticResult constants;
	Ltm13InverseGammaTable inverse;
	Ltm13Curves curves;
	Ltm13FaceSmoothingState next;
	Ltm13SignedTables signedTables;
	if (!prepareLtm13Static(in.constants, &constants) ||
	    !encodeLtm13InverseGamma(in.ifeGreen, &inverse) ||
	    !calculateLtm13FaceCurves(in.curves, in.smoothing, history, &curves, &next) ||
	    !encodeLtm13SignedTables(curves, &signedTables)) return false;
	Ltm13AdrcBlend blend{};
	blend.curve = in.reserveCurve;
	for (unsigned i = 0; i < 65; ++i) {
		float value = std::round(curves.scale[i]);
		if (!std::isfinite(value) || value < -32768 || value > 32767) return false;
		blend.scale[i] = int16_t(value);
	}
	if (adrc) {
		Ltm13AdrcSamples samples;
		for (unsigned i = 0; i < 64; ++i)
			samples.equivalent12[i] = float((inverse.segments[i] & 16383) / 4);
		samples.equivalent12[64] = 4095;
		samples.forwardGamma10 = in.forwardGamma;
		std::array<float, 65> normalized;
		Tmc11PchipResult sampled;
		Ltm13AdrcCurves converted;
		if (!normalizeTmc11LtmInput(samples.equivalent12, &normalized) ||
		    !sampleTmc11Pchip(adrc->pchip, normalized, &sampled) ||
		    !applyTmc11LtmContrast(adrc->ltm, normalized, sampled.gain, *axis,
				  adrc->contrastCurve, &samples.sampledGainQ10) ||
		    !calculateLtm13Adrc(samples, &converted) ||
		    !blendLtm13Adrc(converted, sampled.ltmMix, in.reserveCurve, blend.scale, &blend)) return false;
	}
	Ltm13AdrcTables tables;
	if (!encodeLtm13AdrcTables(blend, &tables)) return false;
	Ltm13Program result{};
	result.reverseGamma = constants.reverseGamma;
	result.localAdaptation = constants.localAdaptation;
	result.maskFilter = constants.maskFilter;
	result.rgb2y = constants.rgb2y;
	result.lceThreshold = constants.lceThreshold;
	result.yRatioMaximum = constants.yRatioMaximum;
	result.maskKernel = constants.maskKernel;
	result.maskShift = constants.maskShift; result.maskScale = constants.maskScale;
	result.dataCollection = constants.dataCollection; result.imageProcessing = constants.imageProcessing;
	for (unsigned i = 0; i < 12; ++i) result.weights[i] = constants.weights[i];
	unpackUnsigned(constants.la, result.la[0], 12); result.la[1] = result.la[0];
	unpackUnsigned(constants.mask, result.mask, 12);
	unpackUnsigned(tables.curve, result.curve, 12);
	unpackSigned(tables.scale, result.scale);
	unpackSigned(signedTables.lcePositive, result.lce[0]);
	unpackSigned(signedTables.lceNegative, result.lce[1]);
	unpackUnsigned(inverse.segments, result.reverse[0], 14);
	for (unsigned i = 1; i < 5; ++i) result.reverse[i] = result.reverse[0];
	*output = result; *nextHistory = next; return true;
}
} /* namespace libcamera::ipa */
