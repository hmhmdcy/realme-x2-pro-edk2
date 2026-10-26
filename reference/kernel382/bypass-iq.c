// SPDX-License-Identifier: GPL-2.0-only
/* SM8150 8-bit linear YUV: keep IQ modules disabled, while retaining the
 * mandatory ICA alignment and invalid-pixel interpolation defaults used by
 * the target HAL. IcaParameters occupies 192 bytes; each field is a u32.
 */
int camss_a5_ipe_encode_bypass_iq(void *buffer, u32 bytes)
{
	if (!buffer || bytes < CAMSS_A5_IPE_IQ_BYTES)
		return -EINVAL;
	memset(buffer, 0, CAMSS_A5_IPE_IQ_BYTES);
	put_unaligned_le32(1, buffer + 52);
	put_unaligned_le32(1, buffer + 68);
	put_unaligned_le32(1, buffer + 244);
	put_unaligned_le32(1, buffer + 260);
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_bypass_iq);
