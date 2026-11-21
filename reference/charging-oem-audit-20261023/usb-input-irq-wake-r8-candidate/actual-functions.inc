static void samurai_usb_stop(void *data)
{
	struct samurai_usb_input *input = data;

	mutex_lock(&input->lock);
	input->paused = true;
	input->udc_valid = false;
	mutex_unlock(&input->lock);
	cancel_delayed_work_sync(&input->work);
}

static int samurai_usb_clear_wake(struct samurai_usb_input *input)
{
	int i, ret, first = 0;

	for (i = ARRAY_SIZE(input->event_irqs) - 1; i >= 0; i--) {
		if (!(input->wake_armed & BIT(i)))
			continue;
		ret = disable_irq_wake(input->event_irqs[i]);
		if (ret) {
			if (!first)
				first = ret;
			continue;
		}
		input->wake_armed &= ~BIT(i);
	}
	return first;
}

static int samurai_usb_arm_wake(struct samurai_usb_input *input)
{
	int i, ret;

	if (!input->psy || !device_may_wakeup(&input->psy->dev))
		return 0;
	for (i = 0; i < ARRAY_SIZE(input->event_irqs); i++) {
		if (input->event_irqs[i] <= 0)
			continue;
		ret = enable_irq_wake(input->event_irqs[i]);
		if (ret)
			return ret;
		input->wake_armed |= BIT(i);
	}
	return 0;
}

static void samurai_usb_restart_work(struct samurai_usb_input *input)
{
	mutex_lock(&input->lock);
	input->udc_valid = false;
	input->paused = false;
	mutex_unlock(&input->lock);
	mod_delayed_work(system_wq, &input->work, 0);
}

static void samurai_usb_cleanup_wake(void *data)
{
	struct samurai_usb_input *input = data;
	int ret = samurai_usb_clear_wake(input);

	if (ret)
		dev_warn(input->event_dev, "USB wake IRQ cleanup failed: %d\n", ret);
}

static int samurai_usb_suspend(struct device *dev)
{
	struct samurai_usb_input *input = dev_get_drvdata(dev);
	int ret, cleanup;

	ret = samurai_usb_clear_wake(input);
	if (ret)
		return ret;
	samurai_usb_stop(input);
	ret = samurai_usb_arm_wake(input);
	if (ret) {
		cleanup = samurai_usb_clear_wake(input);
		if (cleanup)
			dev_warn(dev, "USB wake IRQ unwind failed: %d\n", cleanup);
		samurai_usb_restart_work(input);
	}
	return ret;
}

static int samurai_usb_resume(struct device *dev)
{
	struct samurai_usb_input *input = dev_get_drvdata(dev);
	int ret = samurai_usb_clear_wake(input);

	samurai_usb_restart_work(input);
	return ret;
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

	for (i = 0; i < ARRAY_SIZE(names); i++) {
		ret = devm_request_threaded_irq(&pdev->dev, irqs[i], NULL,
						samurai_usb_event, IRQF_ONESHOT,
						names[i], input);
		if (ret)
			return ret;
		input->event_irqs[i] = irqs[i];
	}
	return 0;
}

static void samurai_usb_shutdown(struct platform_device *pdev)
{
	struct samurai_usb_input *input = platform_get_drvdata(pdev);

	samurai_usb_stop(input);
	samurai_usb_cleanup_wake(input);
}
