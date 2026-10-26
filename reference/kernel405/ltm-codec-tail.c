static int ltm_unsigned_check(const struct camss_a5_ipe_ltm_unsigned *table,
			      u32 count, u32 bits)
{
	u32 i;
	s32 limit = 1U << (bits - 1);

	for (i = 0; i < count; i++)
		if (table[i].base >= (1U << bits) ||
		    table[i].delta < -limit || table[i].delta >= limit)
			return -ERANGE;
	return 0;
}

static int ltm_signed_check(const struct camss_a5_ipe_ltm_signed *table, u32 count)
{
	u32 i;

	for (i = 0; i < count; i++)
		if (table[i].base < -2048 || table[i].base > 2047 ||
		    table[i].delta < -2048 || table[i].delta > 2047)
			return -ERANGE;
	return 0;
}

int camss_a5_ipe_ltm_check(const struct camss_a5_ipe_ltm *ltm)
{
	const struct camss_a5_ipe_ltm_iq *iq;
	u32 i;
	int ret;

	if (!ltm)
		return -EINVAL;
	iq = &ltm->iq;
	if (iq->reverse_gamma > 1 || iq->local_adaptation > 1 ||
	    iq->mask_filter > 1 || iq->data_collection > 1 ||
	    iq->image_processing > 1 || iq->horizontal_termination > 1 ||
	    iq->vertical_termination > 1 || iq->bin_init_count > 15 ||
	    iq->rgb2y[0] > 63 || iq->rgb2y[1] > 63 ||
	    iq->rgb2y[2] > 63 || iq->rgb2y[3] > 127 ||
	    iq->lce_threshold > 1023 || iq->y_ratio_max > 1023 ||
	    iq->mask_shift > 31 || iq->mask_scale > 4095)
		return -ERANGE;
	for (i = 0; i < 6; i++)
		if (iq->mask_kernel[i] > (i < 3 ? 7 : 3))
			return -ERANGE;
	for (i = 0; i < 2; i++) {
		ret = ltm_unsigned_check(ltm->la[i], 64, 12);
		if (ret)
			return ret;
		ret = ltm_signed_check(ltm->lce[i], 16);
		if (ret)
			return ret;
	}
	for (i = 0; i < 5; i++) {
		ret = ltm_unsigned_check(ltm->reverse_gamma[i], 64, 14);
		if (ret)
			return ret;
	}
	ret = ltm_unsigned_check(ltm->curve, 64, 12);
	if (ret)
		return ret;
	ret = ltm_unsigned_check(ltm->mask, 64, 12);
	if (ret)
		return ret;
	return ltm_signed_check(ltm->scale, 64);
}

static void ltm_unsigned_encode(u8 *output,
			       const struct camss_a5_ipe_ltm_unsigned *table,
			       u32 count, u32 bits)
{
	u32 i, mask = (1U << bits) - 1;

	for (i = 0; i < count; i++)
		put_unaligned_le32(table[i].base |
				   (((u32)table[i].delta & mask) << bits), output + 4 * i);
}

static void ltm_signed_encode(u8 *output,
			     const struct camss_a5_ipe_ltm_signed *table, u32 count)
{
	u32 i;

	for (i = 0; i < count; i++)
		put_unaligned_le32(((u32)table[i].base & 0xfff) |
				   (((u32)table[i].delta & 0xfff) << 12), output + 4 * i);
}

