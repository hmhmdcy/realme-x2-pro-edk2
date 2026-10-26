/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Opt-in single-frame diagnostics; buffer ownership stays with the pipeline. */
#pragma once

#include <cerrno>
#include <fcntl.h>
#include <linux/dma-buf.h>
#include <set>
#include <string>
#include <sys/ioctl.h>
#include <unistd.h>
#include <vector>

#include "libcamera/internal/mapped_framebuffer.h"

namespace libcamera {

inline int toneTraceWrite(int fd, const void *data, size_t size)
{
 const auto *bytes = static_cast<const uint8_t *>(data);
 while (size) {
  ssize_t count = ::write(fd, bytes, size);
  if (count < 0 && errno == EINTR) continue;
  if (count <= 0) return count < 0 ? -errno : -EIO;
  bytes += count; size -= count;
 }
 return 0;
}

inline int toneTraceBytes(const std::string &path, const void *data, size_t size)
{
 int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
 if (fd < 0) return -errno;
 int ret = toneTraceWrite(fd, data, size);
 if (::close(fd) && !ret) ret = -errno;
 return ret;
}

inline int toneTraceBuffer(const std::string &path, FrameBuffer *buffer, size_t expected)
{
 if (!buffer || buffer->metadata().status != FrameMetadata::FrameSuccess ||
     buffer->planes().size() != buffer->metadata().planes().size()) return -EINVAL;
 size_t total = 0;
 std::set<int> fds;
 for (size_t i = 0; i < buffer->planes().size(); ++i) {
  const auto &plane = buffer->planes()[i];
  size_t used = buffer->metadata().planes()[i].bytesused;
  if (plane.fd.get() < 0 || !used || used > plane.length) return -EINVAL;
  total += used; fds.insert(plane.fd.get());
 }
 if (total != expected) return -EINVAL;
 std::vector<int> active;
 int ret = 0;
 for (int fd : fds) {
  dma_buf_sync sync{DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ};
  int status;
  do { status = ::ioctl(fd, DMA_BUF_IOCTL_SYNC, &sync); } while (status && errno == EINTR);
  if (status) { ret = -errno; break; }
  active.push_back(fd);
 }
 if (!ret) {
  MappedFrameBuffer map(buffer, MappedFrameBuffer::MapFlag::Read);
  if (!map.isValid()) ret = map.error();
  else {
   int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
   if (fd < 0) ret = -errno;
   else {
    for (size_t i = 0; !ret && i < map.planes().size(); ++i)
     ret = toneTraceWrite(fd, map.planes()[i].data(), buffer->metadata().planes()[i].bytesused);
    if (::close(fd) && !ret) ret = -errno;
   }
  }
 }
 for (int fd : active) {
  dma_buf_sync sync{DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ};
  int status;
  do { status = ::ioctl(fd, DMA_BUF_IOCTL_SYNC, &sync); } while (status && errno == EINTR);
  if (status && !ret) ret = -errno;
 }
 return ret;
}

} /* namespace libcamera */
