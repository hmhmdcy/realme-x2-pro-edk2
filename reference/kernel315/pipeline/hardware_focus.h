/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Bounded spatial focus measurement on the owned NV12 Y plane. */
#pragma once
#include <algorithm>
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
 std::vector<uint16_t> grid(size_t(columns)*rows),smooth(grid.size());
 for (unsigned y=0;y<rows;++y) for (unsigned x=0;x<columns;++x) {
  unsigned px=uint64_t(x)*(width-2)/(columns-1),py=uint64_t(y)*(height-2)/(rows-1);
  uint32_t sum=data[size_t(py)*stride+px]+data[size_t(py)*stride+px+1]+data[size_t(py+1)*stride+px]+data[size_t(py+1)*stride+px+1];
  grid[size_t(y)*columns+x]=sum*257/4;
 }
 for (unsigned y=1;y+1<rows;++y) for (unsigned x=1;x+1<columns;++x) {
  uint32_t sum=0;
  for (unsigned j=y-1;j<=y+1;++j) for (unsigned i=x-1;i<=x+1;++i) sum+=grid[size_t(j)*columns+i];
  smooth[size_t(y)*columns+x]=sum/9;
 }
 for (unsigned y=2;y+2<rows;++y) for (unsigned x=2;x+2<columns;++x) {
  uint16_t mean=smooth[size_t(y)*columns+x];
  if (mean<1024 || mean>64512) continue;
  int64_t dx=int64_t(smooth[size_t(y)*columns+x+1])-smooth[size_t(y)*columns+x-1];
  int64_t dy=int64_t(smooth[size_t(y+1)*columns+x])-smooth[size_t(y-1)*columns+x];
  auto &r=result.regions[(y*FocusStatistics::kRows/rows)*FocusStatistics::kColumns+x*FocusStatistics::kColumns/columns];
  r.energy+=dx*dx+dy*dy;r.sum+=mean;++r.samples;
 }
 result.valid=true;
 return result;
}

inline std::optional<int32_t> measureFrameFocus(FrameBuffer *buffer,const StreamConfiguration &configuration)
{
 if (buffer->planes().empty() || buffer->metadata().planes().empty()) return std::nullopt;
 const auto &plane=buffer->planes()[0];
 dma_buf_sync sync{DMA_BUF_SYNC_START|DMA_BUF_SYNC_READ};
 if (ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync)) return std::nullopt;
 std::optional<int32_t> score;
 {
  MappedFrameBuffer mapped(buffer,MappedFrameBuffer::MapFlag::Read);
  if (mapped.isValid() && !mapped.planes().empty())
   score=measureLumaFocus(mapped.planes()[0].data(),std::min<size_t>(mapped.planes()[0].size(),buffer->metadata().planes()[0].bytesused),
                          configuration.size.width,configuration.size.height,configuration.stride).figureOfMerit();
 }
 sync.flags=DMA_BUF_SYNC_END|DMA_BUF_SYNC_READ;
 if (ioctl(plane.fd.get(),DMA_BUF_IOCTL_SYNC,&sync)) return std::nullopt;
 return score;
}
}
