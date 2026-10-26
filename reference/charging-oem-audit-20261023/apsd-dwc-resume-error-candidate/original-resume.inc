static int dwc3_resume_common(struct dwc3 *dwc, pm_message_t msg)
{
	int		ret;
	u32		reg;
	int		i;

	ret = dwc3_gadget_window_pm_enter(dwc);
	if (ret)
		return ret;

	switch (dwc->current_dr_role) {
	case DWC3_GCTL_PRTCAP_DEVICE:
		ret = dwc3_core_init_for_resume(dwc);
		if (ret)
			goto out;

		dwc3_set_prtcap(dwc, DWC3_GCTL_PRTCAP_DEVICE, true);
		dwc3_gadget_resume(dwc);
		break;
	case DWC3_GCTL_PRTCAP_HOST:
		if (!PMSG_IS_AUTO(msg) &&
		    (!device_may_wakeup(dwc->dev) || dwc->needs_full_reinit)) {
			ret = dwc3_core_init_for_resume(dwc);
			if (ret)
				goto out;
			dwc3_set_prtcap(dwc, DWC3_GCTL_PRTCAP_HOST, true);
			break;
		}
		/* Restore GUSB2PHYCFG bits that were modified in suspend */
		for (i = 0; i < dwc->num_usb2_ports; i++) {
			reg = dwc3_readl(dwc, DWC3_GUSB2PHYCFG(i));
			if (dwc->dis_u2_susphy_quirk)
				reg &= ~DWC3_GUSB2PHYCFG_SUSPHY;

			if (dwc->dis_enblslpm_quirk)
				reg &= ~DWC3_GUSB2PHYCFG_ENBLSLPM;

			dwc3_writel(dwc, DWC3_GUSB2PHYCFG(i), reg);
		}

		for (i = 0; i < dwc->num_usb2_ports; i++)
			phy_pm_runtime_get_sync(dwc->usb2_generic_phy[i]);
		for (i = 0; i < dwc->num_usb3_ports; i++)
			phy_pm_runtime_get_sync(dwc->usb3_generic_phy[i]);
		break;
	case DWC3_GCTL_PRTCAP_OTG:
		/* nothing to do on runtime_resume */
		if (PMSG_IS_AUTO(msg))
			break;

		ret = dwc3_core_init_for_resume(dwc);
		if (ret)
			goto out;

		dwc3_set_prtcap(dwc, dwc->current_dr_role, true);

		dwc3_otg_init(dwc);
		if (dwc->current_otg_role == DWC3_OTG_ROLE_HOST) {
			dwc3_otg_host_init(dwc);
		} else if (dwc->current_otg_role == DWC3_OTG_ROLE_DEVICE) {
			dwc3_gadget_resume(dwc);
		}

		break;
	default:
		/* do nothing */
		break;
	}

	if (!PMSG_IS_AUTO(msg)) {
		/* restore SUSPHY state to that before system suspend. */
		dwc3_enable_susphy(dwc, dwc->susphy_state);
	}

	ret = 0;
out:
	dwc3_gadget_window_pm_exit(dwc);
	return ret;
}
