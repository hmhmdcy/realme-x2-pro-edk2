#define _GNU_SOURCE
#include <sys/stat.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
extern int translate_open(const char *, int);
int main(void)
{
    char root[] = "/tmp/k91-tftp-test-XXXXXX", path[256], got[8] = {0};
    const char *const aliases[] = {"/readonly/firmware/image/fixture", "/readonly/vendor/firmware/fixture", "/readonly/vendor/firmware_mnt/image/fixture", "/readonly/firmware/modem_pr/fixture"};
    assert(mkdtemp(root)); assert(!setenv("SAMURAI_TFTP_FIRMWARE_ROOT", root, 1));
    snprintf(path, sizeof(path), "%s/fixture", root);
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600); assert(fd >= 0);
    assert(write(fd, "FW", 2) == 2); close(fd);
    for (unsigned i = 0; i < 4; i++) {
        fd = translate_open(aliases[i], O_RDONLY); assert(fd >= 0);
        assert(read(fd, got, 2) == 2 && !memcmp(got, "FW", 2)); close(fd);
        assert(translate_open(aliases[i], O_WRONLY | O_CREAT) < 0);
    }
    assert(translate_open("/readwrite/server_check.txt", O_RDONLY) < 0);
    fd = translate_open("/readwrite/server_check.txt", O_WRONLY | O_CREAT); assert(fd >= 0);
    assert(write(fd, "RAM", 3) == 3);
    char proc[64], target[128] = {0};
    snprintf(proc, sizeof(proc), "/proc/self/fd/%d", fd);
    assert(readlink(proc, target, sizeof(target)-1) > 0 && strstr(target, "memfd:samurai-tftp-server-check"));
    close(fd);
    fd = translate_open("/readwrite/server_check.txt", O_RDONLY); assert(fd >= 0);
    assert(read(fd, got, 3) == 3 && !memcmp(got, "RAM", 3)); close(fd);
    assert(translate_open("/readwrite/arbitrary", O_WRONLY | O_CREAT) < 0);
    assert(translate_open("/readwrite/../server_check.txt", O_WRONLY | O_CREAT) < 0);
    assert(translate_open("/dev/sdf4", O_WRONLY | O_CREAT) < 0);
    assert(translate_open("/readonly/firmware/image/../fixture", O_RDONLY) < 0);
    snprintf(path, sizeof(path), "%s/link", root); assert(!symlink("fixture", path));
    assert(translate_open("/readonly/firmware/image/link", O_RDONLY) < 0); assert(!unlink(path));
    snprintf(path, sizeof(path), "%s/fixture", root);
    fd = open(path, O_RDONLY); assert(fd >= 0);
    assert(read(fd, got, 2) == 2 && !memcmp(got, "FW", 2)); close(fd);
    assert(!unlink(path)); assert(!rmdir(root));
    puts("PASS: sole WRQ target is memfd, readback works, firmware unchanged, other writes/traversal/symlinks denied");
    return 0;
}
