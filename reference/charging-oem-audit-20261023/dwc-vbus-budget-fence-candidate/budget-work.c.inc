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
