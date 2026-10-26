/* Stack-only ownership of SUSPHY bits changed by this suspend attempt.
 * No IRQ, core, PHY or PM lifetime is owned by this record.
 */
struct dwc3_suspend_susphy {
	u32 usb2_saved, usb3_saved;
	u32 usb2_changed, usb3_changed;
};

void dwc3_enable_susphy(struct dwc3 *dwc, bool enable)
{
	u32 reg;
	int i;

	for (i = 0; i < dwc->num_usb3_ports; i++) {
		reg = dwc3_readl(dwc, DWC3_GUSB3PIPECTL(i));
		if (enable && !dwc->dis_u3_susphy_quirk)
			reg |= DWC3_GUSB3PIPECTL_SUSPHY;
		else
			reg &= ~DWC3_GUSB3PIPECTL_SUSPHY;

		dwc3_writel(dwc, DWC3_GUSB3PIPECTL(i), reg);
	}

	for (i = 0; i < dwc->num_usb2_ports; i++) {
		reg = dwc3_readl(dwc, DWC3_GUSB2PHYCFG(i));
		if (enable && !dwc->dis_u2_susphy_quirk)
			reg |= DWC3_GUSB2PHYCFG_SUSPHY;
		else
			reg &= ~DWC3_GUSB2PHYCFG_SUSPHY;

		dwc3_writel(dwc, DWC3_GUSB2PHYCFG(i), reg);
	}
}
static void dwc3_suspend_susphy_enable(struct dwc3 *dwc,
				       struct dwc3_suspend_susphy *saved)
{
	u32 reg, next;
	int i;

	/* Match dwc3_enable_susphy(true), recording the actual same-read delta.
	 * In particular, an enable request can clear a bit under a quirk.
	 */
	for (i = 0; i < dwc->num_usb3_ports; i++) {
		reg = dwc3_readl(dwc, DWC3_GUSB3PIPECTL(i));
		if (reg & DWC3_GUSB3PIPECTL_SUSPHY)
			saved->usb3_saved |= BIT(i);
		next = dwc->dis_u3_susphy_quirk ?
			reg & ~DWC3_GUSB3PIPECTL_SUSPHY : reg | DWC3_GUSB3PIPECTL_SUSPHY;
		if (next != reg)
			saved->usb3_changed |= BIT(i);
		dwc3_writel(dwc, DWC3_GUSB3PIPECTL(i), next);
	}
	for (i = 0; i < dwc->num_usb2_ports; i++) {
		reg = dwc3_readl(dwc, DWC3_GUSB2PHYCFG(i));
		if (reg & DWC3_GUSB2PHYCFG_SUSPHY)
			saved->usb2_saved |= BIT(i);
		next = dwc->dis_u2_susphy_quirk ?
			reg & ~DWC3_GUSB2PHYCFG_SUSPHY : reg | DWC3_GUSB2PHYCFG_SUSPHY;
		if (next != reg)
			saved->usb2_changed |= BIT(i);
		dwc3_writel(dwc, DWC3_GUSB2PHYCFG(i), next);
	}
}
static void dwc3_suspend_susphy_restore(struct dwc3 *dwc,
					struct dwc3_suspend_susphy *saved)
{
	u32 reg, next;
	int i;

