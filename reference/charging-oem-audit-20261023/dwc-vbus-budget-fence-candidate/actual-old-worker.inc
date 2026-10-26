static void old_dwc3_vbus_draw_work(struct work_struct *work)
{
	struct dwc3 *dwc = container_of(work, struct dwc3, vbus_draw_work);
	union power_supply_propval val = {0};
	int ret;

	val.intval = 1000 * (dwc->current_limit);
	ret = power_supply_set_property(dwc->usb_psy, POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT, &val);

	if (ret < 0)
		dev_dbg(dwc->dev, "Error (%d) setting vbus draw (%d mA)\n",
			ret, dwc->current_limit);
}
