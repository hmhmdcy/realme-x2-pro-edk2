
static void buffer_request_complete(struct vb2_buffer *vb)
{
	struct ipe_context *ctx = vb2_get_drv_priv(vb->vb2_queue);

	v4l2_ctrl_request_complete(vb->req_obj.req, &ctx->controls);
}

static int request_validate(struct media_request *request)
{
	struct media_request_object *object;
	struct ipe_context *ctx = NULL;
	struct v4l2_ctrl_handler *handler;
	struct v4l2_ctrl *control;
	unsigned int count = vb2_request_buffer_cnt(request);
	int ret;

	if (!count)
		return -ENOENT;
	if (count != 1)
		return -EINVAL;
	list_for_each_entry(object, &request->objects, list) {
		struct vb2_buffer *vb;

		if (!vb2_request_object_is_buffer(object))
			continue;
		vb = container_of(object, struct vb2_buffer, req_obj);
		if (vb->vb2_queue->ops != &queue_ops ||
		    vb->type != V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE)
			return -EINVAL;
		ctx = vb2_get_drv_priv(vb->vb2_queue);
	}
	if (!ctx)
		return -EINVAL;
	handler = v4l2_ctrl_request_hdl_find(request, &ctx->controls);
	if (!handler)
		return -ENOENT;
	control = v4l2_ctrl_request_hdl_ctrl_find(handler,
					      V4L2_CID_QCOM_IPE_A5_FRAME_PARAMS);
	ret = control ? 0 : -ENOENT;
	v4l2_ctrl_request_hdl_put(handler);
	return ret ?: vb2_request_validate(request);
}

static const struct media_device_ops request_ops = {
	.req_validate = request_validate,
	.req_queue = v4l2_m2m_request_queue,
};
