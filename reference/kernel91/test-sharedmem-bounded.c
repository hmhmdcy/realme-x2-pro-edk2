#include <assert.h>
#include "sharedmem-bounded.c"
int main(void)
{
    struct rmtfs_mem mem = { .address = 0xc1001000, .size = 0x200000, .fd = -1 };
    char buf[512];
    assert(in_range(&mem, mem.address, 512));
    assert(in_range(&mem, mem.address + mem.size - 512, 512));
    assert(!in_range(&mem, mem.address - 1, 512));
    assert(!in_range(&mem, mem.address + mem.size - 511, 512));
    assert(!in_range(&mem, UINT64_MAX, 512));
    assert(!in_range(&mem, mem.address, -1));
    assert(!in_range(&mem, mem.address, INT64_MAX));
    assert(rmtfs_mem_alloc(&mem, mem.size) == (int64_t)mem.address);
    assert(rmtfs_mem_alloc(&mem, mem.size + 1) == -EINVAL);
    assert(rmtfs_mem_alloc(&mem, 0) == -EINVAL);
    assert(rmtfs_mem_read(&mem, mem.address - 1, buf, 512) == -EINVAL);
    assert(rmtfs_mem_write(&mem, UINT64_MAX, buf, 512) == -EINVAL);
    puts("PASS: shared-memory range boundaries and overflow rejection");
    return 0;
}
