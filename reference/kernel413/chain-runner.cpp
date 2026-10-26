/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc11_generation.h"
#include "../kernel409/libipa/ltm_adrc.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record {
	Tmc11Region region;float gain,dark;uint32_t present;std::array<float,257> gamma;
	std::array<float,1024> weights;std::array<uint32_t,1024> histogram;
	std::array<float,65> equivalent;std::array<float,1024> contrastAxis;std::array<float,65> forward;
	std::array<int32_t,65> baseCurve;std::array<int16_t,65> baseScale;uint16_t padding;
};
static_assert(sizeof(Record)==14416);
int main()
{
	Record r;
	while(fread(&r,sizeof r,1,stdin)==1) {
		auto saved=r;Tmc11GenerationResult generated;std::array<float,65> normalized,gain;Tmc11PchipResult sampled;
		Ltm13AdrcCurves curves;Ltm13AdrcBlend blend;Ltm13AdrcTables tables;memset(&tables,0xa5,sizeof tables);
		uint32_t ok=r.present<=1 && generateTmc11Curve(r.region,r.gain,r.dark,r.gamma,r.weights,r.present?&r.histogram:nullptr,&generated) &&
			normalizeTmc11LtmInput(r.equivalent,&normalized) && sampleTmc11Pchip(generated.pchip,normalized,&sampled) &&
			applyTmc11LtmContrast(generated.ltm,normalized,sampled.gain,r.contrastAxis,generated.contrastCurve,&gain) &&
			calculateLtm13Adrc({r.equivalent,gain,r.forward},&curves) &&
			blendLtm13Adrc(curves,sampled.ltmMix,r.baseCurve,r.baseScale,&blend) && encodeLtm13AdrcTables(blend,&tables);
		assert(!memcmp(&r,&saved,sizeof r));
		if(!ok){const auto*b=reinterpret_cast<const unsigned char*>(&tables);for(size_t i=0;i<sizeof tables;++i)assert(b[i]==0xa5);}
		assert(fwrite(&ok,4,1,stdout)==1 && fwrite(&tables,sizeof tables,1,stdout)==1);
	}
	return ferror(stdin)||ferror(stdout);
}
