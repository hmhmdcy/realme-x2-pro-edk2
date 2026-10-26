/* SPDX-License-Identifier: GPL-2.0-only */
/* Initial native two-pass profile: 640x480 FULL and 160x120 PD10.
 * Keep the accepted domain explicit until other geometries are verified.
 * Serialize geometry, never an opaque stock striping blob.
 */
int camss_a5_ipe_ltm_pd10_size(const struct camss_a5_ipe_io *io, u32 cores,
			     const struct camss_a5_ipe_ltm_geometry *ltm,
			     u32 *bytes)
{
	u32 single;
	int ret;

	ret = camss_a5_ipe_ltm_size(io, cores, ltm, &single);
	if (ret)
		return ret;
	if (io->input.width != 640 || io->input.height != 480 ||
	    io->output_port != 8 || io->input.uv_swap || (cores != 1 && cores != 2))
		return -EOPNOTSUPP;
	if (ltm->data_collection && !(ltm->image_processing && ltm->mask_filter))
		return -EOPNOTSUPP;
	*bytes = single + (ltm->data_collection ? 624 : 0);
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_ltm_pd10_size);

static void ltm_coarse_axis(u8 *data, u32 length, u32 output_length,
			    bool horizontal)
{
	u32 grid = (max(output_length, horizontal ? 320U : 240U) +
		    (horizontal ? 11 : 8)) / (horizontal ? 12 : 9);

	put_unaligned_le16(1, data + 32);
	put_unaligned_le16(length - 1, data + 34);
	put_unaligned_le16(0xffff, data + 36);
	put_unaligned_le16(horizontal ? 1 : 2, data + 38);
	put_unaligned_le16(24, data + 42);
	put_unaligned_le16(1, data + 46);
	put_unaligned_le32((length << 21) / output_length, data + 60);
	put_unaligned_le16(3, data + 64);
	put_unaligned_le16(length - 1, data + 66);
	put_unaligned_le16(grid, data + 84);
	put_unaligned_le16(65536 / grid, data + 86);
	put_unaligned_le16(length - 1, data + 278);
	put_unaligned_le16(horizontal ? length - 1 : length / 2 - 1, data + 282);
	if (horizontal) {
		put_unaligned_le16(1, data + 72);
		put_unaligned_le16(12, data + 76);
		put_unaligned_le16(output_length - 1, data + 80);
	}
}

int camss_a5_ipe_encode_ltm_pd10_striping(void *buffer, u32 capacity,
					const struct camss_a5_ipe_io *io,
					u32 cores,
					const struct camss_a5_ipe_ltm_geometry *ltm,
					u32 *used)
{
	u8 *output = buffer;
	u32 bytes, single, i;
	int ret;

	if (!buffer || !used)
		return -EINVAL;
	ret = camss_a5_ipe_ltm_pd10_size(io, cores, ltm, &bytes);
	if (ret)
		return ret;
	if (capacity < bytes)
		return -ENOSPC;
	ret = camss_a5_ipe_encode_ltm_striping(buffer, capacity, io, cores, ltm, &single);
	if (ret)
		return ret;
	if (!ltm->data_collection) {
		*used = single;
		return 0;
	}
	/* Stripe pointers are relative to each pass's own base at 20+412*i.
	 * Moving the full pass also changes its module-configuration offset.
	 */
	memmove(output + 2892, output + 2268, single - 2268);
	memmove(output + 436, output + 24, 412);
	memset(output + 24, 0, 412);
	memset(output + 2268, 0, 624);
	put_unaligned_le32(2, output + 20);
	ltm_coarse_axis(output + 24, 120, 108, false);
	put_unaligned_le16(119, output + 24 + 352);
	put_unaligned_le16(1, output + 24 + 390);
	put_unaligned_le16(1, output + 24 + 404);
	put_unaligned_le32(2248, output + 24 + 408);
	put_unaligned_le16(119, output + 436 + 360);
	put_unaligned_le32(434, output + 436 + 400);
	put_unaligned_le32(2460, output + 436 + 408);
	put_unaligned_le16(159, output + 2268 + 6);
	put_unaligned_le16(257, output + 2268 + 44);
	ltm_coarse_axis(output + 2268 + 48, 160, 144, true);
	put_unaligned_le32(160 * 120, output + 2268 + 600);
	put_unaligned_le32(1, output + 2268 + 604);
	for (i = 0; i < 2; i++) {
		u8 *stripe = output + 2892 + i * 624;
		u32 first = get_unaligned_le16(stripe + 20) / 4;
		u32 last = get_unaligned_le16(stripe + 22) / 4;

		put_unaligned_le16(first < 10 ? 0 : first - 10, stripe + 12);
		put_unaligned_le16(min(last + 10, 159U), stripe + 14);
	}
	*used = bytes;
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_ltm_pd10_striping);
