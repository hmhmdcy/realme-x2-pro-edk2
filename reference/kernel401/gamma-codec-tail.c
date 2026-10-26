int camss_a5_ipe_gamma_check(const struct camss_a5_ipe_gamma *gamma)
{
	u32 bank, i;

	if (!gamma)
		return -EINVAL;
	for (bank = 0; bank < 3; bank++)
		for (i = 0; i < 256; i++)
			if (gamma->base[bank][i] > 1023 ||
			    gamma->delta[bank][i] < -512 ||
			    gamma->delta[bank][i] > 511)
				return -ERANGE;
	return 0;
}

int camss_a5_ipe_encode_gamma_iq(void *destination, u32 bytes, u32 iq_iova,
			       const struct camss_a5_ipe_colour *colour,
			       const struct camss_a5_ipe_gamma *gamma)
{
	struct camss_a5_ipe_colour empty = {};
	u8 *output = destination;
	u8 *post;
	u32 count, bank, i;
	int ret;

	if (!output || bytes < CAMSS_A5_IPE_GAMMA_IQ_BYTES || !iq_iova ||
	    (iq_iova & 31) ||
	    (u64)iq_iova + CAMSS_A5_IPE_GAMMA_IQ_BYTES > (1ULL << 32))
		return -EINVAL;
	ret = camss_a5_ipe_gamma_check(gamma);
	if (ret)
		return ret;
	if (!colour)
		colour = &empty;
	ret = camss_a5_ipe_encode_colour_iq(output, bytes, iq_iova, colour);
	if (ret)
		return ret;
	memset(output + CAMSS_A5_IPE_COLOUR_IQ_BYTES, 0,
	       CAMSS_A5_IPE_GAMMA_IQ_BYTES - CAMSS_A5_IPE_COLOUR_IQ_BYTES);
	/* Make room for the third post descriptor. Commands remain contiguous;
	 * only command storage moves, never image data or an externally owned LUT.
	 */
	memmove(output + CAMSS_A5_IPE_GAMMA_CST_PACKET_OFFSET,
		output + CAMSS_A5_IPE_CST_PACKET_OFFSET, 140);
	memset(output + CAMSS_A5_IPE_CST_PACKET_OFFSET, 0, 32);
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CST)
		put_unaligned_le32(iq_iova + CAMSS_A5_IPE_GAMMA_CST_PACKET_OFFSET,
				   output + CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET +
				   CAMSS_A5_IPE_COLOUR_PRE_OFFSET + 8);
	post = output + CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET + CAMSS_A5_IPE_COLOUR_POST_OFFSET;
	count = !!(colour->modules & CAMSS_A5_IPE_COLOUR_CC) +
		!!(colour->modules & CAMSS_A5_IPE_COLOUR_CV);
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CC)
		put_unaligned_le32(iq_iova + CAMSS_A5_IPE_GAMMA_CC_PACKET_OFFSET, post + 8);
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CV)
		put_unaligned_le32(iq_iova + CAMSS_A5_IPE_GAMMA_CV_PACKET_OFFSET,
				   post + 8 + 24 * !!(colour->modules & CAMSS_A5_IPE_COLOUR_CC));
	encode_program(post + 8 + 24 * count, iq_iova + CAMSS_A5_IPE_GAMMA_DMI_OFFSET, 36);
	put_unaligned_le32(CAMSS_A5_IPE_PROGRAM_GAMMA, post + 16 + 24 * count);
	put_unaligned_le32(count + 1, post + 4);
	put_unaligned_le32(1, output + 2192);
	for (bank = 0; bank < 3; bank++) {
		u8 *command = output + CAMSS_A5_IPE_GAMMA_DMI_OFFSET + bank * 12;
		u8 *table = output + CAMSS_A5_IPE_GAMMA_LUT_OFFSET + bank * 1024;

		put_unaligned_le32(0x0a0003ff, command);
		put_unaligned_le32(iq_iova + CAMSS_A5_IPE_GAMMA_LUT_OFFSET + bank * 1024,
				   command + 4);
		put_unaligned_le32(0x6008 | ((bank + 1) << 24), command + 8);
		for (i = 0; i < 256; i++)
			put_unaligned_le32(gamma->base[bank][i] |
					   ((gamma->delta[bank][i] & 0x3ff) << 10),
					   table + 4 * i);
	}
	return 0;
}
