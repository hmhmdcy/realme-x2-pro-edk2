/* A5/Titan17x IO wire layout verified against the retained OEM HAL and ELF.
 * No tuning tables or image buffers are embedded in this serializer.
 */
static bool nv12_layout_valid(const struct camss_a5_nv12_layout *layout)
{
	return layout->width && layout->height &&
	       !(layout->width & 1) && !(layout->height & 1) &&
	       layout->stride >= layout->width && !(layout->stride & 1) &&
	       layout->slice_height >= layout->height &&
	       !(layout->slice_height & 1) &&
	       (u64)layout->stride * layout->slice_height <= (u64)U32_MAX * 2 / 3;
}

static void encode_nv12_image(void *destination,
			      const struct camss_a5_nv12_layout *layout)
{
	put_unaligned_le32(20, destination); /* IMAGE_FORMAT_LINEAR_NV12 */
	put_unaligned_le32(layout->width, destination + 4);
	put_unaligned_le32(layout->height, destination + 8);
	put_unaligned_le32(layout->uv_swap, destination + 24);
	put_unaligned_le32(layout->stride, destination + 52);
	put_unaligned_le32(layout->slice_height, destination + 56);
	put_unaligned_le32(layout->stride, destination + 60);
	put_unaligned_le32(layout->slice_height / 2, destination + 64);
}

static int encode_ipe_io(void *destination, u32 bytes,
			 const struct camss_a5_ipe_io *io)
{
	if (!destination || !io || bytes < IPE_IO_CONFIG_BYTES ||
	    !nv12_layout_valid(&io->input) || !nv12_layout_valid(&io->output) ||
	    (io->output_port != 8 && io->output_port != 9))
		return -EINVAL;
	memset(destination, 0, IPE_IO_CONFIG_BYTES);
	encode_nv12_image(destination, &io->input);
	encode_nv12_image(destination + io->output_port * 84, &io->output);
	/* One frame per batch, ordinary non-secure topology/mux defaults.
	 * The aligned userArg at byte1208 remains zero.
	 */
	put_unaligned_le32(1, destination + 1192);
	return 0;
}
