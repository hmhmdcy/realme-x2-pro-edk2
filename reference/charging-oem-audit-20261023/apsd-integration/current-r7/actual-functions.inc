static int qcom_snps_hsphy_set_mode(struct phy *phy, enum phy_mode mode,
				    int submode)
{
	struct qcom_snps_hsphy *hsphy = phy_get_drvdata(phy);

	hsphy->mode = mode;
	return 0;
}

int phy_set_mode_ext(struct phy *phy, enum phy_mode mode, int submode)
{
	int ret = 0;

	if (!phy)
		return 0;

	mutex_lock(&phy->mutex);
	if (phy->ops->set_mode)
		ret = phy->ops->set_mode(phy, mode, submode);
	if (!ret)
		phy->attrs.mode = mode;
	mutex_unlock(&phy->mutex);

	return ret;
}

void dwc3_set_mode(struct dwc3 *dwc, u32 mode)
{
	unsigned long flags;

	if (dwc->dr_mode != USB_DR_MODE_OTG)
		return;

	spin_lock_irqsave(&dwc->lock, flags);
	dwc->desired_dr_role = mode;
	spin_unlock_irqrestore(&dwc->lock, flags);

	queue_work(system_freezable_wq, &dwc->drd_work);
}

static int dwc3_usb_role_switch_set(struct usb_role_switch *sw,
				    enum usb_role role)
{
	struct dwc3 *dwc = usb_role_switch_get_drvdata(sw);
	u32 mode;

	switch (role) {
	case USB_ROLE_HOST:
		mode = DWC3_GCTL_PRTCAP_HOST;
		break;
	case USB_ROLE_DEVICE:
		mode = DWC3_GCTL_PRTCAP_DEVICE;
		break;
	default:
		if (dwc->role_switch_default_mode == USB_DR_MODE_HOST)
			mode = DWC3_GCTL_PRTCAP_HOST;
		else
			mode = DWC3_GCTL_PRTCAP_DEVICE;
		break;
	}

	dwc3_pre_set_role(dwc, role);
	dwc3_set_mode(dwc, mode);
	return 0;
}

int usb_role_switch_set_role(struct usb_role_switch *sw, enum usb_role role)
{
	int ret;

	if (IS_ERR_OR_NULL(sw))
		return 0;

	if (!sw->registered)
		return -EOPNOTSUPP;

	mutex_lock(&sw->lock);

	ret = sw->set(sw, role);
	if (!ret) {
		sw->role = role;
		kobject_uevent(&sw->dev.kobj, KOBJ_CHANGE);
	}

	mutex_unlock(&sw->lock);

	return ret;
}

static int dwc3_gadget_pullup(struct usb_gadget *g, int is_on)
{
	struct dwc3		*dwc = gadget_to_dwc(g);
	int			ret;

	is_on = !!is_on;

	dwc->softconnect = is_on;

	/*
	 * Avoid issuing a runtime resume if the device is already in the
	 * suspended state during gadget disconnect.  DWC3 gadget was already
	 * halted/stopped during runtime suspend.
	 */
	if (!is_on) {
		pm_runtime_barrier(dwc->dev);
		if (pm_runtime_suspended(dwc->dev))
			return 0;
	}

	/*
	 * Check the return value for successful resume, or error.  For a
	 * successful resume, the DWC3 runtime PM resume routine will handle
	 * the run stop sequence, so avoid duplicate operations here.
	 */
	ret = pm_runtime_get_sync(dwc->dev);
	if (!ret || ret < 0) {
		pm_runtime_put(dwc->dev);
		if (ret < 0)
			pm_runtime_set_suspended(dwc->dev);
		return ret;
	}

	if (dwc->pullups_connected == is_on) {
		pm_runtime_put(dwc->dev);
		return 0;
	}

	synchronize_irq(dwc->irq_gadget);

	/* Serialize against dwc3_err_recovery_work() */
	mutex_lock(&dwc->connect_mutex);
	if (!is_on)
		ret = dwc3_gadget_soft_disconnect(dwc);
	else
		ret = dwc3_gadget_soft_connect(dwc);
	mutex_unlock(&dwc->connect_mutex);

	pm_runtime_put(dwc->dev);

	return ret;
}

static int usb_gadget_connect_locked(struct usb_gadget *gadget)
	__must_hold(&gadget->udc->connect_lock)
{
	int ret = 0;

	if (!gadget->ops->pullup) {
		ret = -EOPNOTSUPP;
		goto out;
	}

	if (gadget->connected)
		goto out;

	if (gadget->deactivated || !gadget->udc->allow_connect || !gadget->udc->started) {
		/*
		 * If the gadget isn't usable (because it is deactivated,
		 * unbound, or not yet started), we only save the new state.
		 * The gadget will be connected automatically when it is
		 * activated/bound/started.
		 */
		gadget->connected = true;
		goto out;
	}

	ret = gadget->ops->pullup(gadget, 1);
	if (!ret)
		gadget->connected = 1;

out:
	trace_usb_gadget_connect(gadget, ret);

	return ret;
}

static int usb_gadget_disconnect_locked(struct usb_gadget *gadget)
	__must_hold(&gadget->udc->connect_lock)
{
	int ret = 0;

	if (!gadget->ops->pullup) {
		ret = -EOPNOTSUPP;
		goto out;
	}

	if (!gadget->connected)
		goto out;

	if (gadget->deactivated || !gadget->udc->started) {
		/*
		 * If gadget is deactivated we only save new state.
		 * Gadget will stay disconnected after activation.
		 */
		gadget->connected = false;
		goto out;
	}

	ret = gadget->ops->pullup(gadget, 0);
	if (!ret)
		gadget->connected = 0;

	mutex_lock(&udc_lock);
	if (gadget->udc->driver)
		gadget->udc->driver->disconnect(gadget);
	mutex_unlock(&udc_lock);

out:
	trace_usb_gadget_disconnect(gadget, ret);

	return ret;
}

int usb_gadget_deactivate(struct usb_gadget *gadget)
{
	int ret = 0;

	mutex_lock(&gadget->udc->connect_lock);
	if (gadget->deactivated)
		goto unlock;

	if (gadget->connected) {
		ret = usb_gadget_disconnect_locked(gadget);
		if (ret)
			goto unlock;

		/*
		 * If gadget was being connected before deactivation, we want
		 * to reconnect it in usb_gadget_activate().
		 */
		gadget->connected = true;
	}
	gadget->deactivated = true;

unlock:
	mutex_unlock(&gadget->udc->connect_lock);
	trace_usb_gadget_deactivate(gadget, ret);

	return ret;
}

int usb_gadget_activate(struct usb_gadget *gadget)
{
	int ret = 0;

	mutex_lock(&gadget->udc->connect_lock);
	if (!gadget->deactivated)
		goto unlock;

	gadget->deactivated = false;

	/*
	 * If gadget has been connected before deactivation, or became connected
	 * while it was being deactivated, we call usb_gadget_connect().
	 */
	if (gadget->connected) {
		gadget->connected = false;
		ret = usb_gadget_connect_locked(gadget);
	}

unlock:
	mutex_unlock(&gadget->udc->connect_lock);
	trace_usb_gadget_activate(gadget, ret);

	return ret;
}
