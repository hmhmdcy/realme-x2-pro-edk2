/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc10_aec.h"
#include "../kernel410/libipa/tmc10.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa;
struct Record { uint32_t count; Tmc10AecControl control; float lux,gain,drc,dark; Tmc10AecRegion regions[5]; };
static_assert(sizeof(Record)==324 && sizeof(Tmc10AecResult)==56 && sizeof(Tmc10Curve)==72);
int main()
{
	Record in;
	while (fread(&in,sizeof in,1,stdin)==1) {
		Record before=in; Tmc10AecResult region; Tmc10Curve curve; std::array<float,65> sampled;
		memset(&region,0xa5,sizeof region);memset(&curve,0xa5,sizeof curve);memset(sampled.data(),0xa5,sizeof sampled);
		uint32_t ok=in.count<=5 && interpolateTmc10Aec(in.regions,in.count,in.control,in.lux,in.gain,&region);
		uint32_t knees=0,gains=0;
		if (ok) {
			Tmc10Parameters p{in.drc,in.dark,region.data[0],region.data[1],region.data[4],region.data[5],region.data[6]};
			knees=calculateTmc10Curve(p,&curve);
			std::array<float,65> eq;for (unsigned i=0;i<65;++i) eq[i]=float(i*4095)/64;
			if (knees) gains=sampleTmc10LtmGain(curve,eq,&sampled);
		}
		assert(!memcmp(&in,&before,sizeof in));
		auto unchanged=[](const void *p,size_t n){const auto*b=static_cast<const unsigned char*>(p);for(size_t i=0;i<n;++i)assert(b[i]==0xa5);};
		if(!ok) unchanged(&region,sizeof region);
		if(!knees) unchanged(&curve,sizeof curve);
		if(!gains) unchanged(sampled.data(),sizeof sampled);
		assert(fwrite(&ok,4,1,stdout)==1 && fwrite(&region,sizeof region,1,stdout)==1 &&
		       fwrite(&knees,4,1,stdout)==1 && fwrite(&curve,sizeof curve,1,stdout)==1 &&
		       fwrite(&gains,4,1,stdout)==1 && fwrite(sampled.data(),sizeof sampled,1,stdout)==1);
	}
	return ferror(stdin)||ferror(stdout);
}
