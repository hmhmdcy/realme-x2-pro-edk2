static int imx319_set_stream(struct v4l2_subdev *sd, int enable)
{
	struct imx319 *imx319 = to_imx319(sd);
	int ret = 0, cleanup_ret;

	enable = !!enable;
	mutex_lock(&imx319->mutex);
	if (enable && imx319->removing) {
		ret = -ENODEV;
		goto unlock;
	}
	if (enable == imx319->streaming)
		goto unlock;
	if (enable) {
		if (imx319->power_fault) {
			ret = -EIO;
			goto unlock;
		}
		ret = pm_runtime_resume_and_get(imx319->dev);
		if (ret < 0)
			goto unlock;
		ret = imx319_start_streaming(imx319);
		if (ret) {
			if (!imx319->of_power_resources) {
				pm_runtime_put(imx319->dev);
				goto unlock;
			}
			/* Keep the stream's PM reference while attempting standby. */
			cleanup_ret = imx319->identified ? imx319_stop_streaming(imx319) : 0;
			if (cleanup_ret)
				imx319->power_fault = true;
			cleanup_ret = pm_runtime_put_sync_suspend(imx319->dev);
			if (cleanup_ret < 0)
				imx319->power_fault = true;
			goto unlock;
		}
		imx319->streaming = true;
	} else {
		ret = imx319_stop_streaming(imx319);
		if (ret && imx319->of_power_resources)
			imx319->power_fault = true;
		/* Exactly one reference is owned, even when the stop write fails. */
		imx319->streaming = false;
		if (imx319->of_power_resources)
			cleanup_ret = pm_runtime_put_sync_suspend(imx319->dev);
		else {
			pm_runtime_put(imx319->dev);
			ret = 0;
			cleanup_ret = 0;
		}
		if (cleanup_ret < 0) {
			imx319->power_fault = true;
			if (!ret)
				ret = cleanup_ret;
		}
	}
	__v4l2_ctrl_grab(imx319->vflip, enable);
	__v4l2_ctrl_grab(imx319->hflip, enable);
unlock:
	mutex_unlock(&imx319->mutex);
	return ret;
}
