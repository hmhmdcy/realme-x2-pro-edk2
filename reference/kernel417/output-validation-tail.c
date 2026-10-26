
static int buffer_output_validate(struct vb2_buffer *vb)
{
	struct vb2_v4l2_buffer *buffer = to_vb2_v4l2_buffer(vb);

	if (buffer->field == V4L2_FIELD_ANY)
		buffer->field = V4L2_FIELD_NONE;
	return buffer->field == V4L2_FIELD_NONE ? 0 : -EINVAL;
}
