// SPDX-License-Identifier: GPL-2.0-only
/* Full-frame, unity-scale, 8-bit linear YUV with IQ modules disabled.
 * The target striping policy uses 328-pixel output partitions, rounds the
 * count to the number of cores, and aligns internal boundaries to chroma.
 * A four-pixel fetch halo is retained at internal boundaries.
 * This describes ranges only; it does not serialize the full firmware blob.
 */
int camss_a5_ipe_bypass_partitions(u32 width, u32 cores,
				 struct camss_a5_ipe_partition *output,
				 u32 capacity, u32 *count)
{
	u32 stripes, i;

	if (!output || !count || width < 128 || width > 8192 || (width & 1) ||
	    !cores || cores > 2)
		return -EINVAL;
	stripes = (width + 327) / 328;
	stripes = ((stripes + cores - 1) / cores) * cores;
	if (capacity < stripes)
		return -ENOSPC;
	for (i = 0; i < stripes; i++) {
		u32 index = stripes - i - 1;
		u32 first = ((width * index) / stripes) & ~1U;
		u32 last = (((width * (index + 1)) / stripes) & ~1U) - 1;

		output[i].output_first = first;
		output[i].output_last = last;
		output[i].fetch_first = first < 4 ? 0 : first - 4;
		output[i].fetch_last = last + 4 < width ? last + 4 : width - 1;
	}
	*count = stripes;
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_bypass_partitions);
