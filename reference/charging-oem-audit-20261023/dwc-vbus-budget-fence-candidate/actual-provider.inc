static int samurai_usb_set_property(struct power_supply *psy,
				    enum power_supply_property property,
				    const union power_supply_propval *value)
{
	struct samurai_usb_input *input = power_supply_get_drvdata(psy);
	int ret = 0;

	if (property != POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT) return -EINVAL;
	mutex_lock(&input->lock);
	input->udc_valid = false;
	if (input->paused) ret = -EBUSY;
	else if (value->intval < 0 || value->intval > 500000) ret = -ERANGE;
	else {
		input->udc_current_ua = value->intval;
		input->udc_valid = true;
	}
	mutex_unlock(&input->lock);
	power_supply_changed(psy);
	return ret;
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

static int samurai_usb_suspend(struct device *dev)
{
	samurai_usb_stop(dev_get_drvdata(dev));
	return 0;
}

static int samurai_usb_resume(struct device *dev)
{
	struct samurai_usb_input *input = dev_get_drvdata(dev);
	mutex_lock(&input->lock);
	input->udc_valid = false;
	input->paused = false;
	mutex_unlock(&input->lock);
	mod_delayed_work(system_wq, &input->work, 0);
	return 0;
}
