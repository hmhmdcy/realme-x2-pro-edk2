/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "focus_functions.h"
#include <cassert>
#include <chrono>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
using namespace libcamera;
static LumaFocusWorkspace workspace;
static FocusStatistics compare(const uint8_t *data,size_t bytes,unsigned w,unsigned h,unsigned stride)
{
 const bool valid=data&&w>=12&&h>=12&&stride>=w&&uint64_t(h-1)*stride+w<=bytes;
 if(valid){assert(workspace.prepare(w,h));std::fill(workspace.grid.begin(),workspace.grid.end(),0xa55a);std::fill(workspace.smooth.begin(),workspace.smooth.end(),0x5aa5);}
 const auto *grid=workspace.grid.data(),*smooth=workspace.smooth.data();const auto storage=workspace.storageBytes();
 const unsigned previousWidth=workspace.width,previousHeight=workspace.height;
 auto a=referenceLumaFocus(data,bytes,w,h,stride),b=measureLumaFocus(data,bytes,w,h,stride,&workspace);
 assert(workspace.grid.data()==grid&&workspace.smooth.data()==smooth&&workspace.storageBytes()==storage);
 if(!valid)assert(workspace.width==previousWidth&&workspace.height==previousHeight);
 assert(a.valid==b.valid && a.figureOfMerit()==b.figureOfMerit());
 for(size_t i=0;i<a.regions.size();++i)assert(a.regions[i].energy==b.regions[i].energy && a.regions[i].sum==b.regions[i].sum && a.regions[i].samples==b.regions[i].samples);
 return b;
}
int main(int argc,char **argv)
{
 if(argc==1){
  struct Layout{unsigned w,h,stride;};
  const Layout layouts[]={{12,12,12},{13,17,32},{640,480,640},{1280,720,1280},{1920,1080,1920},{641,479,704}};
  unsigned valid=0,invalid=0;
  for(auto l:layouts)for(unsigned pattern=0;pattern<9;++pattern){
   std::vector<uint8_t> data(size_t(l.h-1)*l.stride+l.w);uint32_t random=0x4c39e127;
   for(size_t i=0;i<data.size();++i){
    random^=random<<13;random^=random>>17;random^=random<<5;
    const uint8_t flat[]={0,255,3,4,251,252};
    data[i]=pattern<6?flat[pattern]:pattern==6?uint8_t((i/l.stride+i%l.stride)%256):pattern==7?uint8_t(random):uint8_t(((i/l.stride/5+i%l.stride/7)%2)*255);
   }
   assert(compare(data.data(),data.size(),l.w,l.h,l.stride).valid);++valid;
   assert(!compare(data.data(),data.size()-1,l.w,l.h,l.stride).valid);++invalid;
  }
  uint8_t small[144]{};
  for(auto l:{Layout{0,12,12},Layout{12,0,12},Layout{11,12,12},Layout{12,11,12},Layout{12,12,11},Layout{12,12,UINT32_MAX},Layout{UINT32_MAX,12,UINT32_MAX}}){
   assert(!compare(small,sizeof small,l.w,l.h,l.stride).valid);++invalid;
  }
  assert(!compare(nullptr,144,12,12,12).valid);++invalid;
  assert(!workspace.prepare(11,12));workspace.clear();assert(!workspace.storageBytes()&&!workspace.width&&!workspace.height);
  assert(workspace.prepare(1280,720));assert(workspace.storageBytes()==307200);
  std::vector<uint8_t> sequence(1280*720,121);
  const auto *stableGrid=workspace.grid.data(),*stableSmooth=workspace.smooth.data();
  for(unsigned i=0;i<16;++i){sequence[i*1000]=uint8_t(i*13);assert(compare(sequence.data(),sequence.size(),1280,720,1280).valid);assert(workspace.grid.data()==stableGrid&&workspace.smooth.data()==stableSmooth);}
  auto plain=measureLumaFocus(sequence.data(),sequence.size(),1280,720,1280);
  assert(plain.figureOfMerit()==referenceLumaFocus(sequence.data(),sequence.size(),1280,720,1280).figureOfMerit());
  workspace.clear();assert(workspace.grid.empty()&&workspace.smooth.empty()&&!workspace.storageBytes());
  std::cout<<"{\"synthetic_passed\":true,\"valid_cases\":"<<valid<<",\"invalid_cases\":"<<invalid<<"}\n";
  return 0;
 }
 if(argc!=7)return 2;
 const unsigned w=std::stoul(argv[2]),h=std::stoul(argv[3]),stride=std::stoul(argv[4]),repetitions=std::stoul(argv[5]);
 assert(repetitions>=1&&repetitions<=128);
 std::ifstream input(argv[1],std::ios::binary);assert(input.good());
 std::vector<uint8_t> data((std::istreambuf_iterator<char>(input)),{});assert(data.size()==size_t(stride)*h*3/2);
 auto result=compare(data.data(),data.size(),w,h,stride);assert(result.figureOfMerit().value_or(-1)==std::stoi(argv[6]));
 std::vector<int64_t> times[2];uint64_t checksum=0;
 for(unsigned i=0;i<repetitions;++i)for(unsigned j=0;j<2;++j){
  const unsigned which=(i+j)%2;const auto begin=std::chrono::steady_clock::now();
  auto statistics=which?measureLumaFocus(data.data(),data.size(),w,h,stride,&workspace):referenceLumaFocus(data.data(),data.size(),w,h,stride);
  const auto score=statistics.figureOfMerit();checksum+=uint32_t(score.value_or(0));
  times[which].push_back(std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-begin).count());
  assert(score==result.figureOfMerit());
 }
 for(auto &t:times)std::sort(t.begin(),t.end());
 std::cout<<"{\"fixture_passed\":true,\"width\":"<<w<<",\"height\":"<<h<<",\"repetitions\":"<<repetitions
  <<",\"reference_median_us\":"<<times[0][times[0].size()/2]<<",\"optimized_median_us\":"<<times[1][times[1].size()/2]
  <<",\"checksum_consistent\":"<<(checksum==uint64_t(uint32_t(result.figureOfMerit().value_or(0)))*2*repetitions?"true":"false")<<"}\n";
}
