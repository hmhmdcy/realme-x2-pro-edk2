/* SPDX-License-Identifier: GPL-2.0-only */
/* Native DC resampling and pass geometry; no copied opaque striping data. */
static u32 ltm_dc_exponent(u32 width, u32 height)
{
	if (width >= 288 && height > 215)
		return 0;
	if (width >= 144 && height >= 108)
		return 1;
	return 2;
}

int camss_a5_ipe_ltm_pd10_size(const struct camss_a5_ipe_io *io, u32 cores,
			     const struct camss_a5_ipe_ltm_geometry *ltm,
			     u32 *bytes)
{
	struct camss_a5_pd10_layout coarse;
	u32 single;
	int ret;

	if (!bytes)
		return -EINVAL;
	ret = camss_a5_ipe_ltm_size(io, cores, ltm, &single);
	if (ret)
		return ret;
	if (io->output_port != 8 || io->input.uv_swap)
		return -EOPNOTSUPP;
	if (ltm->data_collection && !(ltm->image_processing && ltm->mask_filter))
		return -EOPNOTSUPP;
	ret = camss_a5_ipe_pd10_quarter(&io->input, &coarse);
	if (ret)
		return ret;
	*bytes = single + (ltm->data_collection ? 624 * ((coarse.width + 327) / 328) : 0);
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_ltm_pd10_size);

static void ltm_dc_axis(u8 *data, u32 input_length, u32 target_length,
		       u32 first, u32 last, u32 target_first, u32 target_last,
		       u32 fetch, u32 fetch_last, u32 exponent, bool horizontal)
{
	u32 length = last - first + 1;
	u32 grid = (max(input_length, horizontal ? 320U : 240U) +
		    (horizontal ? 11 : 8)) / (horizontal ? 12 : 9);
	u32 step = ((u64)input_length << 21) / target_length;
	u32 resample_first = ((u64)target_first * step) >> 21;
	u32 resample_offset = resample_first - first;
	u32 phase = first % grid;
	u32 table_step = 24 >> exponent, half = table_step / 2;
	u32 index = target_first < half ? 0 : (target_first - half) / table_step + 1;
	u32 table_phase = target_first < half ? target_first : (target_first - half) % table_step;
	u32 table_first = index ? index - 1 : 0;
	u32 table_end = target_last + 1 < half ? 0 : (target_last + 1 - half) / table_step + 1;
	u32 columns = 12;

	if (table_step * 12 - 1 > target_last)
		columns = table_end > table_first + 2 ? table_end - 2 : table_first;
	put_unaligned_le16(1, data + 32);
	put_unaligned_le16(length - 1, data + 34);
	put_unaligned_le16(horizontal && first ? 1 : 0xffff, data + 36);
	put_unaligned_le16(horizontal ? 1 : 2, data + 38);
	put_unaligned_le16(24, data + 42);
	put_unaligned_le16(resample_offset, data + 44);
	put_unaligned_le16(1, data + 46);
	put_unaligned_le16(resample_offset, data + 52);
	put_unaligned_le32((target_first * step) & 0x1fffff, data + 56);
	put_unaligned_le32(step, data + 60);
	put_unaligned_le16(3, data + 64);
	put_unaligned_le16(last - resample_first, data + 66);
	if (horizontal) {
		put_unaligned_le16(index, data + 68);
		put_unaligned_le16(table_phase, data + 70);
		put_unaligned_le16(!first, data + 72);
		put_unaligned_le16(table_first, data + 74);
		put_unaligned_le16(columns, data + 76);
		put_unaligned_le16(target_last - target_first, data + 80);
	}
	put_unaligned_le16(grid, data + 84);
	put_unaligned_le16(65536 / grid, data + 86);
	put_unaligned_le16(first / grid, data + 88);
	put_unaligned_le16(phase, data + 90);
	put_unaligned_le16(phase * (65536 / grid), data + 92);
	put_unaligned_le16(first - fetch, data + 276);
	put_unaligned_le16(last - fetch, data + 278);
	put_unaligned_le16(horizontal ? fetch_last - fetch : length / 2 - 1, data + 282);
}

