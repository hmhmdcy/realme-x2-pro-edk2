/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Exact bounded focus statistics on the owned NV12 Y plane. */
#pragma once
#include <algorithm>
#include <array>
#include <chrono>
#include <optional>
#include <new>
#include <vector>
#include <linux/dma-buf.h>
#include <sys/ioctl.h>
#include <sys/resource.h>
#include <sched.h>
#include <time.h>
#include <libcamera/stream.h>
#include "libcamera/internal/mapped_framebuffer.h"
#include "libcamera/internal/software_isp/focus_stats.h"

namespace libcamera {
struct LumaFocusWorkspace {
 static constexpr size_t kMaximumCells=320*240;
 unsigned width=0,height=0,columns=0,rows=0;
 std::array<unsigned,320> sampleX{},regionX{};
 std::vector<uint16_t> grid,smooth;
 bool prepare(unsigned w,unsigned h)
 {
  if(w<12 || h<12)return false;
  if(width==w && height==h)return true;
  const unsigned c=std::min(320U,w/2),r=std::min(240U,h/2);
  try {
   grid.reserve(kMaximumCells);smooth.reserve(kMaximumCells);
   grid.assign(size_t(c)*r,0);smooth.assign(size_t(c)*r,0);
  } catch(const std::bad_alloc &) {clear();return false;}
  for(unsigned x=0;x<c;++x){sampleX[x]=uint64_t(x)*(w-2)/(c-1);regionX[x]=x*FocusStatistics::kColumns/c;}
  width=w;height=h;columns=c;rows=r;return true;
 }
 void clear()
 {
  std::vector<uint16_t>().swap(grid);std::vector<uint16_t>().swap(smooth);
  width=height=columns=rows=0;
 }
 size_t storageBytes() const {return (grid.capacity()+smooth.capacity())*sizeof(uint16_t);}
};

inline FocusStatistics measureLumaFocus(const uint8_t *data,size_t bytes,unsigned width,unsigned height,unsigned stride,LumaFocusWorkspace *workspace=nullptr)
{
 FocusStatistics result;
 if (!data || width<12 || height<12 || stride<width || uint64_t(height-1)*stride+width>bytes) return result;
 std::optional<LumaFocusWorkspace> local;
 if(!workspace){local.emplace();workspace=&*local;}
 if(!workspace->prepare(width,height))return result;
 const unsigned columns=workspace->columns,rows=workspace->rows;
 const auto &sampleX=workspace->sampleX,&regionX=workspace->regionX;
 auto &grid=workspace->grid,&smooth=workspace->smooth;
 /* Every grid cell and every smooth cell read below is overwritten this frame. */
 for (unsigned y=0;y<rows;++y) {
  const unsigned py=uint64_t(y)*(height-2)/(rows-1);
  const uint8_t *line=data+size_t(py)*stride,*next=line+stride;
  for (unsigned x=0;x<columns;++x) {
   const unsigned px=sampleX[x];
   const uint32_t sum=line[px]+line[px+1]+next[px]+next[px+1];
   grid[size_t(y)*columns+x]=sum*257/4;
  }
 }
 for (unsigned y=1;y+1<rows;++y) {
  const uint16_t *a=grid.data()+size_t(y-1)*columns,*b=a+columns,*c=b+columns;
  uint32_t sum=uint32_t(a[0])+a[1]+a[2]+b[0]+b[1]+b[2]+c[0]+c[1]+c[2];
  for (unsigned x=1;x+1<columns;++x) {
   smooth[size_t(y)*columns+x]=sum/9;
   if (x+2<columns) {
    sum-=uint32_t(a[x-1])+b[x-1]+c[x-1];
    sum+=uint32_t(a[x+2])+b[x+2]+c[x+2];
   }
  }
 }
 for (unsigned y=2;y+2<rows;++y) {
  const unsigned regionRow=(y*FocusStatistics::kRows/rows)*FocusStatistics::kColumns;
  for (unsigned x=2;x+2<columns;++x) {
   const uint16_t mean=smooth[size_t(y)*columns+x];
   if (mean<1024 || mean>64512) continue;
   const int64_t dx=int64_t(smooth[size_t(y)*columns+x+1])-smooth[size_t(y)*columns+x-1];
   const int64_t dy=int64_t(smooth[size_t(y+1)*columns+x])-smooth[size_t(y-1)*columns+x];
   auto &r=result.regions[regionRow+regionX[x]];
   r.energy+=dx*dx+dy*dy;r.sum+=mean;++r.samples;
  }
 }
 result.valid=true;
 return result;
}

struct FocusExecutionSnapshot {
 int64_t cpuNs=0;long minor=0,major=0,voluntary=0,involuntary=0;int cpu=-1;bool valid=false;
};
inline FocusExecutionSnapshot focusExecutionSnapshot()
{
 FocusExecutionSnapshot result;timespec cpu{};rusage usage{};
 if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&cpu) || getrusage(RUSAGE_THREAD,&usage))return result;
 result.cpuNs=int64_t(cpu.tv_sec)*1000000000+cpu.tv_nsec;
 result.minor=usage.ru_minflt;result.major=usage.ru_majflt;
 result.voluntary=usage.ru_nvcsw;result.involuntary=usage.ru_nivcsw;
 result.cpu=sched_getcpu();result.valid=result.cpu>=0;return result;
}

