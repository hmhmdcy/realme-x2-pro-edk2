/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc10.h"
#include "../kernel409/libipa/ltm_adrc.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record {
	Tmc10Parameters parameters;
	std::array<float,65> equivalent,forward;
	std::array<int32_t,65> curve;
	std::array<int16_t,65> scale;
};
static_assert(sizeof(Record)==940);
int main()
{
	Record input;
	while(std::fread(&input,sizeof input,1,stdin)==1) {
		Record saved;std::memcpy(&saved,&input,sizeof input);
		Tmc10Curve tmc;
		Ltm13AdrcSamples samples;
		Ltm13AdrcCurves generated;
		Ltm13AdrcBlend blended;
		Ltm13AdrcTables tables;
		std::memset(&tables,0xa5,sizeof tables);auto untouched=tables;
		samples.equivalent12=input.equivalent;samples.forwardGamma10=input.forward;
		uint32_t ok=calculateTmc10Curve(input.parameters,&tmc)&&
			sampleTmc10LtmGain(tmc,input.equivalent,&samples.sampledGainQ10)&&
			calculateLtm13Adrc(samples,&generated)&&
			blendLtm13Adrc(generated,tmc.ltmMix,input.curve,input.scale,&blended)&&
			encodeLtm13AdrcTables(blended,&tables);
		if(!ok)assert(!std::memcmp(&tables,&untouched,sizeof tables));
		assert(!std::memcmp(&input,&saved,sizeof input));
		assert(std::fwrite(&ok,4,1,stdout)==1&&std::fwrite(&tables,sizeof tables,1,stdout)==1);
	}
	return std::ferror(stdin)||std::ferror(stdout);
}
