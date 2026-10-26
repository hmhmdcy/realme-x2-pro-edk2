/* RMX1931: PM callbacks are serialized by runtime PM, never take state_lock. */
static int s5k3m5_match_lab_child(struct device *child, const void *unused)
{
	(void)unused;
	return child->bus == &platform_bus_type &&
		str_has_prefix(dev_name(child), "pm8008-reg-lab1246.");
}

static int s5k3m5_rmx_resources(struct s5k3m5 *sensor)
{
	struct device *dev = sensor->dev;
	struct device_node *vana, *vdig, *va_parent, *vd_parent, *pmic;
	struct i2c_client *client;
	struct device *supplier;
	struct device_link *link;
	unsigned int i;
	int ret = -EINVAL;

	if (!of_machine_is_compatible("realme,samurai") ||
	    of_property_count_u32_elems(dev->of_node, "vdda-supply") != 1 ||
	    of_property_count_u32_elems(dev->of_node, "vddd-supply") != 1 ||
	    of_property_count_u32_elems(dev->of_node, "vddio-supply") != 1 ||
	    of_property_present(dev->of_node, "afvdd-supply") ||
	    of_property_count_u32_elems(dev->of_node, "power-domains") != 2)
		return -EINVAL;
	vana = of_parse_phandle(dev->of_node, "vdda-supply", 0);
	vdig = of_parse_phandle(dev->of_node, "vddd-supply", 0);
	if (!vana || !vdig)
		goto put_nodes;
	va_parent = of_get_parent(vana);
	vd_parent = of_get_parent(vdig);
	if (!va_parent || va_parent != vd_parent ||
	    !of_node_name_eq(vana, "ldo6") || !of_node_name_eq(vdig, "ldo2"))
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
	supplier = device_find_child(&client->dev, NULL, s5k3m5_match_lab_child);
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
	if (ret)
		return ret;
	sensor->reset_gpio = devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(sensor->reset_gpio))
		return PTR_ERR(sensor->reset_gpio);
	/* Index0 is deliberately unused: AF has its own independent consumer. */
	for (i = 1; i < S5K3M5_NUM_SUPPLIES; i++) {
		sensor->supplies[i].supply = s5k3m5_supply_names[i];
		sensor->supplies[i].consumer = devm_regulator_get(dev, s5k3m5_supply_names[i]);
		if (IS_ERR(sensor->supplies[i].consumer))
			return PTR_ERR(sensor->supplies[i].consumer);
	}
	ret = regulator_set_voltage(sensor->supplies[1].consumer, 2800000, 2800000);
	if (ret)
		return ret;
	ret = regulator_set_voltage(sensor->supplies[2].consumer, 1056000, 1056000);
	if (ret)
		return ret;
	ret = regulator_get_voltage(sensor->supplies[3].consumer);
	return ret == 1800000 ? 0 : ret < 0 ? ret : -EINVAL;
}

static int s5k3m5_rmx_power_off(struct s5k3m5 *sensor)
{
	/* OEM order: MCLK, RESET low, VIO, VANA, VDIG. */
	static const unsigned int order[] = { 3, 1, 2 };
	unsigned int i, index;
	int ret, first = 0;

	if (sensor->clock_enabled) {
		clk_disable_unprepare(sensor->mclk);
		sensor->clock_enabled = false;
	}
	usleep_range(1000, 1100);
	ret = gpiod_set_value_cansleep(sensor->reset_gpio, 1);
	if (ret)
		first = ret;
	usleep_range(1000, 1100);
	for (i = 0; i < ARRAY_SIZE(order); i++) {
		index = order[i];
		if (!sensor->supply_enabled[index])
			continue;
		ret = regulator_disable(sensor->supplies[index].consumer);
		if (!ret)
			sensor->supply_enabled[index] = false;
		else if (!first)
			first = ret;
	}
	ret = pinctrl_pm_select_sleep_state(sensor->dev);
	if (ret && !first)
		first = ret;
	if (first)
		sensor->power_fault = true;
	return first;
}

static int s5k3m5_rmx_power_on(struct s5k3m5 *sensor)
{
	static const unsigned int order[] = { 3, 1, 2 };
	unsigned int i, index;
	int ret, cleanup_ret;
	bool lease_busy;

	if (sensor->power_fault || sensor->clock_enabled || sensor->supply_enabled[1] ||
	    sensor->supply_enabled[2] || sensor->supply_enabled[3])
		return -EIO;
	ret = pinctrl_pm_select_default_state(sensor->dev);
	if (ret)
		goto failed;
	ret = gpiod_set_value_cansleep(sensor->reset_gpio, 1);
	if (ret)
		goto failed;
	usleep_range(1000, 1100);
	for (i = 0; i < ARRAY_SIZE(order); i++) {
		index = order[i];
		ret = regulator_enable(sensor->supplies[index].consumer);
		if (ret)
			goto failed;
		sensor->supply_enabled[index] = true;
		usleep_range(1000, 1100);
	}
	/* OEM custom1/custom2 have no valid GPIO; keep their two 1ms waits. */
	usleep_range(2000, 2200);
	ret = gpiod_set_value_cansleep(sensor->reset_gpio, 0);
	if (ret)
		goto failed;
	usleep_range(5000, 5500);
	ret = clk_prepare_enable(sensor->mclk);
	if (ret)
		goto failed;
	sensor->clock_enabled = true;
	usleep_range(1000, 1100);
	return 0;
failed:
	/* A first-P-output lease conflict is retryable after our own rollback. */
	lease_busy = ret == -EBUSY && !sensor->supply_enabled[1] && !sensor->supply_enabled[2];
	if (!lease_busy)
		sensor->power_fault = true;
	cleanup_ret = s5k3m5_rmx_power_off(sensor);
	if (cleanup_ret)
		dev_err(sensor->dev, "power rollback incomplete: %d\n", cleanup_ret);
	return ret;
}

static void s5k3m5_rmx_cleanup(void *data)
{
	struct s5k3m5 *sensor = data;
	int ret;

	if (!sensor->clock_enabled && !sensor->supply_enabled[1] &&
	    !sensor->supply_enabled[2] && !sensor->supply_enabled[3])
		return;
	ret = s5k3m5_rmx_power_off(sensor);
	if (ret)
		dev_err(sensor->dev, "managed cleanup incomplete, P fault remains latched: %d\n", ret);
}
