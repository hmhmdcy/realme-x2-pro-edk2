// SPDX-License-Identifier: BSD-3-Clause
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <linux/qrtr.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

extern int translate_open(const char *path, int flags);
enum tftp_error { TFTP_ERROR_EACCESS = 2 };
static int error_count;
static void tftp_send_error_to(struct sockaddr_qrtr *sq, enum tftp_error code, const char *msg)
{
    (void)sq;
    if (code != TFTP_ERROR_EACCESS || !strstr(msg, "read-only")) exit(1);
    ++error_count;
}
#define log_err(...) do { } while (0)
#include "wrq-function.inc"

static void require(int truth, const char *message)
{
    if (!truth) { fprintf(stderr, "FAIL %s\n", message); exit(1); }
}
int main(void)
{
    char root[] = "/tmp/samurai-ro-tftp-XXXXXX", path[512], ch;
    const char *aliases[] = { "/readonly/firmware/image/fixture.bin",
                             "/readonly/vendor/firmware/fixture.bin",
                             "/readonly/vendor/firmware_mnt/image/fixture.bin" };
    struct sockaddr_qrtr peer = { 0 };
    require(mkdtemp(root) != NULL, "fixture root");
    require(setenv("SAMURAI_TFTP_FIRMWARE_ROOT", root, 1) == 0, "set explicit root");
    snprintf(path, sizeof(path), "%s/fixture.bin", root);
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    require(fd >= 0 && write(fd, "Q", 1) == 1, "fixture data"); close(fd);
    for (size_t i = 0; i < sizeof(aliases) / sizeof(aliases[0]); ++i) {
        fd = translate_open(aliases[i], O_RDONLY);
        require(fd >= 0 && read(fd, &ch, 1) == 1 && ch == 'Q', "valid RRQ reads fixture");
        close(fd);
    }
    require(translate_open(aliases[0], O_WRONLY | O_CREAT) < 0 && errno == EACCES, "write flags denied");
    require(translate_open("/readwrite/new-file", O_RDONLY) < 0 && errno == EACCES, "readwrite namespace denied");
    require(translate_open("/readonly/firmware/image/../fixture.bin", O_RDONLY) < 0, "parent traversal denied");
    require(translate_open("/readonly/firmware/image//etc/passwd", O_RDONLY) < 0, "absolute suffix denied");
    snprintf(path, sizeof(path), "%s/link", root);
    require(symlink("/etc", path) == 0, "symlink fixture");
    require(translate_open("/readonly/firmware/image/link/passwd", O_RDONLY) < 0, "intermediate symlink denied");
    unlink(path);
    snprintf(path, sizeof(path), "%s/link", root);
    require(symlink("fixture.bin", path) == 0, "final symlink fixture");
    require(translate_open("/readonly/firmware/image/link", O_RDONLY) < 0, "final symlink denied");
    unlink(path);
    handle_wrq("\0\2/readwrite/new-file\0octet\0", 32, &peer);
    handle_wrq("\0\2", 2, &peer);
    require(error_count == 2, "actual WRQ handler sends access errors");
    snprintf(path, sizeof(path), "%s/new-file", root);
    require(access(path, F_OK) < 0, "no write-request file created");
    snprintf(path, sizeof(path), "%s/fixture.bin", root); unlink(path); rmdir(root);
    puts("PASS actual translator RRQ aliases and byte read; write flags/readwrite/traversal/symlinks denied; actual WRQ handler rejects; no target created");
    return 0;
}
