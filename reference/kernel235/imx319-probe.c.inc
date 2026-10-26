static int imx319_probe(struct i2c_client *client)
{
	struct imx319 *imx319;
	bool full_power = false, probe_reference = false;
	unsigned long freq;
	int ret, cleanup_ret;

	imx319 = devm_kzalloc(&client->dev, sizeof(*imx319), GFP_KERNEL);
	if (!imx319)
		return -ENOMEM;
	imx319->dev = &client->dev;
	imx319->profile = client->dev.of_node ? &imx319_rmx1931_profile : &imx319_acpi_profile;
	mutex_init(&imx319->mutex);
	imx319->clk = devm_v4l2_sensor_clk_get(imx319->dev, NULL);
	if (IS_ERR(imx319->clk)) {
		ret = PTR_ERR(imx319->clk);
		goto error_probe;
	}
	freq = clk_get_rate(imx319->clk);
	if (freq != IMX319_EXT_CLK) {
		ret = -EINVAL;
		goto error_probe;
	}
	v4l2_i2c_subdev_init(&imx319->sd, client, &imx319_subdev_ops);
	ret = imx319_get_power_resources(imx319);
	if (ret)
		goto error_probe;
	imx319->hwcfg = imx319_get_hwcfg(imx319->dev, imx319->profile);
	if (!imx319->hwcfg) {
		ret = -ENODEV;
		goto error_probe;
	}
	imx319->cur_mode = &imx319->profile->modes[0];
	ret = imx319_init_controls(imx319);
	if (ret)
		goto error_probe;
	imx319->sd.internal_ops = &imx319_internal_ops;
	imx319->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE | V4L2_SUBDEV_FL_HAS_EVENTS;
	imx319->sd.entity.ops = &imx319_subdev_entity_ops;
	imx319->sd.entity.function = MEDIA_ENT_F_CAM_SENSOR;
	imx319->pad.flags = MEDIA_PAD_FL_SOURCE;
	ret = media_entity_pads_init(&imx319->sd.entity, 1, &imx319->pad);
	if (ret)
		goto error_handler;
	if (imx319->of_power_resources) {
		ret = imx319_power_on(imx319);
		if (ret)
			goto error_entity;
		full_power = true;
	} else {
		full_power = acpi_dev_state_d0(imx319->dev);
	}
	if (full_power) {
		ret = imx319_identify_module(imx319);
		if (ret)
			goto error_power;
		ret = pm_runtime_set_active(imx319->dev);
		if (ret)
			goto error_power;
	}
	if (imx319->of_power_resources) {
		pm_runtime_get_noresume(imx319->dev);
		probe_reference = true;
		pm_runtime_set_autosuspend_delay(imx319->dev, 1000);
		pm_runtime_use_autosuspend(imx319->dev);
	}
	pm_runtime_enable(imx319->dev);
	ret = v4l2_async_register_subdev_sensor(&imx319->sd);
	if (ret)
		goto error_pm;
	if (probe_reference) {
		pm_runtime_mark_last_busy(imx319->dev);
		pm_runtime_put_autosuspend(imx319->dev);
	} else {
		pm_runtime_idle(imx319->dev);
	}
	return 0;
error_pm:
	pm_runtime_disable(imx319->dev);
	if (imx319->of_power_resources)
		pm_runtime_dont_use_autosuspend(imx319->dev);
	if (probe_reference)
		pm_runtime_put_noidle(imx319->dev);
error_power:
	cleanup_ret = imx319_power_off(imx319);
	if (cleanup_ret)
		dev_err(imx319->dev, "probe power rollback incomplete: %d\n", cleanup_ret);
	else if (full_power)
		pm_runtime_set_suspended(imx319->dev);
error_entity:
	media_entity_cleanup(&imx319->sd.entity);
error_handler:
	v4l2_ctrl_handler_free(&imx319->ctrl_handler);
error_probe:
	mutex_destroy(&imx319->mutex);
	return dev_err_probe(&client->dev, ret, "sensor probe failed\n");
}

static void imx319_remove(struct i2c_client *client)
{
	struct v4l2_subdev *sd = i2c_get_clientdata(client);
	struct imx319 *imx319 = to_imx319(sd);
	int ret;

	v4l2_async_unregister_subdev(sd);
	mutex_lock(&imx319->mutex);
	imx319->removing = true;
	mutex_unlock(&imx319->mutex);
	imx319_set_stream(sd, 0);
	pm_runtime_disable(imx319->dev);
	if (imx319->of_power_resources)
		pm_runtime_dont_use_autosuspend(imx319->dev);
	ret = imx319_power_off(imx319);
	if (ret)
		dev_err(imx319->dev, "remove power rollback incomplete: %d\n", ret);
	else if (!pm_runtime_status_suspended(imx319->dev))
		pm_runtime_set_suspended(imx319->dev);
	media_entity_cleanup(&sd->entity);
	v4l2_ctrl_handler_free(sd->ctrl_handler);
	mutex_destroy(&imx319->mutex);
}
