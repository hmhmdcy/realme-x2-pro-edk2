static int dwc3_clk_enable(struct dwc3 *dwc)
{
	int ret;

	ret = clk_prepare_enable(dwc->bus_clk);
	if (ret)
		return ret;

	ret = clk_prepare_enable(dwc->ref_clk);
	if (ret)
		goto disable_bus_clk;

	ret = clk_prepare_enable(dwc->susp_clk);
	if (ret)
		goto disable_ref_clk;

	ret = clk_prepare_enable(dwc->utmi_clk);
	if (ret)
		goto disable_susp_clk;

	ret = clk_prepare_enable(dwc->pipe_clk);
	if (ret)
		goto disable_utmi_clk;

	return 0;

disable_utmi_clk:
	clk_disable_unprepare(dwc->utmi_clk);
disable_susp_clk:
	clk_disable_unprepare(dwc->susp_clk);
disable_ref_clk:
	clk_disable_unprepare(dwc->ref_clk);
disable_bus_clk:
	clk_disable_unprepare(dwc->bus_clk);
	return ret;
}

static void dwc3_clk_disable(struct dwc3 *dwc)
{
	clk_disable_unprepare(dwc->pipe_clk);
	clk_disable_unprepare(dwc->utmi_clk);
	clk_disable_unprepare(dwc->susp_clk);
	clk_disable_unprepare(dwc->ref_clk);
	clk_disable_unprepare(dwc->bus_clk);
}

void dwc3_core_exit(struct dwc3 *dwc)
{
	dwc3_event_buffers_cleanup(dwc);
	dwc3_phy_power_off(dwc);
	dwc3_phy_exit(dwc);
	dwc3_clk_disable(dwc);
	reset_control_assert(dwc->reset);
}

static int dwc3_core_init_for_resume(struct dwc3 *dwc)
{
	int ret;

	ret = reset_control_deassert(dwc->reset);
	if (ret)
		return ret;

	ret = dwc3_clk_enable(dwc);
	if (ret)
		goto assert_reset;

	ret = dwc3_core_init(dwc);
	if (ret)
		goto disable_clks;

	return 0;

disable_clks:
	dwc3_clk_disable(dwc);
assert_reset:
	reset_control_assert(dwc->reset);

	return ret;
}

static int dwc3_gadget_soft_connect(struct dwc3 *dwc)
{
	int ret;

	/*
	 * In the Synopsys DWC_usb31 1.90a programming guide section
	 * 4.1.9, it specifies that for a reconnect after a
	 * device-initiated disconnect requires a core soft reset
	 * (DCTL.CSftRst) before enabling the run/stop bit.
	 */
	ret = dwc3_core_soft_reset(dwc);
	if (ret)
		return ret;

	dwc3_event_buffers_setup(dwc);
	__dwc3_gadget_start(dwc);
	return dwc3_gadget_run_stop(dwc, true);
}

int dwc3_gadget_resume(struct dwc3 *dwc)
{
	if (dwc3_gadget_window_busy(dwc))
		return -EBUSY;

	if (!dwc->gadget_driver || !dwc->softconnect)
		return 0;

	return dwc3_gadget_soft_connect(dwc);
}

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
		ret = dwc3_gadget_resume(dwc);
		if (ret)
			goto out;
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
			ret = dwc3_gadget_resume(dwc);
			if (ret)
				goto out;
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

int dwc3_runtime_resume(struct dwc3 *dwc)
{
	struct device *dev = dwc->dev;
	int		ret;

	ret = dwc3_resume_common(dwc, PMSG_AUTO_RESUME);
	if (ret)
		return ret;

	switch (dwc->current_dr_role) {
	case DWC3_GCTL_PRTCAP_DEVICE:
		if (dwc->pending_events) {
			pm_runtime_put(dev);
			dwc->pending_events = false;
			enable_irq(dwc->irq_gadget);
		}
		break;
	case DWC3_GCTL_PRTCAP_HOST:
	default:
		/* do nothing */
		break;
	}

	pm_runtime_mark_last_busy(dev);

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

	ret = dwc3_resume_common(dwc, PMSG_RESUME);
	if (ret)
		pm_runtime_set_suspended(dev);

out:
	pm_runtime_enable(dev);

	return ret;
}