struct FocusMeasurementTiming {
 int64_t syncStartUs=0,mapUs=0,sampleUs=0,scoreUs=0,unmapUs=0,syncEndUs=0;
 int64_t sampleCpuUs=0;long sampleMinor=0,sampleMajor=0,sampleVoluntary=0,sampleInvoluntary=0;
 int sampleCpuBefore=-1,sampleCpuAfter=-1;bool sampleExecutionValid=false;
};

inline std::optional<int32_t> measureFrameFocus(FrameBuffer *buffer,const StreamConfiguration &configuration,
                                              FocusMeasurementTiming *timing=nullptr,LumaFocusWorkspace *workspace=nullptr)
{
 using Clock=std::chrono::steady_clock;
 auto previous=Clock::now();
 const auto elapsed=[&]() {const auto now=Clock::now();const auto us=std::chrono::duration_cast<std::chrono::microseconds>(now-previous).count();previous=now;return us;};
 FocusMeasurementTiming measured;
 if (buffer->planes().empty() || buffer->metadata().planes().empty()) return std::nullopt;
 const auto &plane=buffer->planes()[0];
 dma_buf_sync sync{DMA_BUF_SYNC_START|DMA_BUF_SYNC_READ};
 if (ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync)) return std::nullopt;
 measured.syncStartUs=elapsed();
 std::optional<int32_t> score;
 {
  MappedFrameBuffer mapped(buffer,MappedFrameBuffer::MapFlag::Read);
  measured.mapUs=elapsed();
  if (mapped.isValid() && !mapped.planes().empty()) {
   const auto usageBefore=focusExecutionSnapshot();
   const auto statistics=measureLumaFocus(mapped.planes()[0].data(),std::min<size_t>(mapped.planes()[0].size(),buffer->metadata().planes()[0].bytesused),
                                         configuration.size.width,configuration.size.height,configuration.stride,workspace);
   const auto usageAfter=focusExecutionSnapshot();
   measured.sampleUs=elapsed();
   measured.sampleExecutionValid=usageBefore.valid && usageAfter.valid && usageAfter.cpuNs>=usageBefore.cpuNs;
   if(measured.sampleExecutionValid){
    measured.sampleCpuUs=(usageAfter.cpuNs-usageBefore.cpuNs)/1000;
    measured.sampleMinor=usageAfter.minor-usageBefore.minor;measured.sampleMajor=usageAfter.major-usageBefore.major;
    measured.sampleVoluntary=usageAfter.voluntary-usageBefore.voluntary;measured.sampleInvoluntary=usageAfter.involuntary-usageBefore.involuntary;
    measured.sampleCpuBefore=usageBefore.cpu;measured.sampleCpuAfter=usageAfter.cpu;
   }
   score=statistics.figureOfMerit();measured.scoreUs=elapsed();
  }
 }
 measured.unmapUs=elapsed();
 sync.flags=DMA_BUF_SYNC_END|DMA_BUF_SYNC_READ;
 const int status=ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync);
 measured.syncEndUs=elapsed();if(timing)*timing=measured;
 if(status)return std::nullopt;
 return score;
}
}
