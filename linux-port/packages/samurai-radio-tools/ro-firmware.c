// SPDX-License-Identifier: BSD-3-Clause
// Open a firmware path beneath an explicit root without following symlinks.
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int samurai_ro_firmware_open(const char *root, const char *relative)
{
    char path[PATH_MAX], *component, *next, *save;
    int dir, fd = -1, saved_errno;

    if (!root || root[0] != '/' || !relative || !relative[0] ||
        relative[0] == '/' || strlen(relative) >= sizeof(path)) {
        errno = EACCES;
        return -1;
    }
    strcpy(path, relative);
    dir = open(root, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (dir < 0)
        return -1;
    component = strtok_r(path, "/", &save);
    while (component) {
        next = strtok_r(NULL, "/", &save);
        if (!strcmp(component, ".") || !strcmp(component, "..")) {
            errno = EACCES;
            break;
        }
        fd = openat(dir, component, O_RDONLY | O_CLOEXEC | O_NOFOLLOW |
                    (next ? O_DIRECTORY : 0));
        if (fd < 0)
            break;
        if (!next) {
            close(dir);
            return fd;
        }
        close(dir);
        dir = fd;
        fd = -1;
        component = next;
    }
    saved_errno = errno;
    close(dir);
    errno = saved_errno;
    return -1;
}
