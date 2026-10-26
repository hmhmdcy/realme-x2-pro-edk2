/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "contrast_af.h"
#include <cassert>
#include <iostream>
using libcamera::ipa::ContrastAf;
static ContrastAf::Config configuration{208,926,96,16,3,100000000,120000000000ULL,100,1.15,.75};
static uint64_t now=1000000000;
static uint64_t tick(){return now+=100000000;}
static int32_t curve(int32_t position){double x=(position-304)/100.0;return 500+4000*std::exp(-x*x);}
static void sample(ContrastAf &af,int32_t value){auto t=tick();af.process(true,value,t,100000000,t);}
static void complete(ContrastAf &af,bool flat=false,bool lose=false)
{
 unsigned int moves=0;
 while(af.state()==ContrastAf::State::Scanning){
  af.trigger(tick()); // repeated triggers during a scan must not reset it
  auto move=af.takeMove(tick());assert(move && move->position>=208 && move->position<=926);++moves;assert(moves<130);
  af.applied(move->serial,0,now);
  for(int i=0;i<3;++i)sample(af,1000000); // samples before settle+readout cannot select these outliers
  // Above: only the third sample is beyond settle+guard. Reset by completing two ordinary samples:
  // Median of one outlier and two actual measurements still uses the actual measurement.
  int32_t score=flat?500:curve(move->position);
  if(lose && moves>20)score=0;
  sample(af,score);sample(af,score);
 }
}
int main()
{
 ContrastAf af;assert(af.configure(configuration));assert(!af.takeMove(tick()));
 af.trigger(tick());auto first=af.takeMove(tick());assert(first && first->position==208);
 af.applied(first->serial+1,0,now);assert(!af.takeMove(tick()));
 af.cancel();af.applied(first->serial,0,now);assert(af.state()==ContrastAf::State::Idle && !af.takeMove(tick()));
 af.trigger(tick());auto second=af.takeMove(tick());assert(second && second->serial>first->serial);
 af.applied(second->serial,-5,now);assert(af.state()==ContrastAf::State::Failed);
 assert(af.configure(configuration));af.trigger(tick());complete(af);assert(af.state()==ContrastAf::State::Focused && af.selectedPosition()==304);
 af.cancelScan();assert(af.state()==ContrastAf::State::Focused && af.selectedPosition()==304);
 assert(af.configure(configuration));af.trigger(tick());complete(af,true);assert(af.state()==ContrastAf::State::Failed);
 af.cancelScan();assert(af.state()==ContrastAf::State::Failed);
 assert(af.configure(configuration));af.trigger(tick());complete(af,false,true);assert(af.state()==ContrastAf::State::Failed);
 assert(af.configure(configuration));af.trigger(tick());af.process(false,0,0,0,tick());assert(af.state()==ContrastAf::State::Failed && !af.takeMove(tick()));
 assert(af.configure(configuration));af.trigger(tick());auto move=af.takeMove(tick());assert(move);af.applied(move->serial,0,now);
 for(int i=0;i<8;++i){af.process(true,4500,now,0,now);}
 assert(af.state()==ContrastAf::State::Scanning); // duplicate/old capture
 af.process(false,0,tick(),0,now+configuration.timeoutNs+1);assert(af.state()==ContrastAf::State::Failed);
 for(int i=0;i<11;++i){auto bad=configuration;
  switch(i){case 0:bad.maximum=bad.minimum;break;case 1:bad.coarseStep=0;break;case 2:bad.fineStep=0;break;
  case 3:bad.samples=0;break;case 4:bad.samples=10;break;case 5:bad.peakRatio=1;break;case 6:bad.verifyRatio=2;break;
  case 7:bad.peakRatio=std::nan("");break;case 8:bad.minimum=-1;break;case 9:bad.maximum=INT32_MAX;break;case 10:bad.timeoutNs=1;break;}
  assert(!af.configure(bad));af.trigger(tick());assert(!af.takeMove(tick()));}
 assert(af.configure(configuration));af.trigger(UINT64_MAX-1);assert(af.state()==ContrastAf::State::Failed);
 assert(af.configure(configuration));af.trigger(tick());af.process(true,4000,now,0,0);assert(af.state()==ContrastAf::State::Failed);
 assert(af.configure(configuration));af.trigger(tick());af.process(true,4000,now+1,0,now);assert(af.state()==ContrastAf::State::Failed);
 std::cout<<"{\"passed\":true,\"af_search_cancel_timing_error_and_quality_cases\":true}\n";
}
