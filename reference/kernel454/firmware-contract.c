/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ov02a1b_firmware.h"

static unsigned int rejected;
static void reject(const unsigned char *bytes, unsigned long size)
{
	struct ov02a1b_firmware output, original;
	memset(&output, 0xa5, sizeof(output));
	memcpy(&original, &output, sizeof(original));
	if (ov02a1b_parse_firmware(bytes, size, &output) != -1 ||
	    memcmp(&output, &original, sizeof(output)))
		abort();
	++rejected;
}

int main(int argc, char **argv)
{
	unsigned char *data, *bad;
	unsigned long size, i, offset;
	struct ov02a1b_firmware output;
	const unsigned int counts[4] = { 88, 1, 2, 2 };
	FILE *file;

	if (argc != 2 || !(file = fopen(argv[1], "rb")))
		return 1;
	if (fseek(file, 0, SEEK_END) || ftell(file) != 760)
		return 2;
	size = 760;
	rewind(file);
	data = malloc(size + 1); bad = malloc(size + 1);
	if (!data || !bad || fread(data, 1, size, file) != size)
		return 3;
	fclose(file);
	if (ov02a1b_parse_firmware(data, size, &output))
		return 4;
	offset = 16;
	for (i = 0; i < 4; ++i) {
		if (output.count[i] != counts[i] || output.table[i] != data + offset)
			return 5;
		offset += counts[i] * 8;
	}
	for (i = 0; i < size; ++i)
		reject(data, i);
	for (i = 0; i < 16; ++i) {
		memcpy(bad, data, size); bad[i] ^= 1;
		reject(bad, size);
	}
	for (offset = 16; offset < size; offset += 8) {
		memcpy(bad, data, size); bad[offset + 2] = 1;
		reject(bad, size);
		memcpy(bad, data, size); memset(bad + offset + 4, 0xff, 4);
		reject(bad, size);
	}
	data[size] = 0;
	reject(data, size + 1);
	reject(NULL, size);
	if (ov02a1b_parse_firmware(data, size, NULL) != -1)
		return 6;
	printf("{\"valid_firmware\":1,\"rejections_with_unchanged_output\":%u,\"null_output_rejected\":true}\n", rejected);
	free(bad); free(data);
	return 0;
}
