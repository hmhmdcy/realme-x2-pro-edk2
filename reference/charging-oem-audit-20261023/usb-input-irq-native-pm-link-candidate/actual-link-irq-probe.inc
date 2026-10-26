static void samurai_usb_unlink_native_consumer(void *data)
{
	struct samurai_usb_input *input = data;

	if (!input->native_consumer)
		return;
	/* device_del() may already have purged the link. Remove by endpoints,
	 * never dereference a saved link pointer after consumer destruction.
	 */
	device_link_remove(input->native_consumer, input->native_supplier);
	put_device(input->native_consumer);
	input->native_consumer = NULL;
}

static int samurai_usb_link_native_consumer(struct device *dev,
					   struct samurai_usb_input *input)
{
	static const char * const paths[] = {
		"/soc@0/usb@a6f8800/usb@a600000", "/soc@0/usb@a600000",
	};
	static const char * const compatibles[] = { "snps,dwc3", "qcom,snps-dwc3" };
	struct device_node *node, *selected = NULL;
	struct platform_device *consumer;
	const char *name;
	unsigned int i;

	/* The parameter native_retained is not proof of a device relationship. */
	for (i = 0; i < ARRAY_SIZE(paths); i++) {
		node = of_find_node_by_path(paths[i]);
		if (node && of_device_is_available(node) &&
		    of_device_is_compatible(node, compatibles[i]) &&
		    !of_property_read_string(node, "usb-psy-name", &name) &&
		    !strcmp(name, "samurai-usb-input")) {
			if (selected) {
				of_node_put(node);
				of_node_put(selected);
				return -EINVAL;
			}
			selected = node;
		} else {
			of_node_put(node);
		}
	}
	if (!selected)
		return 0; /* The existing non-native observer has no DWC PM owner. */
	consumer = of_find_device_by_node(selected);
	of_node_put(selected);
	if (!consumer)
		return -EPROBE_DEFER;
	if (!device_is_registered(&consumer->dev)) {
		put_device(&consumer->dev);
		return -EPROBE_DEFER;
	}
	if (!device_link_add(&consumer->dev, dev, DL_FLAG_STATELESS)) {
		put_device(&consumer->dev);
		return -EINVAL;
	}
	input->native_consumer = &consumer->dev;
	input->native_supplier = dev;
	/* LIFO devres: existing stop, PSY release, this link, then input storage.
	 * The consumer reference survives link purge until this action releases it.
	 */
	return devm_add_action_or_reset(dev, samurai_usb_unlink_native_consumer, input);
}

static irqreturn_t samurai_usb_event(int irq, void *data)
{
	struct samurai_usb_input *input = data;

	mutex_lock(&input->lock);
	if (!input->paused)
		mod_delayed_work(system_wq, &input->work, 0);
	mutex_unlock(&input->lock);
	return IRQ_HANDLED;
}

static int samurai_usb_request_events(struct platform_device *pdev,
				      struct samurai_usb_input *input)
{
	static const char * const names[] = { "usbin-plugin", "usbin-src-change" };
	int irqs[ARRAY_SIZE(names)], i, ret;

	/* A legacy software device has no IRQ resources. Keep its existing 1s
	 * fallback; only a complete named DT pair enables event-driven reads.
	 */
	for (i = 0; i < ARRAY_SIZE(names); i++) {
		irqs[i] = platform_get_irq_byname_optional(pdev, names[i]);
		if (irqs[i] == -EPROBE_DEFER)
			return -EPROBE_DEFER;
	}
	if ((irqs[0] == -ENXIO || irqs[0] == -ENODEV) &&
	    (irqs[1] == -ENXIO || irqs[1] == -ENODEV))
		return 0;
	for (i = 0; i < ARRAY_SIZE(names); i++) {
		if (irqs[i] <= 0)
			return irqs[i] < 0 ? irqs[i] : -EINVAL;
	}
	if (irqs[0] == irqs[1])
		return -EINVAL;
	/* Requested while paused, before publishing the power_supply. A probe
	 * failure therefore cannot queue work against an unpublished supply.
	 */
	for (i = 0; i < ARRAY_SIZE(names); i++) {
		ret = devm_request_threaded_irq(&pdev->dev, irqs[i], NULL,
						samurai_usb_event, IRQF_ONESHOT,
						names[i], input);
		if (ret)
			return ret;
	}
	return 0;
}

static int samurai_usb_probe(struct platform_device *pdev)
{
	struct power_supply_config config = { 0 };
	struct samurai_usb_input *input;
	struct device *dev = &pdev->dev;
	u32 base;
	int ret;

	if (!of_machine_is_compatible("realme,samurai") ||
	    !of_device_is_compatible(dev->parent->of_node, "qcom,pm8150b"))
		return -ENODEV;
	if (!of_node_name_eq(dev->parent->of_node, "pmic") ||
	    of_property_read_u32(dev->parent->of_node, "reg", &base) || base != 2)
		return -ENODEV;
	if (device_property_read_u32(dev, "reg", &base) || base != 0x1300)
		return -EINVAL;
	input = devm_kzalloc(dev, sizeof(*input), GFP_KERNEL);
	if (!input)
		return -ENOMEM;
	input->map = dev_get_regmap(dev->parent, NULL);
	if (!input->map)
		return -ENODEV;
	mutex_init(&input->lock);
	platform_set_drvdata(pdev, input);
	INIT_DELAYED_WORK(&input->work, samurai_usb_poll);
	input->paused = true;
	/* Order system PM before publishing the supply or requesting its IRQs. */
	ret = samurai_usb_link_native_consumer(dev, input);
	if (ret)
		return ret;
	ret = samurai_usb_request_events(pdev, input);
	if (ret)
		return dev_err_probe(dev, ret, "USB input events\n");
	config.drv_data = input;
	/* A runtime software node already has a link named for its platform
	 * parent. Reusing it for a same-named power_supply creates duplicate
	 * sysfs links and unbalanced software-node removal references.
	 * DT nodes retain the established firmware associations.
	 */
	config.fwnode = dev->of_node ? dev_fwnode(dev) : NULL;
	input->psy = devm_power_supply_register(dev, &samurai_usb_desc, &config);
	if (IS_ERR(input->psy))
		return PTR_ERR(input->psy);
	/* LIFO devres: stop polling before the supply and PMIC map are released. */
	ret = devm_add_action_or_reset(dev, samurai_usb_stop, input);
	if (ret)
		return ret;
	mutex_lock(&input->lock);
	input->paused = false;
	schedule_delayed_work(&input->work, 0);
	mutex_unlock(&input->lock);
	samurai_usb_retain_for_native_consumer(dev);
	dev_info(dev, "read-only PM8150B USB input budget registered\n");
	return 0;
}
