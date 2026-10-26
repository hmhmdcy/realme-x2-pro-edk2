/* SPDX-License-Identifier: GPL-2.0-only */
int camss_a5_ipe_encode_io(void *destination, u32 bytes,
			 const struct camss_a5_ipe_io *io,
			 const struct camss_a5_pd10_layout *coarse)
{
	struct camss_a5_pd10_layout expected;
	u8 *output = destination;
	int ret;

	if (!destination || !io || bytes < IPE_IO_CONFIG_BYTES ||
	    !nv12_layout_valid(&io->input) || !nv12_layout_valid(&io->output) ||
	    (io->output_port != 8 && io->output_port != 9))
		return -EINVAL;
	if (coarse) {
		ret = camss_a5_ipe_pd10_quarter(&io->input, &expected);
		if (ret)
			return ret;
		if (io->input.width != io->output.width ||
		    io->input.height != io->output.height ||
		    io->input.uv_swap != io->output.uv_swap ||
		    coarse->width != expected.width ||
		    coarse->height != expected.height ||
		    coarse->stride != expected.stride ||
		    coarse->slice_height != expected.slice_height ||
		    coarse->bytes != expected.bytes)
			return -EINVAL;
	}
	/* Validation precedes all writes, including optional coarse layout. */
	memset(output, 0, IPE_IO_CONFIG_BYTES);
	encode_nv12_image(output, &io->input);
	encode_nv12_image(output + io->output_port * 84, &io->output);
	if (coarse) {
		u8 *image = output + 84; /* IPE_INPUT_IMAGE_DS4, one PD10 plane */

		put_unaligned_le32(10, image);
		put_unaligned_le32(coarse->width, image + 4);
		put_unaligned_le32(coarse->height, image + 8);
		put_unaligned_le32(coarse->stride, image + 52);
		put_unaligned_le32(coarse->slice_height, image + 56);
	}
	put_unaligned_le32(1, output + 1192);
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_io);
