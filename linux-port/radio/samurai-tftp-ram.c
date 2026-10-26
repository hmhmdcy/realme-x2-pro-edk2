// SPDX-License-Identifier: BSD-3-Clause
// Modem work files live in a bounded tmpfs; firmware remains read-only.
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <sys/stat.h>
#include <sys/vfs.h>
#include <linux/magic.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define SAMURAI_TFTP_FILE_LIMIT (8U * 1024U * 1024U)
extern int samurai_ro_firmware_open(const char *root, const char *relative);

static int cache_root(void)
{
    const char *root = getenv("SAMURAI_TFTP_RW_ROOT");
    struct stat st;
    struct statfs fs;
    int fd, saved;
    if (!root)
        root = "/run/samurai-wifi/tftp-rw";
    if (root[0] != '/') {
        errno = EACCES;
        return -1;
    }
    fd = open(root, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0)
        return -1;
    if (fstat(fd, &st) < 0 || fstatfs(fd, &fs) < 0)
        goto fail;
    if (fs.f_type != TMPFS_MAGIC || st.st_uid != geteuid() || (st.st_mode & 077)) {
        errno = EACCES;
        goto fail;
    }
    return fd;
fail:
    saved = errno;
    close(fd);
    errno = saved;
    return -1;
}

static int cache_open(const char *relative, int flags)
{
    char path[PATH_MAX], *component, *next, *save;
    struct stat st;
    unsigned int depth = 0;
    int dir, fd = -1, saved;
    int writing = flags == (O_WRONLY | O_CREAT) || flags == (O_WRONLY | O_CREAT | O_TRUNC);
    if (!relative[0] || relative[0] == '/' || strlen(relative) >= sizeof(path) ||
        strstr(relative, "//") || relative[strlen(relative) - 1] == '/' ||
        strchr(relative, '\\') || (!writing && flags != O_RDONLY)) {
        errno = EACCES;
        return -1;
    }
    /* Reject invalid components before creating any directories. */
    strcpy(path, relative);
    for (component = strtok_r(path, "/", &save); component; component = strtok_r(NULL, "/", &save)) {
        if (!strcmp(component, ".") || !strcmp(component, "..") ||
            strlen(component) > NAME_MAX || ++depth > 16) {
            errno = EACCES;
            return -1;
        }
    }
    dir = cache_root();
    if (dir < 0)
        return -1;
    strcpy(path, relative);
    component = strtok_r(path, "/", &save);
    while (component) {
        next = strtok_r(NULL, "/", &save);
        if (next) {
            if (writing && mkdirat(dir, component, 0700) < 0 && errno != EEXIST)
                break;
            fd = openat(dir, component, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
        } else {
            /* Validate an existing inode before a requested truncation. */
            fd = openat(dir, component, (flags & ~O_TRUNC) | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK, 0600);
        }
        if (fd < 0)
            break;
        if (!next) {
            if (fstat(fd, &st) < 0)
                break;
            if (!S_ISREG(st.st_mode) || st.st_nlink != 1 || st.st_size > SAMURAI_TFTP_FILE_LIMIT) {
                errno = EACCES;
                break;
            }
            if ((flags & O_TRUNC) && ftruncate(fd, 0) < 0)
                break;
            close(dir);
            return fd;
        }
        close(dir);
        dir = fd;
        fd = -1;
        component = next;
    }
    saved = errno;
    if (fd >= 0)
        close(fd);
    close(dir);
    errno = saved;
    return -1;
}

int translate_open(const char *path, int flags)
{
    static const char *const prefixes[] = {
        "/readonly/firmware/image/", "/readonly/firmware/modem_pr/",
        "/readonly/vendor/firmware/", "/readonly/vendor/firmware_mnt/image/"
    };
    const char *root;
    if (!path || strchr(path, '\\')) {
        errno = EACCES;
        return -1;
    }
    if (!strncmp(path, "/readwrite/", 11))
        return cache_open(path + 11, flags);
    if (flags != O_RDONLY) {
        errno = EACCES;
        return -1;
    }
    root = getenv("SAMURAI_TFTP_FIRMWARE_ROOT");
    if (!root) {
        errno = EACCES;
        return -1;
    }
    for (size_t i = 0; i < sizeof(prefixes) / sizeof(prefixes[0]); i++) {
        size_t n = strlen(prefixes[i]);
        if (!strncmp(path, prefixes[i], n))
            return samurai_ro_firmware_open(root, path + n);
    }
    errno = EACCES;
    return -1;
}
