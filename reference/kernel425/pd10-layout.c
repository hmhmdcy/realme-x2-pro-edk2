/* SPDX-License-Identifier: GPL-2.0-only */
/* Native SM8150 PD10 layout for an explicit quarter-resolution input.
 * This describes backing; it neither produces pixels nor starts DMA. */
int camss_a5_ipe_pd10_quarter(const struct camss_a5_nv12_layout *full,
			    struct camss_a5_pd10_layout *result)
{
	struct camss_a5_pd10_layout layout;

	if (!full || !result || full->width < 128 || full->width > 8192 ||
	    full->height < 128 || full->height > 8192 ||
	    ((full->width | full->height | full->stride | full->slice_height) & 1) ||
	    full->stride < full->width || full->slice_height < full->height)
		return -EINVAL;
	/* Even ceiling of ceil(full / 4), as in the retained native allocator. */
	layout.width = ((full->width + 7) / 4) & ~1U;
	layout.height = ((full->height + 7) / 4) & ~1U;
	/* Each PD10 2x2 block occupies eight bytes in one plane. The native
	 * format helper aligns rows to 192 bytes and packed rows to four.
	 * Newer reference sources' 256-byte/32-line rules differ. */
	layout.stride = ((layout.width * 4 + 191) / 192) * 192;
	layout.slice_height = ((layout.height + 7) / 8) * 4;
	layout.bytes = layout.stride * layout.slice_height;
	*result = layout;
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_pd10_quarter);
