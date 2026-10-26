/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef OV02A1B_FIRMWARE_H
#define OV02A1B_FIRMWARE_H

struct ov02a1b_firmware {
	const unsigned char *table[4];
	unsigned int count[4];
};

static inline unsigned int ov02a1b_fw_u32(const unsigned char *p)
{
	return (unsigned int)p[0] | ((unsigned int)p[1] << 8) |
	       ((unsigned int)p[2] << 16) | ((unsigned int)p[3] << 24);
}

/* OV2B v1, four original ordered tables, 8-byte records. The backing firmware
 * must remain alive while the caller uses these views. Validate before I/O. */
static inline int ov02a1b_parse_firmware(const unsigned char *data,
				       unsigned long size,
				       struct ov02a1b_firmware *output)
{
	const unsigned int expected[4] = { 88, 1, 2, 2 };
	unsigned long offset = 16;
	unsigned int i, j, count;

	if (!data || !output || size < 16 || data[0] != 'O' ||
	    data[1] != 'V' || data[2] != '2' || data[3] != 'B' ||
	    data[4] != 1 || data[5] != 4 || data[6] || data[7])
		return -1;
	for (i = 0; i < 4; ++i) {
		count = data[8 + 2 * i] | (data[9 + 2 * i] << 8);
		if (count != expected[i] || offset > size ||
		    count > (size - offset) / 8)
			return -1;
		for (j = 0; j < count; ++j) {
			const unsigned char *record = data + offset + j * 8;

			if (record[2] || record[3] ||
			    ov02a1b_fw_u32(record + 4) > 1000000U)
				return -1;
		}
		offset += count * 8;
	}
	if (offset != size)
		return -1;
	offset = 16;
	for (i = 0; i < 4; ++i) {
		output->table[i] = data + offset;
		output->count[i] = expected[i];
		offset += expected[i] * 8;
	}
	return 0;
}

#endif
