static int original_suspend_common(struct dwc3 *dwc, pm_message_t msg)
{
	u32 reg;
	int i;
	int ret;

	if (!pm_runtime_suspended(dwc->dev) && !PMSG_IS_AUTO(msg)) {
		dwc->susphy_state = (dwc3_readl(dwc, DWC3_GUSB2PHYCFG(0)) &
				    DWC3_GUSB2PHYCFG_SUSPHY) ||
				    (dwc3_readl(dwc, DWC3_GUSB3PIPECTL(0)) &
				    DWC3_GUSB3PIPECTL_SUSPHY);
		/*
		 * TI AM62 platform requires SUSPHY to be
		 * enabled for system suspend to work.
		 */
		if (!dwc->susphy_state)
			dwc3_enable_susphy(dwc, true);
	}

	switch (dwc->current_dr_role) {
	case DWC3_GCTL_PRTCAP_DEVICE:
		if (pm_runtime_suspended(dwc->dev))
			break;
		ret = dwc3_gadget_suspend(dwc);
		if (ret)
			return ret;
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
				return ret;
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
}
