#include <assert.h>
#include "storage-cow.c"

int main(void)
{
    char root[] = "/tmp/k91-cow-test-XXXXXX", path[256];
    unsigned char original[512], changed[512], got[512];
    const char *const names[] = {"modem_fs1", "modem_fs2", "modem_fsc", "modem_fsg"};
    struct rmtfd *handle;
    int fd;
    memset(original, 0x5a, sizeof(original)); memset(changed, 0xc3, sizeof(changed));
    assert(mkdtemp(root));
    for (unsigned i = 0; i < 4; i++) {
        snprintf(path, sizeof(path), "%s/%s", root, names[i]);
        fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600); assert(fd >= 0);
        assert(write(fd, original, sizeof(original)) == sizeof(original)); close(fd);
    }
    assert(storage_init(root, false, false) < 0);
    assert(storage_init(root, true, true) < 0);
    assert(storage_init(root, true, false) == 0);
    assert(!storage_open(0, "/boot/../modem_fs1", ""));
    assert(!storage_open(0, "/dev/sdf4", ""));
    assert(!storage_open(0, "/oem/nvbk/static", ""));
    handle = storage_open(0, "/boot/modem_fs1", ""); assert(handle);
    int id = storage_get_caller_id(handle);
    assert(storage_get(0, id) == handle);
    assert(!storage_get(1, id)); assert(!storage_get(0, -1)); assert(!storage_get(0, 10));
    assert(storage_pwrite(handle, changed, sizeof(changed), -1) == -EINVAL);
    assert(storage_pwrite(handle, changed, sizeof(changed), LIMIT - 511) == -EINVAL);
    assert(storage_pwrite(handle, changed, sizeof(changed), INT64_MAX) == -EINVAL);
    assert(storage_pwrite(handle, changed, sizeof(changed), 0) == sizeof(changed));
    assert(storage_sync(handle) == 0);
    storage_close(handle); assert(!storage_get(0, id));
    handle = storage_open(0, "/boot/modem_fs1", ""); assert(handle);
    assert(storage_pread(handle, got, sizeof(got), 0) == sizeof(got));
    assert(!memcmp(got, changed, sizeof(got)));
    assert(storage_pread(handle, got, sizeof(got), 1024) == sizeof(got));
    for (unsigned i = 0; i < sizeof(got); i++) assert(got[i] == 0);
    storage_exit();
    snprintf(path, sizeof(path), "%s/modem_fs1", root);
    fd = open(path, O_RDONLY); assert(fd >= 0);
    assert(read(fd, got, sizeof(got)) == sizeof(got)); close(fd);
    assert(!memcmp(got, original, sizeof(got)));
    assert(unlink(path) == 0); assert(symlink("modem_fs2", path) == 0);
    assert(storage_init(root, true, false) < 0);
    for (unsigned i = 0; i < 4; i++) {
        snprintf(path, sizeof(path), "%s/%s", root, names[i]); assert(unlink(path) == 0);
    }
    assert(rmdir(root) == 0);
    puts("PASS: RAM writes, close/reopen, original input unchanged, bounds, caller identity, symlink and path rejection");
    return 0;
}
