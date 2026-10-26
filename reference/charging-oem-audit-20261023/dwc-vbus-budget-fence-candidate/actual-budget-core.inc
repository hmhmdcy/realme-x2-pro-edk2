static void dwc3_vbus_draw_work(struct work_struct *work)
{
	struct dwc3 *dwc = container_of(work, struct dwc3, vbus_draw_work);
	union power_supply_propval val = {0};
	struct power_supply *psy;
	unsigned long flags;
	unsigned int limit;
	bool blocked;
	int ret;

	spin_lock_irqsave(&dwc->lock, flags);
	psy = dwc->usb_psy;
	limit = dwc->current_limit;
	blocked = dwc->vbus_draw_blocked;
	spin_unlock_irqrestore(&dwc->lock, flags);
	if (blocked || !psy || limit == DWC3_CURRENT_UNSPECIFIED)
		return;

	val.intval = 1000 * limit;
	ret = power_supply_set_property(psy, POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT, &val);
	if (ret < 0)
		dev_dbg(dwc->dev, "Error (%d) setting vbus draw (%u mA)\n", ret, limit);
}

static void dwc3_vbus_budget_close(struct dwc3 *dwc)
{
	struct power_supply *psy;
	union power_supply_propval val = { .intval = 0 };
	unsigned long flags;
	int ret;

	/* This work is initialized only after a successful usb-psy-name lookup.
	 * Legacy usb_phy_set_power() and non-DEVICE policies are not changed.
	 */
	if (!dwc->usb_psy_name || dwc->usb2_phy ||
	    dwc->current_dr_role != DWC3_GCTL_PRTCAP_DEVICE)
		return;
	spin_lock_irqsave(&dwc->lock, flags);
	dwc->vbus_draw_blocked = true;
	dwc->current_limit = DWC3_CURRENT_UNSPECIFIED;
	psy = dwc->usb_psy;
	spin_unlock_irqrestore(&dwc->lock, flags);

	/* Join only this software allowance work, with no DWC spinlock held.
	 * A worker may already have captured a positive allowance before close.
	 */
	cancel_work_sync(&dwc->vbus_draw_work);
	if (psy) {
		ret = power_supply_set_property(psy, POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT, &val);
		if (ret < 0)
			dev_warn(dwc->dev, "VBUS budget revoke failed: %d\n", ret);
	}
}

static void dwc3_vbus_budget_open(struct dwc3 *dwc)
{
	unsigned long flags;

	if (!dwc->usb_psy_name || dwc->usb2_phy ||
	    dwc->current_dr_role != DWC3_GCTL_PRTCAP_DEVICE)
		return;
	spin_lock_irqsave(&dwc->lock, flags);
	/* Reopening never schedules or republishes a pre-suspend allowance. */
	dwc->current_limit = DWC3_CURRENT_UNSPECIFIED;
	dwc->vbus_draw_blocked = false;
	spin_unlock_irqrestore(&dwc->lock, flags);
}

static int dwc3_psy_notifier(struct notifier_block *nb,
			     unsigned long event, void *data)
{
	struct dwc3 *dwc = container_of(nb, struct dwc3, psy_nb);
	struct power_supply *psy = data;
	unsigned long flags;

	if (dwc->usb_psy)
		return NOTIFY_DONE;

	if (strcmp(psy->desc->name, dwc->usb_psy_name) != 0)
		return NOTIFY_DONE;

	/* Explicitly get the reference for this psy */
	psy = power_supply_get_by_name(dwc->usb_psy_name);
	if (!psy)
		return NOTIFY_DONE;

	spin_lock_irqsave(&dwc->lock, flags);
	/*
	 * The USB power_supply may already be set. This can happen if notifier
	 * callbacks for the USB power_supply race, or if a previous notifier
	 * callback has already successfully fetched and associated the instance.
	 * In such cases, release the newly acquired reference and ignore
	 * subsequent notifications until the notifier is unregistered.
	 */
	if (dwc->usb_psy) {
		spin_unlock_irqrestore(&dwc->lock, flags);
		power_supply_put(psy);
		return NOTIFY_DONE;
	}

	dwc->usb_psy = psy;
	if (!dwc->vbus_draw_blocked &&
	    dwc->current_limit != DWC3_CURRENT_UNSPECIFIED)
		schedule_work(&dwc->vbus_draw_work);
	spin_unlock_irqrestore(&dwc->lock, flags);

	return NOTIFY_OK;
}

static void dwc3_get_usb_power_supply(struct dwc3 *dwc)
{
	struct power_supply *psy;
	unsigned long flags;
	int ret;

	ret = device_property_read_string(dwc->dev, "usb-psy-name", &dwc->usb_psy_name);
	if (ret < 0)
		return;

	INIT_WORK(&dwc->vbus_draw_work, dwc3_vbus_draw_work);

	dwc->current_limit = DWC3_CURRENT_UNSPECIFIED;
	dwc->vbus_draw_blocked = false;
	dwc->psy_nb.notifier_call = dwc3_psy_notifier;
	ret = power_supply_reg_notifier(&dwc->psy_nb);
	if (ret) {
		dev_err(dwc->dev, "Failed to register power supply notifier: %d\n", ret);
		dwc->psy_nb.notifier_call = NULL;
		return;
	}

	psy = power_supply_get_by_name(dwc->usb_psy_name);
	if (!psy)
		return;

	/* Unregister the notifier now that we have the power supply */
	power_supply_unreg_notifier(&dwc->psy_nb);
	dwc->psy_nb.notifier_call = NULL;

	spin_lock_irqsave(&dwc->lock, flags);
	/*
	 * It is possible that the notifier callback ran before we reached here
	 * and successfully fetched the power supply. In that case we need to
	 * release the above reference.
	 */
	if (dwc->usb_psy) {
		spin_unlock_irqrestore(&dwc->lock, flags);
		power_supply_put(psy);
		return;
	}

	dwc->usb_psy = psy;
	spin_unlock_irqrestore(&dwc->lock, flags);
}

int dwc3_pm_suspend(struct dwc3 *dwc)
{
	struct device *dev = dwc->dev;
	int		ret;

	ret = dwc3_suspend_common(dwc, PMSG_SUSPEND);
	if (ret)
		return ret;

	dwc3_vbus_budget_close(dwc);
	pinctrl_pm_select_sleep_state(dev);

	return 0;
}

int dwc3_pm_resume(struct dwc3 *dwc)
{
	struct device *dev = dwc->dev;
	int		ret = 0;

	pinctrl_pm_select_default_state(dev);

	pm_runtime_disable(dev);
	ret = pm_runtime_set_active(dev);
	if (ret)
		goto out;

	dwc3_vbus_budget_open(dwc);
	ret = dwc3_resume_common(dwc, PMSG_RESUME);
	if (ret)
		pm_runtime_set_suspended(dev);

out:
	if (ret)
		dwc3_vbus_budget_close(dwc);
	pm_runtime_enable(dev);

	return ret;
}
