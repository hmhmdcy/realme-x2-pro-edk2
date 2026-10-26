/* Fixed TFTP write target backed by memfd. Firmware remains read-only. */
#define _GNU_SOURCE
#include <sys/mman.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
extern int samurai_ro_firmware_open(const char *root, const char *relative);
static int probe_fd = -1;

int translate_open(const char *path, int flags)
{
    static const char *const prefixes[] = {
        "/readonly/firmware/image/", "/readonly/firmware/modem_pr/",
        "/readonly/vendor/firmware/", "/readonly/vendor/firmware_mnt/image/"
    };
    if (!path || strstr(path, "..") || strchr(path, '\\')) { errno = EACCES; return -1; }
    if (!strcmp(path, "/readwrite/server_check.txt")) {
        char fd_path[64];
        if (flags != O_RDONLY && flags != (O_WRONLY | O_CREAT)) { errno = EACCES; return -1; }
        if (probe_fd < 0) {
            if (flags == O_RDONLY) { errno = ENOENT; return -1; }
            probe_fd = memfd_create("samurai-tftp-server-check", MFD_CLOEXEC);
            if (probe_fd < 0) return -1;
        }
        snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", probe_fd);
        return open(fd_path, (flags == O_RDONLY ? O_RDONLY : O_WRONLY) | O_CLOEXEC);
    }
    if (flags != O_RDONLY) { errno = EACCES; return -1; }
    const char *root = getenv("SAMURAI_TFTP_FIRMWARE_ROOT");
    if (!root) { errno = EACCES; return -1; }
    for (size_t i = 0; i < sizeof(prefixes)/sizeof(prefixes[0]); i++) {
        size_t n = strlen(prefixes[i]);
        if (!strncmp(path, prefixes[i], n)) return samurai_ro_firmware_open(root, path + n);
    }
    errno = EACCES; return -1;
}
