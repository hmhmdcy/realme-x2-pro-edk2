/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <string.h>
#include "ov02a1b_control.h"

int main(void)
{
	unsigned int exposure, frame_length, gain;
	unsigned char output[OV02A1B_CONTROL_WRITES][2];
	unsigned int i;
	int result;

	while (scanf("%u %u %u", &exposure, &frame_length, &gain) == 3) {
		memset(output, 0xa5, sizeof(output));
		result = ov02a1b_pack_controls(exposure, frame_length, gain, output);
		printf("%d ", result);
		for (i = 0; i < sizeof(output); ++i)
			printf("%02x", ((unsigned char *)output)[i]);
		putchar('\n');
	}
	memset(output, 0xa5, sizeof(output));
	if (ov02a1b_pack_controls(1, 1738, 16, NULL) != -1)
		return 1;
	return 0;
}
