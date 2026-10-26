// SPDX-License-Identifier: GPL-2.0-only
/* SM8150, one full-frame unity-scale pass, linear 8-bit NV12/NV21.
 * Geometry is serialized into the A5 firmware ABI; no OEM blob is copied.
 * IQ modules stay disabled. Mandatory crops, FE/WE geometry, LTM grid
 * coordinates and radial coordinates are still consumed by CDM preparation.
 */
int camss_a5_ipe_bypass_size(const struct camss_a5_ipe_io *io, u32 cores,
			   u32 *bytes)
{
	const struct camss_a5_nv12_layout *in, *out;
	u32 stripes;

	if (!io || !bytes || !cores || cores > 2 ||
	    (io->output_port != 8 && io->output_port != 9))
		return -EINVAL;
	in = &io->input;
	out = &io->output;
	if (in->width < 128 || in->width > 8192 ||
	    in->height < 128 || in->height > 8192 ||
	    in->width != out->width || in->height != out->height ||
	    in->uv_swap != out->uv_swap ||
	    ((in->width | in->height | in->stride | in->slice_height |
	      out->stride | out->slice_height) & 1) ||
	    in->stride < in->width || in->slice_height < in->height ||
	    out->stride < out->width || out->slice_height < out->height)
		return -EINVAL;
	stripes = (in->width + 327) / 328;
	stripes = ((stripes + cores - 1) / cores) * cores;
	*bytes = 2268 + 624 * stripes;
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_bypass_size);

static void bypass_module_1d(u8 *data, u32 length, u32 grid, u32 first,
			     u32 port, bool horizontal, u32 fetch, u32 fetch_last)
{
	static const u16 planes[] = { 130, 162, 194, 226 };
	static const u16 full_crops[] = { 278, 286, 290, 294, 298, 302, 310, 318 };
	static const u16 half_crops[] = { 282, 306, 314 };
	u32 i;

	put_unaligned_le16(1, data + 32);
	put_unaligned_le16(length - 1, data + 34);
	put_unaligned_le16(horizontal && first ? 1 : 0xffff, data + 36);
	put_unaligned_le16(horizontal ? 1 : 2, data + 38);
	put_unaligned_le16(24, data + 42);
	put_unaligned_le16(grid, data + 84);
	put_unaligned_le16(65536 / grid, data + 86);
	put_unaligned_le16(first / grid, data + 88);
	put_unaligned_le16(first % grid, data + 90);
	put_unaligned_le16((first % grid) * (65536 / grid), data + 92);
	for (i = 0; i < ARRAY_SIZE(planes); i++) {
		u32 off = planes[i];
		bool chroma = off == (port == 9 ? 162 : 226);

		put_unaligned_le16(chroma ? 64 : 32, data + off);
		put_unaligned_le16(chroma, data + off + 2);
		put_unaligned_le16(length, data + off + 4);
		put_unaligned_le16(3, data + off + 10);
	}
	for (i = 0; i < ARRAY_SIZE(full_crops); i++)
		put_unaligned_le16(length - 1, data + full_crops[i]);
	for (i = 0; i < ARRAY_SIZE(half_crops); i++)
		put_unaligned_le16(length / 2 - 1, data + half_crops[i]);
	if (horizontal) {
		put_unaligned_le16(first - fetch, data + 276);
		put_unaligned_le16(first - fetch + length - 1, data + 278);
		put_unaligned_le16(fetch_last - fetch, data + 282);
	}
}

int camss_a5_ipe_encode_bypass_striping(void *buffer, u32 capacity,
				      const struct camss_a5_ipe_io *io,
				      u32 cores, u32 *used)
{
	struct camss_a5_ipe_partition parts[26];
	u8 *output = buffer;
	u32 bytes, count, i, width, height, port;
	int ret;

	if (!output || !used)
		return -EINVAL;
	ret = camss_a5_ipe_bypass_size(io, cores, &bytes);
	if (ret)
		return ret;
	if (capacity < bytes)
		return -ENOSPC;
	ret = camss_a5_ipe_bypass_partitions(io->input.width, cores, parts,
					  ARRAY_SIZE(parts), &count);
	if (ret)
		return ret;
	width = io->input.width;
	height = io->input.height;
	port = io->output_port;
	/* Every fallible check precedes writes, including the returned size. */
	memset(output, 0, bytes);
	put_unaligned_le16(20, output + (port == 9 ? 2 : 4));
	put_unaligned_le32(1, output + 20);
	bypass_module_1d(output + 24, height, (max(height, 240U) + 8) / 9,
			 0, port, false, 0, 0);
	put_unaligned_le16(height - 1, output + 376);
	put_unaligned_le16(height - 1, output + (port == 9 ? 396 : 392));
	put_unaligned_le32(22, output + 424);
	put_unaligned_le16(count, output + 428);
	put_unaligned_le32(2248, output + 432);
	for (i = 0; i < count; i++) {
		const struct camss_a5_ipe_partition *p = parts + i;
		u8 *stripe = output + 2268 + 624 * i;
		u32 length = p->output_last - p->output_first + 1;
		s32 x = (s32)p->output_first - (s32)(width / 2);
		s32 y = -(s32)(height / 2);

		put_unaligned_le16(p->fetch_first, stripe + 4);
		put_unaligned_le16(p->fetch_last, stripe + 6);
		put_unaligned_le16(p->output_first, stripe + (port == 9 ? 24 : 20));
		put_unaligned_le16(p->output_last, stripe + (port == 9 ? 26 : 22));
		put_unaligned_le16((p->output_first == 0) |
				   ((p->output_last == width - 1) << 8), stripe + 44);
		bypass_module_1d(stripe + 48, length, (max(width, 320U) + 11) / 12,
				 p->output_first, port, true, p->fetch_first, p->fetch_last);
		put_unaligned_le16(p->output_first, stripe + 568);
		put_unaligned_le32(x * x + y * y, stripe + 576);
		put_unaligned_le16(x, stripe + 580);
		put_unaligned_le16(y, stripe + 582);
		put_unaligned_le32((p->fetch_last - p->fetch_first + 1) * height,
				   stripe + 600);
		put_unaligned_le16(257, stripe + 618);
		put_unaligned_le16(257, stripe + 620);
	}
	*used = bytes;
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_bypass_striping);
