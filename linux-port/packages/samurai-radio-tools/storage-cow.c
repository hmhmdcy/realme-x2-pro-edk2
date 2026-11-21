/* RMTFS storage backend: fixed regular-file snapshots, RAM writes only. */
#define _GNU_SOURCE
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "rmtfs.h"

#define LIMIT (16U * 1024U * 1024U)
#define HANDLES 10
struct image { const char *name; unsigned char *data; size_t length; };
static struct image images[] = {
    { "modem_fs1", NULL, 0 }, { "modem_fs2", NULL, 0 },
    { "modem_fsc", NULL, 0 }, { "modem_fsg", NULL, 0 },
    { "oem_stanvbk", NULL, 0 }, { "oem_dycnvbk", NULL, 0 }
};
struct rmtfd { struct image *image; unsigned node; unsigned id; bool active; };
static struct rmtfd handles[HANDLES];
static bool initialized;

int storage_init(const char *root, bool read_only, bool use_partitions)
{
    int dir;
    if (!root || !read_only || use_partitions || initialized) return -EINVAL;
    dir = open(root, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (dir < 0) return -errno;
    for (size_t i = 0; i < sizeof(images)/sizeof(images[0]); i++) {
        struct stat st;
        size_t got = 0;
        int fd = openat(dir, images[i].name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
        if (fd < 0 && errno == ENOENT && i >= 4) continue;
        if (fd < 0) { close(dir); storage_exit(); return -EINVAL; }
        if (fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_size <= 0 ||
            st.st_size > LIMIT || st.st_size % 512) {
            close(fd); close(dir); storage_exit(); return -EINVAL;
        }
        images[i].data = calloc(1, LIMIT);
        if (!images[i].data) { close(fd); close(dir); storage_exit(); return -ENOMEM; }
        images[i].length = (size_t)st.st_size;
        while (got < images[i].length) {
            ssize_t n = read(fd, images[i].data + got, images[i].length - got);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) { close(fd); close(dir); storage_exit(); return -EIO; }
            got += (size_t)n;
        }
        close(fd);
        printf("[COW] loaded %s bytes=%zu\n", images[i].name, images[i].length);
    }
    close(dir);
    for (unsigned i = 0; i < HANDLES; i++) handles[i].id = i;
    initialized = true;
    return 0;
}

static int path_index(const char *path)
{
    static const char *const paths[] = {
        "/boot/modem_fs1", "/boot/modem_fs2", "/boot/modem_fsc", "/boot/modem_fsg",
        "/oem/nvbk/static", "/oem/nvbk/dynamic", "/oppo/oem_partion"
    };
    if (!path || strnlen(path, 256) == 256) return -1;
    for (unsigned i = 0; i < sizeof(paths)/sizeof(paths[0]); i++)
        if (!strcmp(path, paths[i])) return i == 6 ? 4 : (int)i;
    return -1;
}

struct rmtfd *storage_open(unsigned node, const char *path, const char *suffix)
{
    int ix = path_index(path);
    if (!initialized || ix < 0 || !images[ix].data || (suffix && *suffix)) return NULL;
    for (unsigned i = 0; i < HANDLES; i++)
        if (handles[i].active && handles[i].node == node && handles[i].image == &images[ix])
            return &handles[i];
    for (unsigned i = 0; i < HANDLES; i++) {
        if (!handles[i].active) {
            handles[i].image = &images[ix]; handles[i].node = node;
            handles[i].active = true; return &handles[i];
        }
    }
    return NULL;
}

struct rmtfd *storage_get(unsigned node, int id)
{
    if (id < 0 || id >= HANDLES || !handles[id].active || handles[id].node != node) return NULL;
    return &handles[id];
}
void storage_close(struct rmtfd *fd) { if (fd) fd->active = false; }
int storage_get_caller_id(const struct rmtfd *fd) { return fd ? (int)fd->id : -1; }
int storage_get_error(const struct rmtfd *fd) { return !fd || !fd->active; }
int storage_sync(struct rmtfd *fd) { return fd && fd->active ? 0 : -EINVAL; }
void storage_exit(void)
{
    for (size_t i = 0; i < sizeof(images)/sizeof(images[0]); i++) {
        free(images[i].data); images[i].data = NULL; images[i].length = 0;
    }
    memset(handles, 0, sizeof(handles)); initialized = false;
}
static bool in_range(const struct rmtfd *fd, size_t count, off_t offset)
{
    return fd && fd->active && offset >= 0 && (uint64_t)offset <= LIMIT &&
           count <= LIMIT - (uint64_t)offset;
}
ssize_t storage_pread(const struct rmtfd *fd, void *buf, size_t count, off_t offset)
{
    if (!in_range(fd, count, offset)) return -EINVAL;
    memcpy(buf, fd->image->data + offset, count);
    return (ssize_t)count;
}
ssize_t storage_pwrite(struct rmtfd *fd, const void *buf, size_t count, off_t offset)
{
    if (!in_range(fd, count, offset)) return -EINVAL;
    memcpy(fd->image->data + offset, buf, count);
    if ((uint64_t)offset + count > fd->image->length) fd->image->length = offset + count;
    return (ssize_t)count;
}