	/* The callback failed before core_exit. Keep all resources ACTIVE and
	 * undo only this attempt's changed bits, preserving other current bits.
	 */
	for (i = 0; i < dwc->num_usb3_ports; i++) {
		if (!(saved->usb3_changed & BIT(i)))
			continue;
		reg = dwc3_readl(dwc, DWC3_GUSB3PIPECTL(i));
		next = (reg & ~DWC3_GUSB3PIPECTL_SUSPHY) |
			(saved->usb3_saved & BIT(i) ? DWC3_GUSB3PIPECTL_SUSPHY : 0);
		if (next != reg)
			dwc3_writel(dwc, DWC3_GUSB3PIPECTL(i), next);
	}
	for (i = 0; i < dwc->num_usb2_ports; i++) {
		if (!(saved->usb2_changed & BIT(i)))
			continue;
		reg = dwc3_readl(dwc, DWC3_GUSB2PHYCFG(i));
		next = (reg & ~DWC3_GUSB2PHYCFG_SUSPHY) |
			(saved->usb2_saved & BIT(i) ? DWC3_GUSB2PHYCFG_SUSPHY : 0);
		if (next != reg)
			dwc3_writel(dwc, DWC3_GUSB2PHYCFG(i), next);
	}
}
static int dwc3_suspend_common(struct dwc3 *dwc, pm_message_t msg)
{
	struct dwc3_suspend_susphy saved_susphy = { 0 };
	u32 reg;
	int i;
	int ret;

	if (!pm_runtime_suspended(dwc->dev) && !PMSG_IS_AUTO(msg)) {
		dwc->susphy_state = (dwc->num_usb2_ports && (dwc3_readl(dwc, DWC3_GUSB2PHYCFG(0)) &
				    DWC3_GUSB2PHYCFG_SUSPHY)) ||
				    (dwc->num_usb3_ports && (dwc3_readl(dwc, DWC3_GUSB3PIPECTL(0)) &
				    DWC3_GUSB3PIPECTL_SUSPHY));
		/*
		 * TI AM62 platform requires SUSPHY to be
		 * enabled for system suspend to work.
		 */
		if (!dwc->susphy_state) {
			if (dwc->current_dr_role == DWC3_GCTL_PRTCAP_DEVICE ||
			    (dwc->current_dr_role == DWC3_GCTL_PRTCAP_OTG &&
			     dwc->current_otg_role == DWC3_OTG_ROLE_DEVICE))
				dwc3_suspend_susphy_enable(dwc, &saved_susphy);
			else
				dwc3_enable_susphy(dwc, true);
		}
	}

	switch (dwc->current_dr_role) {
	case DWC3_GCTL_PRTCAP_DEVICE:
		if (pm_runtime_suspended(dwc->dev))
			break;
		ret = dwc3_gadget_suspend(dwc);
		if (ret)
			goto restore_susphy;
		synchronize_irq(dwc->irq_gadget);
		dwc3_core_exit(dwc);
		break;
	case DWC3_GCTL_PRTCAP_HOST:
		if (!PMSG_IS_AUTO(msg) &&
		    (!device_may_wakeup(dwc->dev) || dwc->needs_full_reinit)) {
			dwc3_core_exit(dwc);
			break;
		}

		/* Let controller to suspend HSPHY before PHY driver suspends */
		if (dwc->dis_u2_susphy_quirk ||
		    dwc->dis_enblslpm_quirk) {
			for (i = 0; i < dwc->num_usb2_ports; i++) {
				reg = dwc3_readl(dwc, DWC3_GUSB2PHYCFG(i));
				reg |=  DWC3_GUSB2PHYCFG_ENBLSLPM |
					DWC3_GUSB2PHYCFG_SUSPHY;
				dwc3_writel(dwc, DWC3_GUSB2PHYCFG(i), reg);
			}

			/* Give some time for USB2 PHY to suspend */
			usleep_range(5000, 6000);
		}

		for (i = 0; i < dwc->num_usb2_ports; i++)
			phy_pm_runtime_put_sync(dwc->usb2_generic_phy[i]);
		for (i = 0; i < dwc->num_usb3_ports; i++)
			phy_pm_runtime_put_sync(dwc->usb3_generic_phy[i]);
		break;
	case DWC3_GCTL_PRTCAP_OTG:
		/* do nothing during runtime_suspend */
		if (PMSG_IS_AUTO(msg))
			break;

		if (dwc->current_otg_role == DWC3_OTG_ROLE_DEVICE) {
			ret = dwc3_gadget_suspend(dwc);
			if (ret)
				goto restore_susphy;
			synchronize_irq(dwc->irq_gadget);
		}

		dwc3_otg_exit(dwc);
		dwc3_core_exit(dwc);
		break;
	default:
		/* do nothing */
		break;
	}

	return 0;
restore_susphy:
	dwc3_suspend_susphy_restore(dwc, &saved_susphy);
	return ret;
}
static int dwc3_runtime_checks(struct dwc3 *dwc)
{
	switch (dwc->current_dr_role) {
	case DWC3_GCTL_PRTCAP_DEVICE:
		if (dwc->connected)
			return -EBUSY;
		break;
	case DWC3_GCTL_PRTCAP_HOST:
	default:
		/* do nothing */
		break;
	}

	return 0;
}
int dwc3_runtime_suspend(struct dwc3 *dwc)
{
	int		ret;

	if (dwc3_runtime_checks(dwc))
		return -EBUSY;

	ret = dwc3_suspend_common(dwc, PMSG_AUTO_SUSPEND);
	if (ret)
		return ret;

	return 0;
}
int dwc3_pm_suspend(struct dwc3 *dwc)
{
	struct device *dev = dwc->dev;
	int		ret;

	ret = dwc3_suspend_common(dwc, PMSG_SUSPEND);
	if (ret)
		return ret;

	pinctrl_pm_select_sleep_state(dev);

	return 0;
}
int dwc3_gadget_suspend(struct dwc3 *dwc)
{
	int ret;

	ret = dwc3_gadget_soft_disconnect(dwc);
	/*
	 * Attempt to reset the controller's state. Likely no
	 * communication can be established until the host
	 * performs a port reset.
	 */
	if (ret && dwc->softconnect) {
		dwc3_gadget_soft_connect(dwc);
		return -EAGAIN;
	}

	dwc3_disconnect_gadget_sleepable(dwc);

	return 0;
}
