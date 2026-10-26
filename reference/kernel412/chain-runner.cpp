/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc11_ltm.h"
#include "../kernel409/libipa/ltm_adrc.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record {
	std::array<float,65> equivalent; Tmc11PchipCurve pchip; Tmc11LtmContrast contrast;
	std::array<float,1024> axis,hist; std::array<float,65> forward;
	std::array<int32_t,65> baseCurve; std::array<int16_t,65> baseScale; uint16_t padding;
};
static_assert(sizeof(Record)==9192 && sizeof(Ltm13AdrcTables)==512);
int main()
{
	Record r;
	while(fread(&r,sizeof r,1,stdin)==1) {
		auto saved=r;std::array<float,65> normalized,gain;Tmc11PchipResult pchip;
		Ltm13AdrcCurves curves;Ltm13AdrcBlend blended;Ltm13AdrcTables tables;
		memset(&tables,0xa5,sizeof tables);
		uint32_t ok=normalizeTmc11LtmInput(r.equivalent,&normalized) && sampleTmc11Pchip(r.pchip,normalized,&pchip) &&
			applyTmc11LtmContrast(r.contrast,normalized,pchip.gain,r.axis,r.hist,&gain) &&
			calculateLtm13Adrc({r.equivalent,gain,r.forward},&curves) &&
			blendLtm13Adrc(curves,pchip.ltmMix,r.baseCurve,r.baseScale,&blended) && encodeLtm13AdrcTables(blended,&tables);
		assert(!memcmp(&r,&saved,sizeof r));
		if(!ok){const auto*b=reinterpret_cast<const unsigned char*>(&tables);for(size_t i=0;i<sizeof tables;++i)assert(b[i]==0xa5);}
		assert(fwrite(&ok,4,1,stdout)==1 && fwrite(&tables,sizeof tables,1,stdout)==1);
	}
	return ferror(stdin)||ferror(stdout);
}
