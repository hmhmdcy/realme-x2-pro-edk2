/* Private per-process ioctl evidence. Does not change any ioctl argument. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <unistd.h>

struct bind_op { uint32_t op, handle; uint64_t offset, iova, range; uint32_t flags, pad; };
struct bind_req {
 uint32_t flags, nr_ops; int32_t fence_fd; uint32_t queue_id;
 uint64_t in_syncobjs, out_syncobjs;
 uint32_t nr_in, nr_out, sync_stride, op_stride;
 union { struct bind_op op; uint64_t ops; };
};
_Static_assert(sizeof(struct bind_op)==40,"Unexpected MSM_VM_BIND operation ABI");
_Static_assert(sizeof(struct bind_req)==88,"Unexpected MSM_VM_BIND request ABI");
static int (*next_ioctl)(int, int, ...);
static int log_fd = -1;
__attribute__((constructor)) static void init(void) {
 next_ioctl = dlsym(RTLD_NEXT, "ioctl");
 const char *path = getenv("K148_IOCTL_LOG");
 if (path) log_fd = open(path, O_WRONLY|O_APPEND|O_CREAT|O_CLOEXEC, 0600);
}
int ioctl(int fd, int req, ...) {
 va_list ap; va_start(ap, req); void *arg = va_arg(ap, void *); va_end(ap);
 int rc = next_ioctl(fd, req, arg), saved = errno;
 if (log_fd >= 0 && ((unsigned)req >> 8 & 255) == 'd' && (req & 255) == 0x4d && arg) {
  const struct bind_req *b = arg;
  for (unsigned i = 0; i < b->nr_ops; i++) {
   const struct bind_op *op = b->nr_ops == 1 ? &b->op :
       (const void *)(uintptr_t)(b->ops + (uint64_t)i * b->op_stride);
   char line[512]; int n = snprintf(line, sizeof(line),
       "{\"pid\":%d,\"fd\":%d,\"rc\":%d,\"errno\":%d,\"queue\":%u,\"op\":%u,\"handle\":%u,\"iova\":%llu,\"range\":%llu,\"offset\":%llu,\"flags\":%u,\"bind_flags\":%u,\"fence\":%d,\"nr_in\":%u,\"nr_out\":%u}\n",
       getpid(),fd,rc,rc < 0 ? saved : 0,b->queue_id,op->op,op->handle,
       (unsigned long long)op->iova,(unsigned long long)op->range,
       (unsigned long long)op->offset,op->flags,b->flags,b->fence_fd,b->nr_in,b->nr_out);
   if (n > 0 && (size_t)n < sizeof(line)) write(log_fd, line, n);
  }
 }
 errno = saved; return rc;
}
