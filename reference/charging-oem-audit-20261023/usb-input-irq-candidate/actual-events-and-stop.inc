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

static void samurai_usb_stop(void *data)
{
	struct samurai_usb_input *input = data;

	mutex_lock(&input->lock);
	input->paused = true;
	input->udc_valid = false;
	mutex_unlock(&input->lock);
	cancel_delayed_work_sync(&input->work);
}

static void samurai_usb_shutdown(struct platform_device *pdev)
{
	samurai_usb_stop(platform_get_drvdata(pdev));
}
