// SPDX-License-Identifier: GPL-2.0-only
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

int main(int argc, char **argv)
{
	uint64_t base;
	size_t length;
	long page;
	size_t map_length;
	void *map;
	int fd;
	size_t off;

	if (argc != 3) {
		fprintf(stderr, "usage: %s <phys> <length>\n", argv[0]);
		return 2;
	}

	base = strtoull(argv[1], NULL, 0);
	length = strtoull(argv[2], NULL, 0);
	page = sysconf(_SC_PAGESIZE);
	if (!length || page <= 0) {
		fprintf(stderr, "invalid length or page size\n");
		return 2;
	}

	fd = open("/dev/mem", O_RDONLY | O_SYNC);
	if (fd < 0) {
		perror("open /dev/mem");
		return 1;
	}

	map_length = (length + (base & (page - 1)) + page - 1) &
		     ~((size_t)page - 1);
	map = mmap(NULL, map_length, PROT_READ, MAP_SHARED, fd,
		   base & ~((uint64_t)page - 1));
	if (map == MAP_FAILED) {
		perror("mmap");
		close(fd);
		return 1;
	}

	for (off = 0; off < length; off += sizeof(uint32_t)) {
		volatile uint32_t *reg = (volatile uint32_t *)
			((char *)map + (base & (page - 1)) + off);

		printf("%#010llx %#010x\n",
		       (unsigned long long)(base + off), *reg);
	}

	munmap(map, map_length);
	close(fd);
	return 0;
}
