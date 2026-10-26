/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Exact bounded focus statistics on the owned NV12 Y plane. */
#pragma once
#include <algorithm>
#include <array>
#include <chrono>
#include <optional>
#include <vector>
#include <linux/dma-buf.h>
#include <sys/ioctl.h>
#include <libcamera/stream.h>
#include "libcamera/internal/mapped_framebuffer.h"
#include "libcamera/internal/software_isp/focus_stats.h"

namespace libcamera {
inline FocusStatistics measureLumaFocus(const uint8_t *data,size_t bytes,unsigned width,unsigned height,unsigned stride)
{
 FocusStatistics result;
 if (!data || width<12 || height<12 || stride<width || uint64_t(height-1)*stride+width>bytes) return result;
 const unsigned columns=std::min(320U,width/2),rows=std::min(240U,height/2);
 std::array<unsigned,320> sampleX{},regionX{};
 for (unsigned x=0;x<columns;++x) {
  sampleX[x]=uint64_t(x)*(width-2)/(columns-1);
  regionX[x]=x*FocusStatistics::kColumns/columns;
 }
 std::vector<uint16_t> grid(size_t(columns)*rows),smooth(grid.size());
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

struct FocusMeasurementTiming {
 int64_t syncStartUs=0,mapUs=0,sampleUs=0,scoreUs=0,unmapUs=0,syncEndUs=0;
};

inline std::optional<int32_t> measureFrameFocus(FrameBuffer *buffer,const StreamConfiguration &configuration,
                                              FocusMeasurementTiming *timing=nullptr)
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
   const auto statistics=measureLumaFocus(mapped.planes()[0].data(),std::min<size_t>(mapped.planes()[0].size(),buffer->metadata().planes()[0].bytesused),
                                         configuration.size.width,configuration.size.height,configuration.stride);
   measured.sampleUs=elapsed();
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
