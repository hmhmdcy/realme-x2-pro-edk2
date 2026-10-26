
static int frame_params_try(struct v4l2_ctrl *ctrl)
{
	return camss_a5_ipe_frame_params_check(ctrl->p_new.p);
}

static int frame_params_set(struct v4l2_ctrl *ctrl)
{
	struct ipe_context *ctx = container_of(ctrl->handler, struct ipe_context, controls);

	/* Only request_setup running on this context's hardware worker may apply
	 * parameters. Direct S_CTRL cannot race or replace a request snapshot.
	 * EXECUTE_ON_WRITE ensures identical consecutive payloads are copied too.
	 */
	if (current != READ_ONCE(ctx->control_task) || !ctx->pending_params)
		return -EACCES;
	memcpy(ctx->pending_params, ctrl->p_new.p, sizeof(*ctx->pending_params));
	ctx->params_written = true;
	return 0;
}

static const struct v4l2_ctrl_ops frame_params_ops = {
	.try_ctrl = frame_params_try,
	.s_ctrl = frame_params_set,
};

static const struct v4l2_ctrl_config frame_params_config = {
	.ops = &frame_params_ops,
	.id = V4L2_CID_QCOM_IPE_A5_FRAME_PARAMS,
	.name = "IPE frame parameters",
	.type = V4L2_CTRL_TYPE_U8,
	.min = 0,
	.max = 255,
	.step = 1,
	.def = 0,
	.dims = { sizeof(struct qcom_ipe_a5_frame_params) },
	.flags = V4L2_CTRL_FLAG_EXECUTE_ON_WRITE,
};

static int frame_params_run(struct ipe_context *ctx,
			    const struct camss_a5_ipe_job *job,
			    const struct qcom_ipe_a5_frame_params *params,
			    enum camss_a5_ipe_result *result)
{
	const struct camss_a5_ipe_colour *colour;
	const struct camss_a5_ipe_gamma *gamma;
	const struct camss_a5_ipe_ltm *ltm;

	if (!params || !params->version)
		return camss_a5_ipe_run_status(ctx->dev->a5, &ctx->session, job, result);
	colour = (const void *)&params->colour;
	gamma = params->flags & QCOM_IPE_A5_GAMMA ? (const void *)&params->gamma : NULL;
	ltm = params->flags & QCOM_IPE_A5_LTM ? (const void *)&params->ltm : NULL;
	return camss_a5_ipe_run_ltm_status(ctx->dev->a5, &ctx->session, job,
					 colour, gamma, ltm, result);
}