int camss_a5_ipe_encode_ltm_iq(void *destination, u32 bytes, u32 iq_iova,
			     const struct camss_a5_ipe_colour *colour,
			     const struct camss_a5_ipe_gamma *gamma,
			     const struct camss_a5_ipe_ltm *ltm)
{
	static const u16 offsets[] = {
		0, 48, 304, 560, 816, 1072, 1328, 1392, 1456, 1712, 1968, 2224, 2480
	};
	static const u16 lengths[] = {
		48, 256, 256, 256, 256, 256, 64, 64, 256, 256, 256, 256, 256
	};
	struct camss_a5_ipe_colour empty = {};
	const struct camss_a5_ipe_ltm_iq *iq;
	u8 *output = destination, *pre, *post, *table;
	u32 i, bank, count;
	int ret;

	if (!output || bytes < CAMSS_A5_IPE_LTM_IQ_BYTES || !iq_iova ||
	    (iq_iova & 31) ||
	    (u64)iq_iova + CAMSS_A5_IPE_LTM_IQ_BYTES > (1ULL << 32))
		return -EINVAL;
	ret = camss_a5_ipe_ltm_check(ltm);
	if (ret)
		return ret;
	if (gamma) {
		ret = camss_a5_ipe_gamma_check(gamma);
		if (ret)
			return ret;
	}
	if (!colour)
		colour = &empty;
	ret = camss_a5_ipe_colour_check(colour);
	if (ret)
		return ret;
	/* Reuse the checked conversion encoder; move only fixed command storage. */
	ret = camss_a5_ipe_encode_colour_iq(output, bytes, iq_iova, colour);
	if (ret)
		return ret;
	memmove(output + CAMSS_A5_IPE_LTM_CST_OFFSET,
		output + CAMSS_A5_IPE_CST_PACKET_OFFSET, 140);
	memset(output + CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET, 0,
	       CAMSS_A5_IPE_LTM_CST_OFFSET - CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET);
	memset(output + CAMSS_A5_IPE_LTM_CST_OFFSET + 140, 0,
	       CAMSS_A5_IPE_LTM_IQ_BYTES - CAMSS_A5_IPE_LTM_CST_OFFSET - 140);
	pre = output + CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET + CAMSS_A5_IPE_LTM_PRE_OFFSET;
	post = output + CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET + CAMSS_A5_IPE_LTM_POST_OFFSET;
	count = !!(colour->modules & CAMSS_A5_IPE_COLOUR_CST);
	if (count)
		encode_program(pre + 8, iq_iova + CAMSS_A5_IPE_LTM_CST_OFFSET, 56);
	encode_program(pre + 8 + 24 * count, iq_iova + CAMSS_A5_IPE_LTM_DMI_OFFSET, 156);
	put_unaligned_le32(CAMSS_A5_IPE_PROGRAM_LTM, pre + 16 + 24 * count);
	put_unaligned_le32(count + 1, pre + 4);
	count = 0;
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CC)
		encode_program(post + 8 + 24 * count++, iq_iova + CAMSS_A5_IPE_LTM_CC_OFFSET, 44);
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CV)
		encode_program(post + 8 + 24 * count++, iq_iova + CAMSS_A5_IPE_LTM_CV_OFFSET, 40);
	if (gamma) {
		encode_program(post + 8 + 24 * count, iq_iova + CAMSS_A5_IPE_LTM_GAMMA_DMI_OFFSET, 36);
		put_unaligned_le32(CAMSS_A5_IPE_PROGRAM_GAMMA, post + 16 + 24 * count++);
		put_unaligned_le32(1, output + 2192);
		for (bank = 0; bank < 3; bank++) {
			u8 *command = output + CAMSS_A5_IPE_LTM_GAMMA_DMI_OFFSET + bank * 12;
			u32 address = iq_iova + CAMSS_A5_IPE_LTM_GAMMA_LUT_OFFSET + bank * 1024;

			put_unaligned_le32(0x010003ff, command);
			put_unaligned_le32(address, command + 4);
			put_unaligned_le32(0x6008 | ((bank + 1) << 24), command + 8);
			for (i = 0; i < 256; i++)
				put_unaligned_le32(gamma->base[bank][i] |
						   (((u32)gamma->delta[bank][i] & 0x3ff) << 10),
						   output + CAMSS_A5_IPE_LTM_GAMMA_LUT_OFFSET +
						   bank * 1024 + 4 * i);
		}
	}
	put_unaligned_le32(count, post + 4);
	iq = &ltm->iq;
	put_unaligned_le32(1, output + 2096);
	put_unaligned_le32(iq->reverse_gamma, output + 2100);
	put_unaligned_le32(iq->local_adaptation, output + 2104);
	put_unaligned_le32(iq->mask_filter, output + 2108);
	put_unaligned_le32(iq->bin_init_count, output + 2112);
	for (i = 0; i < 4; i++)
		put_unaligned_le32(iq->rgb2y[i], output + 2116 + 4 * i);
	put_unaligned_le32(iq->lce_threshold, output + 2132);
	put_unaligned_le32(iq->y_ratio_max, output + 2136);
	for (i = 0; i < 6; i++)
		put_unaligned_le32(iq->mask_kernel[i], output + 2140 + 4 * i);
	put_unaligned_le32(iq->mask_shift, output + 2164);
	put_unaligned_le32(iq->mask_scale, output + 2168);
	put_unaligned_le32(iq->horizontal_termination, output + 2172);
	put_unaligned_le32(iq->vertical_termination, output + 2176);
	put_unaligned_le32(iq->data_collection, output + 2180);
	put_unaligned_le32(iq->image_processing, output + 2184);
	for (bank = 0; bank < ARRAY_SIZE(offsets); bank++) {
		u8 *command = output + CAMSS_A5_IPE_LTM_DMI_OFFSET + bank * 12;

		put_unaligned_le32(0x01000000 | (lengths[bank] - 1), command);
		put_unaligned_le32(iq_iova + CAMSS_A5_IPE_LTM_LUT_OFFSET + offsets[bank],
				   command + 4);
		put_unaligned_le32(0x5c08 | ((bank + 1) << 24), command + 8);
	}
	table = output + CAMSS_A5_IPE_LTM_LUT_OFFSET;
	for (i = 0; i < 12; i++)
		put_unaligned_le32(ltm->weight[i], table + 4 * i);
	for (i = 0; i < 2; i++) {
		ltm_unsigned_encode(table + offsets[1 + i], ltm->la[i], 64, 12);
		ltm_signed_encode(table + offsets[6 + i], ltm->lce[i], 16);
	}
	ltm_unsigned_encode(table + offsets[3], ltm->curve, 64, 12);
	ltm_signed_encode(table + offsets[4], ltm->scale, 64);
	ltm_unsigned_encode(table + offsets[5], ltm->mask, 64, 12);
	for (i = 0; i < 5; i++)
		ltm_unsigned_encode(table + offsets[8 + i], ltm->reverse_gamma[i], 64, 14);
	return 0;
}
