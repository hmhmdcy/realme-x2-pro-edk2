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
