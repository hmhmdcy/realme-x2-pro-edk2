/* RMX1931 resources: runtime callbacks never acquire the controls mutex. */
static int imx319_match_lab_child(struct device *child, const void *unused)
{
	(void)unused;
	return child->bus == &platform_bus_type &&
		str_has_prefix(dev_name(child), "pm8008-reg-lab14.");
}

static int imx319_link_lab_supplier(struct imx319 *imx319)
{
	struct device *dev = imx319->dev;
	struct device_node *vana, *vdig, *va_parent, *vd_parent, *pmic;
	struct i2c_client *client;
	struct device *supplier;
	struct device_link *link;
	int ret = -EINVAL;

	vana = of_parse_phandle(dev->of_node, "vana-supply", 0);
	vdig = of_parse_phandle(dev->of_node, "vdig-supply", 0);
	if (!vana || !vdig)
		goto put_nodes;
	va_parent = of_get_parent(vana);
	vd_parent = of_get_parent(vdig);
	if (!va_parent || va_parent != vd_parent ||
	    !of_node_name_eq(vana, "ldo4") || !of_node_name_eq(vdig, "ldo1"))
		goto put_parents;
	pmic = of_get_parent(va_parent);
	if (!pmic)
		goto put_parents;
	client = i2c_find_device_by_fwnode(of_fwnode_handle(pmic));
	of_node_put(pmic);
	if (!client) {
		ret = -EPROBE_DEFER;
		goto put_parents;
	}
	supplier = device_find_child(&client->dev, NULL, imx319_match_lab_child);
	put_device(&client->dev);
	if (!supplier) {
		ret = -EPROBE_DEFER;
		goto put_parents;
	}
	device_lock(supplier);
	if (!device_is_bound(supplier) ||
	    READ_ONCE(supplier->links.status) != DL_DEV_DRIVER_BOUND)
		ret = -EPROBE_DEFER;
	else if (!supplier->driver || strcmp(supplier->driver->name, "pm8008-imx319-lab"))
		ret = -EINVAL;
	else {
		link = device_link_add(dev, supplier, DL_FLAG_AUTOPROBE_CONSUMER);
		ret = link ? 0 : -EINVAL;
	}
	device_unlock(supplier);
	put_device(supplier);
put_parents:
	of_node_put(va_parent);
	of_node_put(vd_parent);
put_nodes:
	of_node_put(vana);
	of_node_put(vdig);
	return ret;
}

static int imx319_get_power_resources(struct imx319 *imx319)
{
	struct device *dev = imx319->dev;
	int ret;

	if (!dev->of_node)
		return 0;
	if (!of_device_is_compatible(dev->of_node, "realme,rmx1931-imx319") ||
	    !of_machine_is_compatible("realme,samurai") ||
	    of_property_count_u32_elems(dev->of_node, "vana-supply") != 1 ||
	    of_property_count_u32_elems(dev->of_node, "vdig-supply") != 1 ||
	    of_property_count_u32_elems(dev->of_node, "vif-supply") != 1 ||
	    of_property_count_u32_elems(dev->of_node, "power-domains") != 2)
		return -EINVAL;
	ret = imx319_link_lab_supplier(imx319);
	if (ret)
		return ret;
	imx319->reset_gpio = devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(imx319->reset_gpio))
		return PTR_ERR(imx319->reset_gpio);
	imx319->vana = devm_regulator_get(dev, "vana");
	if (IS_ERR(imx319->vana))
		return PTR_ERR(imx319->vana);
	imx319->vdig = devm_regulator_get(dev, "vdig");
	if (IS_ERR(imx319->vdig))
		return PTR_ERR(imx319->vdig);
	imx319->vif = devm_regulator_get(dev, "vif");
	if (IS_ERR(imx319->vif))
		return PTR_ERR(imx319->vif);
	ret = regulator_set_voltage(imx319->vana, 2800000, 2800000);
	if (ret)
		return ret;
	ret = regulator_set_voltage(imx319->vdig, 1104000, 1104000);
	if (ret)
		return ret;
	ret = regulator_get_voltage(imx319->vif);
	if (ret != 1800000)
		return ret < 0 ? ret : -EINVAL;
	imx319->of_power_resources = true;
	return 0;
}

static int imx319_power_off(struct imx319 *imx319)
{
	int ret, first = 0;

	if (!imx319->of_power_resources)
		return 0;
	if (imx319->clock_enabled) {
		clk_disable_unprepare(imx319->clk);
		imx319->clock_enabled = false;
	}
	usleep_range(1000, 1100);
	ret = gpiod_set_value_cansleep(imx319->reset_gpio, 1);
	if (ret)
		first = ret;
	imx319->identified = false;
	usleep_range(1000, 1100);
	if (imx319->vif_enabled) {
		ret = regulator_disable(imx319->vif);
		if (!ret)
			imx319->vif_enabled = false;
		else if (!first)
			first = ret;
	}
	if (imx319->vdig_enabled) {
		ret = regulator_disable(imx319->vdig);
		if (!ret)
			imx319->vdig_enabled = false;
		else if (!first)
			first = ret;
	}
	if (imx319->vana_enabled) {
		ret = regulator_disable(imx319->vana);
		if (!ret)
			imx319->vana_enabled = false;
		else if (!first)
			first = ret;
	}
	ret = pinctrl_pm_select_sleep_state(imx319->dev);
	if (ret && !first)
		first = ret;
	if (first)
		imx319->power_fault = true;
	return first;
}

static int imx319_power_on(struct imx319 *imx319)
{
	int ret, cleanup_ret;

	if (!imx319->of_power_resources)
		return 0;
	if (imx319->power_fault || imx319->vana_enabled || imx319->vdig_enabled ||
	    imx319->vif_enabled || imx319->clock_enabled)
		return -EIO;
	ret = pinctrl_pm_select_default_state(imx319->dev);
	if (ret) {
		imx319->power_fault = true;
		return ret;
	}
	ret = gpiod_set_value_cansleep(imx319->reset_gpio, 1);
	if (ret) {
		imx319->power_fault = true;
		return ret;
	}
	usleep_range(1000, 1100);
	ret = regulator_enable(imx319->vana);
	if (ret)
		goto failed;
	imx319->vana_enabled = true;
	usleep_range(1000, 1100);
	ret = regulator_enable(imx319->vdig);
	if (ret)
		goto failed;
	imx319->vdig_enabled = true;
	usleep_range(1000, 1100);
	ret = regulator_enable(imx319->vif);
	if (ret)
		goto failed;
	imx319->vif_enabled = true;
	ret = clk_prepare_enable(imx319->clk);
	if (ret)
		goto failed;
	imx319->clock_enabled = true;
	usleep_range(1000, 1100);
	ret = gpiod_set_value_cansleep(imx319->reset_gpio, 0);
	if (ret)
		goto failed;
	usleep_range(18000, 19000);
	return 0;
failed:
	imx319->power_fault = true;
	cleanup_ret = imx319_power_off(imx319);
	if (cleanup_ret)
		dev_err(imx319->dev, "power rollback incomplete: %d\n", cleanup_ret);
	return ret;
}

static int imx319_runtime_resume(struct device *dev)
{
	return imx319_power_on(to_imx319(dev_get_drvdata(dev)));
}

static int imx319_runtime_suspend(struct device *dev)
{
	return imx319_power_off(to_imx319(dev_get_drvdata(dev)));
}

static const struct dev_pm_ops imx319_pm_ops = {
	SET_RUNTIME_PM_OPS(imx319_runtime_suspend, imx319_runtime_resume, NULL)
};
