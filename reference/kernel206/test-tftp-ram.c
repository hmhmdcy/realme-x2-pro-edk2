#define _GNU_SOURCE
#include <sys/stat.h>
#include <sys/vfs.h>
#include <linux/magic.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern int translate_open(const char *, int);
static void denied(const char *p, int flags) { int fd = translate_open(p, flags); if (fd >= 0) fprintf(stderr, "Unexpected open: %s flags=%d\n", p, flags); assert(fd < 0); }
int main(int argc, char **argv)
{
    char ram[] = "/dev/shm/samurai-tftp-206-XXXXXX";
    char firmware[] = "/tmp/samurai-fw-206-XXXXXX";
    char path[1024], outside[1024], nonram[PATH_MAX], buf[32] = {0};
    const int wr = O_WRONLY | O_CREAT | O_TRUNC;
    struct statfs fs;
    assert(mkdtemp(ram) && mkdtemp(firmware));
    assert(argc == 2 && snprintf(nonram, sizeof(nonram), "%s/nonram-XXXXXX", argv[1]) < (int)sizeof(nonram));
    assert(mkdtemp(nonram));
    assert(!statfs(nonram, &fs) && fs.f_type != TMPFS_MAGIC);
    assert(!chmod(ram, 0700));
    assert(!statfs(ram, &fs) && fs.f_type == TMPFS_MAGIC);
    assert(!setenv("SAMURAI_TFTP_RW_ROOT", ram, 1));
    assert(!setenv("SAMURAI_TFTP_FIRMWARE_ROOT", firmware, 1));
    snprintf(outside, sizeof(outside), "%s/fixture", firmware);
    int fd = open(outside, O_WRONLY | O_CREAT | O_EXCL, 0600);
    assert(fd >= 0 && write(fd, "firmware", 8) == 8); close(fd);

    fd = translate_open("/readwrite/mcfg.tmp", wr);
    assert(fd >= 0 && write(fd, "configuration", 13) == 13); close(fd);
    fd = translate_open("/readwrite/mcfg.tmp", O_RDONLY);
    assert(fd >= 0 && read(fd, buf, sizeof(buf)) == 13 && !memcmp(buf, "configuration", 13)); close(fd);
    fd = translate_open("/readwrite/mcfg.tmp", wr);
    assert(fd >= 0 && write(fd, "new", 3) == 3); close(fd);
    fd = translate_open("/readwrite/mcfg.tmp", O_RDONLY);
    assert(fd >= 0 && read(fd, buf, sizeof(buf)) == 3); close(fd);
    fd = translate_open("/readwrite/mcfg.tmp", O_WRONLY | O_CREAT);
    assert(fd >= 0 && lseek(fd, 1, SEEK_SET) == 1 && write(fd, "X", 1) == 1); close(fd);
    fd = translate_open("/readwrite/mcfg.tmp", O_RDONLY);
    assert(fd >= 0 && read(fd, buf, sizeof(buf)) == 3 && !memcmp(buf, "nXw", 3)); close(fd);
    fd = translate_open("/readwrite/ota_firewall/ruleset", wr);
    assert(fd >= 0 && write(fd, "rules", 5) == 5); close(fd);
    fd = translate_open("/readwrite/ota_firewall/ruleset", O_RDONLY);
    assert(fd >= 0 && read(fd, buf, sizeof(buf)) == 5); close(fd);
    errno = 0; denied("/readwrite/not-created", O_RDONLY); assert(errno == ENOENT);

    const char *bad[] = {"/readwrite/../fixture", "/readwrite/a/../../fixture", "/readwrite/a/./fixture", "/readwrite//fixture", "/readwrite/a/", "/readwrite/a\\fixture", "/dev/sda2", "/readonly/firmware/image/fixture"};
    for (unsigned i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) denied(bad[i], wr);
    denied("/readwrite/mcfg.tmp", O_RDWR);
    denied("/readwrite/", wr);
    char too_deep[128] = "/readwrite/";
    for (int i = 0; i < 17; i++) strcat(too_deep, "a/");
    strcat(too_deep, "f"); denied(too_deep, wr);

    snprintf(path, sizeof(path), "%s/link", ram); assert(!symlink(outside, path));
    denied("/readwrite/link", O_RDONLY); denied("/readwrite/link", wr); assert(!unlink(path));
    snprintf(path, sizeof(path), "%s/dir-link", ram); assert(!symlink(firmware, path));
    denied("/readwrite/dir-link/fixture", O_RDONLY); denied("/readwrite/dir-link/fixture", wr); assert(!unlink(path));
    snprintf(path, sizeof(path), "%s/fifo", ram); assert(!mkfifo(path, 0600));
    denied("/readwrite/fifo", O_RDONLY); assert(!unlink(path));
    snprintf(path, sizeof(path), "%s/hardlink", ram);
    char existing[1024]; snprintf(existing, sizeof(existing), "%s/mcfg.tmp", ram);
    assert(!link(existing, path)); denied("/readwrite/hardlink", O_RDONLY); denied("/readwrite/hardlink", wr);
    fd = open(existing, O_RDONLY); assert(fd >= 0 && read(fd, buf, sizeof(buf)) == 3 && !memcmp(buf, "nXw", 3)); close(fd);
    assert(!unlink(path));
    snprintf(path, sizeof(path), "%s/oversize", ram);
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    assert(fd >= 0 && !ftruncate(fd, 8 * 1024 * 1024 + 1)); close(fd);
    denied("/readwrite/oversize", O_RDONLY); assert(!unlink(path));
    assert(!chmod(ram, 0755)); denied("/readwrite/mcfg.tmp", O_RDONLY); assert(!chmod(ram, 0700));
    assert(!setenv("SAMURAI_TFTP_RW_ROOT", nonram, 1)); denied("/readwrite/mcfg.tmp", wr); assert(!rmdir(nonram));
    assert(!setenv("SAMURAI_TFTP_RW_ROOT", ram, 1));
    fd = translate_open("/readonly/firmware/image/fixture", O_RDONLY);
    assert(fd >= 0 && read(fd, buf, sizeof(buf)) == 8 && !memcmp(buf, "firmware", 8)); close(fd);
    fd = open(outside, O_RDONLY); assert(fd >= 0 && read(fd, buf, sizeof(buf)) == 8 && !memcmp(buf, "firmware", 8)); close(fd);
    assert(!unlink(existing));
    snprintf(path, sizeof(path), "%s/ota_firewall/ruleset", ram); assert(!unlink(path));
    snprintf(path, sizeof(path), "%s/ota_firewall", ram); assert(!rmdir(path));
    assert(!rmdir(ram)); assert(!unlink(outside)); assert(!rmdir(firmware));
    puts("PASS: modem work-file read/write/truncate/seek, missing-file errno, tmpfs confinement, firmware preservation and path/type limits");
    return 0;
}
