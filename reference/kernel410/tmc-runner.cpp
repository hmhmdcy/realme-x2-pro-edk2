/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc10.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <cstdint>
using namespace libcamera::ipa;
struct Record { Tmc10Parameters input; std::array<float,65> equivalent; };
static_assert(sizeof(Record)==288);
static_assert(sizeof(Tmc10Curve)==72);
int main()
{
	assert(!calculateTmc10Curve({},nullptr));
	Record r;
	while(std::fread(&r,sizeof r,1,stdin)==1) {
		auto saved=r;
		Tmc10Curve curve;
		std::array<float,65> gain;
		std::memset(&curve,0xa5,sizeof curve);
		std::memset(&gain,0xa5,sizeof gain);
		auto oldCurve=curve;auto oldGain=gain;
		uint32_t ok=calculateTmc10Curve(r.input,&curve);
		if(!ok)assert(!std::memcmp(&curve,&oldCurve,sizeof curve));
		uint32_t sampled=ok&&sampleTmc10LtmGain(curve,r.equivalent,&gain);
		if(!sampled)assert(!std::memcmp(&gain,&oldGain,sizeof gain));
		assert(!std::memcmp(&r,&saved,sizeof r));
		assert(std::fwrite(&ok,4,1,stdout)==1&&std::fwrite(&curve,sizeof curve,1,stdout)==1);
		assert(std::fwrite(&sampled,4,1,stdout)==1&&std::fwrite(gain.data(),4,65,stdout)==65);
	}
	return std::ferror(stdin)||std::ferror(stdout);
}
