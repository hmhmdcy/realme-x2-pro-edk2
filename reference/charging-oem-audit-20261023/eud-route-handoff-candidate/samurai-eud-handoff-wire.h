/* SPDX-License-Identifier: (GPL-2.0-only OR BSD-2-Clause) */
#ifndef SAMURAI_EUD_HANDOFF_WIRE_H
#define SAMURAI_EUD_HANDOFF_WIRE_H

/* Internal little-endian ARM64 firmware/kernel channel, not a route lease.
 * A new EFI-reserved page is published under this GUID before LoadImage.
 * No byte in the existing best-effort log ring is reused for authorization.
 */
#define SAMURAI_EUD_GUID_WORDS \
	0x346dfd34, 0x196b, 0x4ea6, 0x93, 0x9a, 0xf3, 0xfb, 0xff, 0x5d, 0xa1, 0x53
#define SAMURAI_EUD_HANDOFF_MAGIC 0x4f445545U
#define SAMURAI_EUD_HANDOFF_VERSION 1U
#define SAMURAI_EUD_HANDOFF_CSR 0x088e1014ULL
#define SAMURAI_EUD_FLAG_ATTEMPTED 1U
#define SAMURAI_EUD_FLAG_DIRECT_FIFO_RETIRED 2U
#define SAMURAI_EUD_FLAG_WRITE_ATTEMPTED 4U

struct samurai_eud_handoff {
	unsigned int commit, version, bytes, flags;
	unsigned int arm_csr, before_csr, after_csr, reserved0;
	unsigned long long status, csr_address, table_address;
	unsigned int checksum, reserved1;
};

static inline unsigned int
samurai_eud_handoff_crc(const struct samurai_eud_handoff *record)
{
	const unsigned char *bytes = (const unsigned char *)record;
	unsigned int crc = ~0U, i, bit;

	/* Commit is stored last; checksum itself is outside the checksum. */
	for (i = 4; i < sizeof(*record); i++) {
		if (i >= 56 && i < 60)
			continue;
		crc ^= bytes[i];
		for (bit = 0; bit < 8; bit++)
			crc = (crc >> 1) ^ ((crc & 1U) ? 0xedb88320U : 0U);
	}
	return ~crc;
}

static inline int samurai_eud_handoff_word_known(unsigned int value)
{
	return value == 0U || value == 1U || value == 0x01010101U;
}

static inline int samurai_eud_handoff_valid(
		const struct samurai_eud_handoff *record, unsigned long long physical)
{
	unsigned int expected_flags = SAMURAI_EUD_FLAG_ATTEMPTED |
		SAMURAI_EUD_FLAG_DIRECT_FIFO_RETIRED;

	if (record->before_csr)
		expected_flags |= SAMURAI_EUD_FLAG_WRITE_ATTEMPTED;
	return sizeof(*record) == 64 && physical && !(physical & 4095ULL) &&
		record->commit == SAMURAI_EUD_HANDOFF_MAGIC &&
		record->version == SAMURAI_EUD_HANDOFF_VERSION && record->bytes == 64 &&
		record->flags == expected_flags && !record->reserved0 && !record->reserved1 &&
		samurai_eud_handoff_word_known(record->arm_csr) &&
		samurai_eud_handoff_word_known(record->before_csr) &&
		!record->after_csr && !record->status &&
		record->csr_address == SAMURAI_EUD_HANDOFF_CSR &&
		record->table_address == physical && record->checksum == samurai_eud_handoff_crc(record);
}
#endif
