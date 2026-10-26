/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ipe_frame_history.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace libcamera::ipa::camss;
static IpeFrameObservation observation(uint64_t epoch, uint32_t sof)
{
	IpeFrameObservation f;f.epoch=epoch;f.sof=sof;f.exposureNs=1000000;f.exposureLines=100;
	f.analogueGain=2;f.histogram[sof%1024]=100;f.population=100;return f;
}
int main()
{
	unsigned cases=0;IpeFrameHistory h;uint64_t token=99;
	assert(h.prepare(observation(1,0),&token)==-ESTALE && token==99);++cases;
	assert(!h.start(0) && h.start(1) && !h.start(2));++cases;
	auto f=observation(1,0);assert(!h.prepare(f,&token));auto saved=*h.pending(token);f.histogram.fill(0);
	assert(h.pending(token)->histogram==saved.histogram && !h.committed());++cases;
	assert(h.resolve(2,0,token,true)==-ESTALE && h.pending(token));++cases;
	assert(h.resolve(1,1,token,true)==-ESTALE && h.pending(token));++cases;
	assert(h.resolve(1,0,token,false)==IpeFrameHistory::Discarded && !h.committed());++cases;
	assert(h.resolve(1,0,token,true)==-ENOENT && !h.committed());++cases;
	assert(h.prepare(observation(1,0),&token)==-EALREADY);++cases;
	uint64_t a,b;assert(!h.prepare(observation(1,1),&a) && !h.prepare(observation(1,2),&b));
	assert(h.resolve(1,2,b,true)==IpeFrameHistory::Committed && h.committed()->sof==2);++cases;
	assert(h.resolve(1,1,a,true)==IpeFrameHistory::Superseded && h.committed()->sof==2);++cases;
	uint64_t c;assert(!h.prepare(observation(1,3),&c));h.stop();
	assert(!h.pendingCount() && h.counters().aborted==1 && h.resolve(1,3,c,true)==-ESTALE);++cases;
	assert(!h.start(1) && h.start(2) && !h.committed());uint64_t next;assert(!h.prepare(observation(2,0),&next) && next>c);
	assert(h.resolve(2,0,c,true)==-ENOENT && h.pending(next));++cases;
	for(unsigned i=1;i<64;++i)assert(!h.prepare(observation(2,i),&token));
	assert(h.prepare(observation(2,64),&token)==-ENOSPC && h.pendingCount()==64);++cases;
	assert(h.resolve(2,0,next,false)==0 && !h.prepare(observation(2,64),&token));++cases;
	h.stop();assert(h.counters().prepared==65 && h.counters().discarded==1 && h.counters().aborted==64);++cases;
	assert(h.start(3));
	for(unsigned i=0;i<5;++i){auto invalid=observation(3,0);uint64_t out=123;
		if(i==0)invalid.histogram.fill(0);if(i==1)invalid.exposureNs=0;if(i==2)invalid.exposureLines=0;
		if(i==3)invalid.analogueGain=std::numeric_limits<float>::quiet_NaN();
		if(i==4){invalid.luxValid=true;invalid.exposureIndex=std::numeric_limits<float>::infinity();}
		assert(h.prepare(invalid,&out)==-EINVAL && out==123 && !h.pendingCount());++cases;}
	assert(h.prepare(observation(3,0),nullptr)==-EINVAL && !h.pendingCount());++cases;
	assert(!h.prepare(observation(3,0),&token) && h.resolve(3,0,token,true)==1);
	assert(h.committed()->exposureNs==1000000 && h.committed()->analogueGain==2);++cases;
	std::printf("IPE_HISTORY_MODEL cases=%u passed=1\n",cases);
}
