/* Every program is generated from typed, bounded values, never external CDM. */
int camss_a5_ipe_colour_check(const struct camss_a5_ipe_colour *colour)
{
	u8 command[CAMSS_A5_IPE_CC_COMMAND_BYTES];
	u32 i;

	if (!colour || (colour->modules & ~CAMSS_A5_IPE_COLOUR_MODULES))
		return -EINVAL;
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CST) {
		const struct camss_a5_ipe_cst *cst = &colour->cst;

		for (i = 0; i < 9; i++)
			if (cst->matrix[i] < -4096 || cst->matrix[i] > 4095)
				return -ERANGE;
		for (i = 0; i < 3; i++)
			if (cst->subtract[i] < -1024 || cst->subtract[i] > 1023 ||
			    cst->offset[i] > 1023 || cst->minimum[i] > 1023 ||
			    cst->maximum[i] > 1023 || cst->minimum[i] > cst->maximum[i])
				return -ERANGE;
	}
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CC) {
		int ret = camss_a5_ipe_cc_encode(command, sizeof(command), &colour->cc);

		if (ret)
			return ret;
	}
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CV) {
		const struct camss_a5_ipe_cv *cv = &colour->cv;

		for (i = 0; i < 3; i++)
			if (cv->luma[i] < -2048 || cv->luma[i] > 2047)
				return -ERANGE;
		for (i = 0; i < 8; i++)
			if (cv->chroma[i] < -2048 || cv->chroma[i] > 2047)
				return -ERANGE;
		if (cv->y_offset < -1024 || cv->y_offset > 1023 ||
		    cv->offset[0] < -1024 || cv->offset[0] > 1023 ||
		    cv->offset[1] < -1024 || cv->offset[1] > 1023)
			return -ERANGE;
	}
	return 0;
}

static void encode_cst(u8 *output, const struct camss_a5_ipe_cst *cst)
{
	u32 i;

	put_unaligned_le32(0x0300000c, output);
	put_unaligned_le32(0x5a68, output + 4);
	for (i = 0; i < 3; i++) {
		u8 *row = output + 8 + i * 16;

		put_unaligned_le32((cst->matrix[3 * i] & 0x1fff) |
				   ((cst->matrix[3 * i + 1] & 0x1fff) << 16), row);
		put_unaligned_le32(cst->matrix[3 * i + 2] & 0x1fff, row + 4);
		put_unaligned_le32((cst->subtract[i] & 0x7ff) |
				   ((u32)cst->offset[i] << 16), row + 8);
		put_unaligned_le32(cst->minimum[i] |
				   ((u32)cst->maximum[i] << 16), row + 12);
	}
}

static void encode_cv(u8 *output, const struct camss_a5_ipe_cv *cv)
{
	u32 i;

	put_unaligned_le32(0x03000008, output);
	put_unaligned_le32(0x6468, output + 4);
	put_unaligned_le32((cv->luma[0] & 0xfff) |
			   ((cv->luma[1] & 0xfff) << 16), output + 8);
	put_unaligned_le32((cv->luma[2] & 0xfff) |
			   ((cv->y_offset & 0x7ff) << 16), output + 12);
	for (i = 0; i < 4; i++)
		put_unaligned_le32((cv->chroma[2 * i] & 0xfff) |
				   ((cv->chroma[2 * i + 1] & 0xfff) << 16),
				   output + 16 + 4 * i);
	put_unaligned_le32(cv->offset[0] & 0x1fff, output + 32);
	put_unaligned_le32(cv->offset[1] & 0x1fff, output + 36);
}

static void encode_program(u8 *descriptor, u32 address, u32 bytes)
{
	put_unaligned_le32(address, descriptor);
	put_unaligned_le32((bytes - 1) << 12, descriptor + 4);
}

int camss_a5_ipe_encode_colour_iq(void *destination, u32 bytes, u32 iq_iova,
				const struct camss_a5_ipe_colour *colour)
{
	u8 *output = destination;
	u8 *pre, *post;
	u32 count = 0;
	int ret;

	if (!output || bytes < CAMSS_A5_IPE_COLOUR_IQ_BYTES || !iq_iova ||
	    (iq_iova & 31) ||
	    (u64)iq_iova + CAMSS_A5_IPE_COLOUR_IQ_BYTES > (1ULL << 32))
		return -EINVAL;
	ret = camss_a5_ipe_colour_check(colour);
	if (ret)
		return ret;
	ret = camss_a5_ipe_encode_bypass_iq(output, bytes);
	if (ret)
		return ret;
	memset(output + CAMSS_A5_IPE_IQ_BYTES, 0,
	       CAMSS_A5_IPE_COLOUR_IQ_BYTES - CAMSS_A5_IPE_IQ_BYTES);
	pre = output + CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET + CAMSS_A5_IPE_COLOUR_PRE_OFFSET;
	post = output + CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET + CAMSS_A5_IPE_COLOUR_POST_OFFSET;
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CST) {
		put_unaligned_le32(1, output + 2092);
		put_unaligned_le32(1, pre + 4);
		encode_program(pre + 8, iq_iova + CAMSS_A5_IPE_CST_PACKET_OFFSET, 56);
		encode_cst(output + CAMSS_A5_IPE_CST_PACKET_OFFSET, &colour->cst);
	}
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CC) {
		put_unaligned_le32(1, output + 2188);
		encode_program(post + 8 + 24 * count++, iq_iova + CAMSS_A5_IPE_COLOUR_CC_PACKET_OFFSET, 44);
		/* Already validated above; this fixed encoder cannot fail here. */
		camss_a5_ipe_cc_encode(output + CAMSS_A5_IPE_COLOUR_CC_PACKET_OFFSET, 44, &colour->cc);
	}
	if (colour->modules & CAMSS_A5_IPE_COLOUR_CV) {
		put_unaligned_le32(1, output + 2200);
		encode_program(post + 8 + 24 * count++, iq_iova + CAMSS_A5_IPE_CV_PACKET_OFFSET, 40);
		encode_cv(output + CAMSS_A5_IPE_CV_PACKET_OFFSET, &colour->cv);
	}
	put_unaligned_le32(count, post + 4);
	return 0;
}
