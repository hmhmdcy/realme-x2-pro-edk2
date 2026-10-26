/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc11_generation.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record { Tmc11Region region;float gain,dark;uint32_t present;std::array<float,257> gamma;std::array<float,1024> weights;std::array<uint32_t,1024> histogram; };
static_assert(sizeof(Record)==9408);
int main()
{
	Record r;
	while(fread(&r,sizeof r,1,stdin)==1) {
		auto saved=r;Tmc11GenerationResult out;memset(&out,0xa5,sizeof out);
		uint32_t ok=r.present<=1 && generateTmc11Curve(r.region,r.gain,r.dark,r.gamma,r.weights,r.present?&r.histogram:nullptr,&out);
		assert(!memcmp(&r,&saved,sizeof r));
		if(!ok){const auto*b=reinterpret_cast<const unsigned char*>(&out);for(size_t i=0;i<sizeof out;++i)assert(b[i]==0xa5);}
		assert(fwrite(&ok,4,1,stdout)==1 && fwrite(&out,sizeof out,1,stdout)==1);
	}
	return ferror(stdin)||ferror(stdout);
}
