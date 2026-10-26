/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "lens_shading.h"
#include "tuning_interpolation.h"

#include <algorithm>
#include <cmath>

namespace libcamera::ipa {

static bool positive(float value)
{
	return std::isfinite(value) && value > 0.0f;
}

bool interpolateLscMesh(const LscMesh &first,const LscMesh &second,float weight,LscMesh *result)
{
 if(!result||!std::isfinite(weight)||weight<0||weight>1)return false;
 LscMesh output;
 for(unsigned c=0;c<LscChannels;c++)for(unsigned i=0;i<LscPoints;i++){
  float a=first[c][i],b=second[c][i];if(!positive(a)||!positive(b))return false;
  if(weight==0)output[c][i]=a;
  else if(weight==1)output[c][i]=b;
  else {
   if(a>=2147483648.0f||b>=2147483648.0f)return false;
   output[c][i]=interpolateTuningFloat(a,b,weight);
  }
  if(!positive(output[c][i]))return false;
 }
 *result=output;return true;
}

bool lscCalibrationFactors(const LscMesh &golden, const LscMesh &unit,
			   LscMesh *factors)
{
	if (!factors)
		return false;
	LscMesh result;
	for (unsigned int channel = 0; channel < LscChannels; ++channel) {
		for (unsigned int point = 0; point < LscPoints; ++point) {
			if (!positive(golden[channel][point]) || !positive(unit[channel][point]))
				return false;
			result[channel][point] = golden[channel][point] / unit[channel][point];
			if (!positive(result[channel][point]))
				return false;
		}
	}
	*factors = result;
	return true;
}

bool lscApplyCalibration(const LscMesh &base, const LscMesh &factors,
			 LscMesh *calibrated)
{
	if (!calibrated)
		return false;
	LscMesh result;
	for (unsigned int channel = 0; channel < LscChannels; ++channel) {
		for (unsigned int point = 0; point < LscPoints; ++point) {
			if (!positive(base[channel][point]) || !positive(factors[channel][point]))
				return false;
			result[channel][point] = base[channel][point] * factors[channel][point];
			if (!positive(result[channel][point]))
				return false;
		}
	}
	for (unsigned int point = 0; point < LscPoints; ++point) {
		/* Halving first avoids overflow when both valid inputs are large. */
		float green = result[LscGr][point] * 0.5f + result[LscGb][point] * 0.5f;
		result[LscGr][point] = result[LscGb][point] = green;
	}
	*calibrated = result;
	return true;
}

bool lscPackTitan17x(const LscMesh &mesh, LscPackedMesh *packed)
{
	if (!packed)
		return false;
	LscPackedMesh result;
	for (unsigned int point = 0; point < LscPoints; ++point) {
		std::array<uint32_t, LscChannels> q;
		for (unsigned int channel = 0; channel < LscChannels; ++channel) {
			float gain = mesh[channel][point];
			if (!positive(gain))
				return false;
			/* Four 13-bit unsigned Q10 gains, minimum unity. */
			gain = std::clamp(gain, 1.0f, 8191.0f / 1024.0f);
			q[channel] = std::lround(gain * 1024.0f);
		}
		result.grr[point] = q[LscR] | q[LscGr] << 13;
		result.gbb[point] = q[LscB] | q[LscGb] << 13;
	}
	*packed = result;
	return true;
}

} /* namespace libcamera::ipa */