int camss_a5_ipe_encode_ltm_pd10_striping(void *buffer, u32 capacity,
					const struct camss_a5_ipe_io *io,
					u32 cores,
					const struct camss_a5_ipe_ltm_geometry *ltm,
					u32 *used)
{
	struct camss_a5_ipe_partition parts[7];
	struct camss_a5_pd10_layout coarse;
	u8 *output = buffer;
	u32 bytes, single, count, full_count, i, exponent, target_width, target_height;
	u32 phase_step;
	int ret;

	if (!buffer || !used)
		return -EINVAL;
	ret = camss_a5_ipe_ltm_pd10_size(io, cores, ltm, &bytes);
	if (ret)
		return ret;
	if (capacity < bytes)
		return -ENOSPC;
	ret = camss_a5_ipe_pd10_quarter(&io->input, &coarse);
	if (ret)
		return ret;
	count = (coarse.width + 327) / 328;
	for (i = 0; i < count; i++) {
		u32 index = count - i - 1;

		parts[i].output_first = ((coarse.width * index) / count) & ~1U;
		parts[i].output_last = (((coarse.width * (index + 1)) / count) & ~1U) - 1;
	}
	ret = camss_a5_ipe_encode_ltm_striping(buffer, capacity, io, cores, ltm, &single);
	if (ret)
		return ret;
	if (!ltm->data_collection) {
		*used = single;
		return 0;
	}
	exponent = ltm_dc_exponent(coarse.width, coarse.height);
	target_width = 288 >> exponent;
	target_height = 216 >> exponent;
	phase_step = ((u64)coarse.width << 21) / target_width;
	full_count = get_unaligned_le16(output + 428);
	memmove(output + 2268 + count * 624, output + 2268, single - 2268);
	memmove(output + 436, output + 24, 412);
	memset(output + 24, 0, 412);
	memset(output + 2268, 0, count * 624);
	put_unaligned_le32(2, output + 20);
	ltm_dc_axis(output + 24, coarse.height, target_height, 0, coarse.height - 1,
		    0, target_height - 1, 0, coarse.height - 1, exponent, false);
	put_unaligned_le16(coarse.height - 1, output + 24 + 270);
	put_unaligned_le16(coarse.height / 2 - 1, output + 24 + 274);
	put_unaligned_le16(coarse.height - 1, output + 24 + 376);
	put_unaligned_le16(coarse.height - 1, output + 24 + 352);
	put_unaligned_le16(1, output + 24 + 390);
	put_unaligned_le16(count, output + 24 + 404);
	put_unaligned_le32(2248, output + 24 + 408);
	put_unaligned_le16(coarse.height - 1, output + 436 + 360);
	put_unaligned_le32(434, output + 436 + 400);
	put_unaligned_le32(1836 + count * 624, output + 436 + 408);
	for (i = 0; i < count; i++) {
		const struct camss_a5_ipe_partition *p = parts + i;
		u8 *stripe = output + 2268 + i * 624;
		u32 target_first = p->output_first * target_width / coarse.width;
		u32 target_last = (p->output_last + 1) * target_width / coarse.width - 1;
		u32 first, last = p->output_last, fetch, fetch_last;

		target_first = target_first > 2 ? target_first - 2 : 0;
		first = (((u64)target_first * phase_step) >> 21) & ~1U;
		fetch = (first < 4 ? 0 : first - 4) & ~1U;
		fetch_last = min(last + 4, coarse.width - 1);
		put_unaligned_le16(fetch, stripe + 4);
		put_unaligned_le16(fetch_last, stripe + 6);
		put_unaligned_le16(p->output_first, stripe + 28);
		put_unaligned_le16(p->output_last, stripe + 30);
		put_unaligned_le16((p->output_first == 0) | ((p->output_last == coarse.width - 1) << 8), stripe + 44);
		ltm_dc_axis(stripe + 48, coarse.width, target_width, first, last,
			    target_first, target_last - (last < coarse.width - 1 ? 2 : 0),
			    fetch, fetch_last, exponent, true);
		put_unaligned_le16(p->output_first - fetch, stripe + 316);
		put_unaligned_le16(last - fetch, stripe + 318);
		put_unaligned_le16(p->output_first - fetch, stripe + 320);
		put_unaligned_le16(last - fetch, stripe + 322);
		put_unaligned_le32((fetch_last - fetch + 1) * coarse.height, stripe + 600);
		put_unaligned_le32(count == 1, stripe + 604);
	}
	for (i = 0; i < full_count; i++) {
		u8 *stripe = output + 2268 + count * 624 + i * 624;
		u32 first = get_unaligned_le16(stripe + 20) / 4;
		u32 last = get_unaligned_le16(stripe + 22) / 4;

		put_unaligned_le16(first < 10 ? 0 : first - 10, stripe + 12);
		put_unaligned_le16(min(last + 10, coarse.width - 1), stripe + 14);
	}
	*used = bytes;
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_ltm_pd10_striping);
