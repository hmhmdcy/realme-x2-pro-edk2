static int dwc3_gadget_vbus_draw(struct usb_gadget *g, unsigned int mA)
{
	struct dwc3		*dwc = gadget_to_dwc(g);
	unsigned long		flags;

	if (dwc->usb2_phy)
		return usb_phy_set_power(dwc->usb2_phy, mA);

	spin_lock_irqsave(&dwc->lock, flags);
	if (dwc->vbus_draw_blocked) {
		spin_unlock_irqrestore(&dwc->lock, flags);
		return -EBUSY;
	}
	if (!dwc->usb_psy) {
		if (!dwc->psy_nb.notifier_call) {
			spin_unlock_irqrestore(&dwc->lock, flags);
			return -EOPNOTSUPP;
		}
		dwc->current_limit = mA;
		spin_unlock_irqrestore(&dwc->lock, flags);
		dev_dbg(dwc->dev, "Stored VBUS draw: %u mA (power supply not ready)\n", mA);
		return 0;
	}

	dwc->current_limit = mA;
	schedule_work(&dwc->vbus_draw_work);
	spin_unlock_irqrestore(&dwc->lock, flags);

	return 0;
}
