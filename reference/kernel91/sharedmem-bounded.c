/* Only the reviewed kernel RMTFS character device; no /dev/mem or UIO. */
#define _GNU_SOURCE
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "rmtfs.h"
struct rmtfs_mem { uint64_t address, size; int fd; };

static int attribute(const char *path, int base, uint64_t *value)
{
    char buf[64] = {0}, *end;
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    ssize_t n;
    if (fd < 0) return -1;
    n = read(fd, buf, sizeof(buf)-1); close(fd);
    if (n <= 0 || n == sizeof(buf)-1) return -1;
    errno = 0; *value = strtoull(buf, &end, base);
    if (errno || end == buf || (*end != '\n' && *end != 0)) return -1;
    return 0;
}
struct rmtfs_mem *rmtfs_mem_open(void)
{
    const char *root = "/sys/class/rmtfs/qcom_rmtfs_mem1";
    struct rmtfs_mem *mem = calloc(1, sizeof(*mem));
    struct stat st;
    char path[128], buf[64] = {0};
    uint64_t client;
    unsigned major_number, minor_number;
    int fd;
    if (!mem) return NULL;
    mem->fd = -1;
    snprintf(path, sizeof(path), "%s/phys_addr", root);
    if (attribute(path, 16, &mem->address)) goto fail;
    snprintf(path, sizeof(path), "%s/size", root);
    if (attribute(path, 16, &mem->size)) goto fail;
    snprintf(path, sizeof(path), "%s/client_id", root);
    if (attribute(path, 10, &client)) goto fail;
    if (client != 1 || mem->size != 0x200000 || mem->address < 0xc0001000 ||
        mem->address > 0xf0000000 - 0x201000 || mem->address % 4096) goto fail;
    snprintf(path, sizeof(path), "%s/dev", root);
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) goto fail;
    ssize_t n = read(fd, buf, sizeof(buf)-1); close(fd);
    if (n <= 0 || sscanf(buf, "%u:%u", &major_number, &minor_number) != 2) goto fail;
    mem->fd = open("/dev/qcom_rmtfs_mem1", O_RDWR | O_NOFOLLOW | O_CLOEXEC);
    if (mem->fd < 0 || fstat(mem->fd, &st) || !S_ISCHR(st.st_mode) ||
        major(st.st_rdev) != major_number || minor(st.st_rdev) != minor_number) goto fail;
    printf("[RMTFS MEM] client=1 address=0x%llx size=0x%llx\n",
           (unsigned long long)mem->address, (unsigned long long)mem->size);
    return mem;
fail:
    if (mem->fd >= 0) close(mem->fd);
    free(mem); fputs("RMTFS memory validation failed\n", stderr); return NULL;
}
int64_t rmtfs_mem_alloc(struct rmtfs_mem *mem, size_t size)
{ return mem && size > 0 && size <= mem->size ? (int64_t)mem->address : -EINVAL; }
void rmtfs_mem_free(struct rmtfs_mem *mem) { (void)mem; }
static bool in_range(const struct rmtfs_mem *mem, uint64_t addr, ssize_t size)
{
    return mem && size >= 0 && addr >= mem->address && addr - mem->address <= mem->size &&
           (uint64_t)size <= mem->size - (addr - mem->address);
}
ssize_t rmtfs_mem_read(struct rmtfs_mem *mem, unsigned long addr, void *buf, ssize_t size)
{
    if (!in_range(mem, addr, size)) return -EINVAL;
    return pread(mem->fd, buf, size, (off_t)(addr - mem->address));
}
ssize_t rmtfs_mem_write(struct rmtfs_mem *mem, unsigned long addr, const void *buf, ssize_t size)
{
    if (!in_range(mem, addr, size)) return -EINVAL;
    return pwrite(mem->fd, buf, size, (off_t)(addr - mem->address));
}
void rmtfs_mem_close(struct rmtfs_mem *mem)
{ if (mem) { close(mem->fd); free(mem); } }
