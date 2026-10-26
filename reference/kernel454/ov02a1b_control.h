/* SPDX-License-Identifier: GPL-2.0-only */
/* Sensor command packing only. No clocks, GPIOs, I/O or tuning coefficients. */
#ifndef OV02A1B_CONTROL_H
#define OV02A1B_CONTROL_H

#define OV02A1B_FRAME_BASE 1224U
#define OV02A1B_CONTROL_WRITES 7U

/* The caller validates its mode-specific exposure and gain policy. All writes
 * are in page 1 and become effective at the final apply command. This is not
 * the unrelated mode descriptor's placeholder group-hold register list. */
static inline int ov02a1b_pack_controls(unsigned int exposure,
				      unsigned int frame_length,
				      unsigned int gain,
				      unsigned char output[OV02A1B_CONTROL_WRITES][2])
{
	unsigned int blanking;

	if (!output || frame_length < OV02A1B_FRAME_BASE ||
	    frame_length > 65535U || !exposure || exposure > 65535U ||
	    gain < 16U || gain > 248U)
		return -1;
	blanking = frame_length - OV02A1B_FRAME_BASE;
	output[0][0] = 0xfd; output[0][1] = 1;
	output[1][0] = 0x05; output[1][1] = blanking >> 8;
	output[2][0] = 0x06; output[2][1] = blanking;
	output[3][0] = 0x03; output[3][1] = exposure >> 8;
	output[4][0] = 0x04; output[4][1] = exposure;
	output[5][0] = 0x24; output[5][1] = gain;
	output[6][0] = 0x01; output[6][1] = 1;
	return 0;
}

#endif
