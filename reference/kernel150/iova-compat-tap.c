/* SPDX-License-Identifier: MIT
 * Per-process experiment: simulate failed optional capability probes.
 * Does not rewrite GPU addresses or modify the installed Mesa library.
 */
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

struct msm_param { uint32_t pipe, param; uint64_t value; uint32_t len, pad; };
struct msm_info { uint32_t handle, info; uint64_t value; uint32_t len, pad; };
_Static_assert(sizeof(struct msm_param) == 24, "MSM parameter ABI");
_Static_assert(sizeof(struct msm_info) == 24, "MSM info ABI");
static int (*real_ioctl)(int, int, ...);
static int log_fd = -1, kernel_iova;

__attribute__((constructor)) static void init(void)
{
    real_ioctl = dlsym(RTLD_NEXT, "ioctl");
    kernel_iova = getenv("K150_KERNEL_IOVA") != NULL;
    const char *path = getenv("K150_IOCTL_LOG");
    if (path) log_fd = open(path, O_WRONLY | O_APPEND | O_CREAT | O_CLOEXEC, 0600);
}

int ioctl(int fd, int req, ...)
{
    va_list ap;
    va_start(ap, req);
    void *arg = va_arg(ap, void *);
    va_end(ap);
    unsigned nr = (unsigned)req & 255;
    int drm = (((unsigned)req >> 8) & 255) == 'd';
    int blocked = 0;
    uint32_t selector = 0;
    uint64_t value = 0;
    const char *kind = NULL;
    if (drm && arg && (nr == 0x40 || nr == 0x41)) {
        struct msm_param *p = arg;
        selector = p->param;
        value = p->value;
        kind = nr == 0x40 ? "get_param" : "set_param";
        blocked = p->pipe == 0x10 && p->len == 0 &&
            ((nr == 0x41 && p->param == 0x16 && p->value == 1) ||
             (kernel_iova && nr == 0x40 && p->param == 0x0e));
    } else if (drm && arg && nr == 0x43) {
        struct msm_info *p = arg;
        selector = p->info;
        value = p->value;
        if (p->info == 1 || p->info == 4) kind = "gem_info";
    } else if (drm && nr == 0x4d) {
        kind = "vm_bind";
    }
    int rc;
    if (blocked) { errno = EOPNOTSUPP; rc = -1; }
    else rc = real_ioctl(fd, req, arg);
    int saved_errno = errno;
    if (arg && kind && nr == 0x43) value = ((struct msm_info *)arg)->value;
    if (arg && kind && nr == 0x40) value = ((struct msm_param *)arg)->value;
    if (kind && log_fd >= 0) {
        char line[384];
        int n = snprintf(line, sizeof(line),
            "{\"kind\":\"%s\",\"selector\":%u,\"blocked\":%d,\"rc\":%d,\"errno\":%d,\"value\":%llu}\n",
            kind, selector, blocked, rc, rc < 0 ? saved_errno : 0,
            (unsigned long long)value);
        if (n > 0 && (size_t)n < sizeof(line)) (void)write(log_fd, line, n);
    }
    errno = saved_errno;
    return rc;
}
