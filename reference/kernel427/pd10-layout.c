int camss_format_pd10_layout(u32 width, u32 height,
			     struct camss_pd10_layout *layout)
{
	struct camss_pd10_layout result;

	if (!layout || width < 2 || height < 2 || width > 2048 || height > 2048 ||
	    ((width | height) & 1))
		return -EINVAL;
	result.stride = DIV_ROUND_UP(width * 4, 192) * 192;
	result.slice_height = DIV_ROUND_UP(height, 8) * 4;
	result.bytes = result.stride * result.slice_height;
	*layout = result;
	return 0;
}
