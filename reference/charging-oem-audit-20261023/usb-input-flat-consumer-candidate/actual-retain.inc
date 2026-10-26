static void samurai_usb_retain_for_native_consumer(struct device *dev)
{
	struct device_node *node;
	const char *name;

	/* DWC3 owns its supply reference for the controller's lifetime. Current
	 * power_supply_unregister() warns if such a reference remains; unloading
	 * this module would also invalidate its property callbacks. Do not permit
	 * that lifecycle after native wiring has been selected in the boot DT.
	 */
	node = of_find_node_by_path("/soc@0/usb@a6f8800/usb@a600000");
	if (node && !of_property_read_string(node, "usb-psy-name", &name) &&
	    !strcmp(name, "samurai-usb-input") && !native_retained) {
		__module_get(THIS_MODULE);
		native_retained = true;
		dev_info(dev, "native DWC3 supply retained until next boot\n");
	}
	of_node_put(node);
	if (native_retained)
		return;

	/* The combined Qualcomm driver owns the same native supply reference
	 * on a flat controller. Never retain for an unavailable or unrelated node.
	 * Keep the established legacy-path selection above unchanged.
	 */
	node = of_find_node_by_path("/soc@0/usb@a600000");
	if (node && of_device_is_available(node) &&
	    of_device_is_compatible(node, "qcom,snps-dwc3") &&
	    !of_property_read_string(node, "usb-psy-name", &name) &&
	    !strcmp(name, "samurai-usb-input")) {
		__module_get(THIS_MODULE);
		native_retained = true;
		dev_info(dev, "native DWC3 supply retained until next boot\n");
	}
	of_node_put(node);
}
