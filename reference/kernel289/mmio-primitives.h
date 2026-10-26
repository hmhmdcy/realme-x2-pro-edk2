/* SPDX-License-Identifier: GPL-2.0-only */
/* Development-only readback: caller owns the live V4L2 stream throughout. */
static uint32_t mmio_read(volatile uint32_t *base, unsigned offset)
{
 uint32_t value=base[offset/4];__sync_synchronize();return value;
}
static void mmio_write(volatile uint32_t *base,unsigned offset,uint32_t value)
{
 __sync_synchronize();base[offset/4]=value;__sync_synchronize();
}
static int read_file(const char *path,unsigned char *data,size_t capacity)
{
 int fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)return -1;
 ssize_t n=read(fd,data,capacity);int saved=errno;close(fd);errno=saved;
 return n<0?-1:(int)n;
}
static uint64_t be64(const unsigned char *p)
{
 uint64_t value=0;for(unsigned i=0;i<8;i++)value=(value<<8)|p[i];return value;
}
