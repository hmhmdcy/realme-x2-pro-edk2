/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc11_ltm.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <cstdint>
using namespace libcamera::ipa;
struct Record { std::array<float,65> equivalent; Tmc11PchipCurve curve; Tmc11LtmContrast contrast; std::array<float,1024> axis,hist; };
static_assert(sizeof(Record)==8540 && sizeof(Tmc11PchipResult)==264);
int main()
{
	Record r;
	while(fread(&r,sizeof r,1,stdin)==1) {
		auto saved=r;std::array<float,65> normalized,gain;Tmc11PchipResult pchip;
		memset(normalized.data(),0xa5,sizeof normalized);memset(&pchip,0xa5,sizeof pchip);memset(gain.data(),0xa5,sizeof gain);
		uint32_t ok=normalizeTmc11LtmInput(r.equivalent,&normalized);
		uint32_t sampled=ok && sampleTmc11Pchip(r.curve,normalized,&pchip);
		uint32_t enhanced=sampled && applyTmc11LtmContrast(r.contrast,normalized,pchip.gain,r.axis,r.hist,&gain);
		assert(!memcmp(&r,&saved,sizeof r));
		auto check=[](const void*p,size_t n){const auto*b=static_cast<const unsigned char*>(p);for(size_t i=0;i<n;++i)assert(b[i]==0xa5);};
		if(!ok)check(normalized.data(),sizeof normalized);
		if(!sampled)check(&pchip,sizeof pchip);
		if(!enhanced)check(gain.data(),sizeof gain);
		assert(fwrite(&ok,4,1,stdout)==1 && fwrite(normalized.data(),sizeof normalized,1,stdout)==1 &&
		       fwrite(&sampled,4,1,stdout)==1 && fwrite(&pchip,sizeof pchip,1,stdout)==1 &&
		       fwrite(&enhanced,4,1,stdout)==1 && fwrite(gain.data(),sizeof gain,1,stdout)==1);
	}
	return ferror(stdin)||ferror(stdout);
}
