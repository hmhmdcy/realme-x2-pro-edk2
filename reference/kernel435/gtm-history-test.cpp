/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <cassert>
#include <cstdio>
#include "ife_gtm_history.h"
#include "ipe_numeric_history.h"
using namespace libcamera::ipa::camss;
struct Math { uint64_t cookie=0,value=0; };
int main()
{
 IfeGtmHistory<Math> physical;using H=decltype(physical);
 H::Version initial;H::Pointer first,actual;bool changed=false;
 assert(!physical.stage(initial,0,&first));assert(first->parameters.cookie==1&&!physical.active());
 H::Pointer ignored;assert(physical.stage(initial,1,&ignored)==-EBUSY);
 camss_stats_ife_gtm receipt{};receipt.cookie=1;receipt.generation=1;receipt.status=1;receipt.bank=0;
 auto invalid=receipt;invalid.cookie=999;assert(physical.accept(0,invalid,&actual,&changed)==-ESTALE&&!physical.active());
 invalid=receipt;invalid.generation=2;assert(physical.accept(0,invalid,&actual,&changed)==-EPROTO&&!physical.active());
 assert(!physical.accept(0,receipt,&actual,&changed)&&changed&&actual==first);
 assert(!physical.accept(1,receipt,&actual,&changed)&&!changed);
 H::Version next;next.ready=true;next.sourceSof=5;next.sourceHistogram=111;next.math.value=42;next.parameters.enabled=1;
 H::Pointer second;assert(!physical.stage(next,1,&second));assert(physical.active()==first);
 receipt.cookie=2;receipt.generation=2;receipt.status=3;receipt.bank=1;
 assert(physical.accept(5,receipt,&actual,&changed)==-EPROTO&&physical.active()==first);
 invalid=receipt;invalid.bank=2;assert(physical.accept(6,invalid,&actual,&changed)==-EPROTO);
 invalid=receipt;invalid.status=1;assert(physical.accept(6,invalid,&actual,&changed)==-EPROTO);
 assert(!physical.accept(6,receipt,&actual,&changed)&&changed&&actual==second);
 auto frameVersion=actual;IpeNumericHistory<Math> numeric;assert(numeric.start(100));
 Math proposed{frameVersion->parameters.cookie,frameVersion->math.value};assert(!numeric.prepare(100,6,9,0,proposed));
 next.sourceSof=7;next.math.value=99;H::Pointer third;assert(!physical.stage(next,2,&third));
 receipt.cookie=3;receipt.generation=3;receipt.bank=0;assert(!physical.accept(8,receipt,&actual,&changed)&&actual==third);
 assert(frameVersion->math.value==42&&frameVersion->parameters.cookie==2);
 /* IPE failure discards math, retaining already-ACKed physical version 3. */
 assert(numeric.resolve(100,6,9,false)==0&&numeric.revision()==0&&physical.active()==third);
 assert(!numeric.prepare(100,9,10,0,proposed));assert(numeric.resolve(100,9,10,true)==1);
 assert(numeric.state().cookie==2&&numeric.state().value==42&&physical.active()->parameters.cookie==3);
 invalid=receipt;invalid.cookie=2;invalid.generation=2;invalid.bank=1;assert(physical.accept(10,invalid,&actual,&changed)==-ESTALE);
 next.sourceSof=11;H::Pointer cancelled;assert(!physical.stage(next,3,&cancelled));physical.cancelUnsubmitted(cancelled->parameters.cookie);assert(!physical.busy()&&physical.active()==third);
 physical.reset();assert(!physical.active()&&!physical.busy()&&frameVersion->math.value==42);
 puts("GTM_HISTORY_PASS submission_not_ack=1 causal_sof=1 immutable_frame=1 ipe_failure_keeps_ife=1 successful_math_uses_bound_version=1");
}
