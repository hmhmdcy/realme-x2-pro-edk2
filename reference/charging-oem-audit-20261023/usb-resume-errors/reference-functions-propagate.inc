static int dwc3_qcom_suspend(struct dwc3_qcom *qcom, bool wakeup)
{
	u32 val;
	int i, ret;

	if (qcom->is_suspended)
		return 0;

	for (i = 0; i < qcom->num_ports; i++) {
		val = readl(qcom->qscratch_base + pwr_evnt_irq_stat_reg[i]);
		if (!(val & PWR_EVNT_LPM_IN_L2_MASK))
			dev_err(qcom->dev, "port-%d HS-PHY not in L2: status=%#x wakeup=%d\n",
			i + 1, val, wakeup);
	}

	for (i = qcom->num_clocks - 1; i >= 0; i--)
		clk_disable_unprepare(qcom->clks[i]);

	ret = dwc3_qcom_interconnect_disable(qcom);
	if (ret)
		dev_warn(qcom->dev, "failed to disable interconnect: %d\n", ret);

	/*
	 * The role is stable during suspend as role switching is done from a
	 * freezable workqueue.
	 */
	if (dwc3_qcom_is_host(qcom) && wakeup) {
		for (i = 0; i < qcom->num_ports; i++)
			qcom->ports[i].usb2_speed = dwc3_qcom_read_usb2_speed(qcom, i);
		dwc3_qcom_enable_interrupts(qcom);
	}

	qcom->is_suspended = true;

	return 0;
}

static int dwc3_qcom_resume(struct dwc3_qcom *qcom, bool wakeup)
{
	int ret;
	int i;

	if (!qcom->is_suspended)
		return 0;

	if (dwc3_qcom_is_host(qcom) && wakeup)
		dwc3_qcom_disable_interrupts(qcom);

	for (i = 0; i < qcom->num_clocks; i++) {
		ret = clk_prepare_enable(qcom->clks[i]);
		if (ret < 0) {
			while (--i >= 0)
				clk_disable_unprepare(qcom->clks[i]);
			return ret;
		}
	}

	ret = dwc3_qcom_interconnect_enable(qcom);
	if (ret)
		dev_warn(qcom->dev, "failed to enable interconnect: %d\n", ret);

	/* Clear existing events from PHY related to L2 in/out */
	for (i = 0; i < qcom->num_ports; i++) {
		dwc3_qcom_setbits(qcom->qscratch_base,
				  pwr_evnt_irq_stat_reg[i],
				  PWR_EVNT_LPM_IN_L2_MASK | PWR_EVNT_LPM_OUT_L2_MASK);
	}

	qcom->is_suspended = false;

	return 0;
}

int dwc3_core_soft_reset(struct dwc3 *dwc)
{
	u32		reg;
	int		retries = 1000;

	/*
	 * We're resetting only the device side because, if we're in host mode,
	 * XHCI driver will reset the host block. If dwc3 was configured for
	 * host-only mode, then we can return early.
	 */
	if (dwc->current_dr_role == DWC3_GCTL_PRTCAP_HOST)
		return 0;

	reg = dwc3_readl(dwc, DWC3_DCTL);
	reg |= DWC3_DCTL_CSFTRST;
	reg &= ~DWC3_DCTL_RUN_STOP;
	dwc3_gadget_dctl_write_safe(dwc, reg);

	/*
	 * For DWC_usb31 controller 1.90a and later, the DCTL.CSFRST bit
	 * is cleared only after all the clocks are synchronized. This can
	 * take a little more than 50ms. Set the polling rate at 20ms
	 * for 10 times instead.
	 */
	if (DWC3_VER_IS_WITHIN(DWC31, 190A, ANY) || DWC3_IP_IS(DWC32))
		retries = 10;

	do {
		reg = dwc3_readl(dwc, DWC3_DCTL);
		if (!(reg & DWC3_DCTL_CSFTRST))
			goto done;

		if (DWC3_VER_IS_WITHIN(DWC31, 190A, ANY) || DWC3_IP_IS(DWC32))
			msleep(20);
		else
			udelay(1);
	} while (--retries);

	dev_warn(dwc->dev, "DWC3 controller soft reset failed.\n");
	return -ETIMEDOUT;

done:
	/*
	 * For DWC_usb31 controller 1.80a and prior, once DCTL.CSFRST bit
	 * is cleared, we must wait at least 50ms before accessing the PHY
	 * domain (synchronization delay).
	 */
	if (DWC3_VER_IS_WITHIN(DWC31, ANY, 180A))
		msleep(50);

	return 0;
}

static int __dwc3_gadget_start(struct dwc3 *dwc)
{
	struct dwc3_ep		*dep;
	int			ret = 0;
	u32			reg;

	/*
	 * Use IMOD if enabled via dwc->imod_interval. Otherwise, if
	 * the core supports IMOD, disable it.
	 */
	if (dwc->imod_interval) {
		dwc3_writel(dwc, DWC3_DEV_IMOD(0), dwc->imod_interval);
		dwc3_writel(dwc, DWC3_GEVNTCOUNT(0), DWC3_GEVNTCOUNT_EHB);
	} else if (dwc3_has_imod(dwc)) {
		dwc3_writel(dwc, DWC3_DEV_IMOD(0), 0);
	}

	/*
	 * We are telling dwc3 that we want to use DCFG.NUMP as ACK TP's NUMP
	 * field instead of letting dwc3 itself calculate that automatically.
	 *
	 * This way, we maximize the chances that we'll be able to get several
	 * bursts of data without going through any sort of endpoint throttling.
	 */
	reg = dwc3_readl(dwc, DWC3_GRXTHRCFG);
	if (DWC3_IP_IS(DWC3))
		reg &= ~DWC3_GRXTHRCFG_PKTCNTSEL;
	else
		reg &= ~DWC31_GRXTHRCFG_PKTCNTSEL;

	dwc3_writel(dwc, DWC3_GRXTHRCFG, reg);

	dwc3_gadget_setup_nump(dwc);

	/*
	 * Currently the controller handles single stream only. So, Ignore
	 * Packet Pending bit for stream selection and don't search for another
	 * stream if the host sends Data Packet with PP=0 (for OUT direction) or
	 * ACK with NumP=0 and PP=0 (for IN direction). This slightly improves
	 * the stream performance.
	 */
	reg = dwc3_readl(dwc, DWC3_DCFG);
	reg |= DWC3_DCFG_IGNSTRMPP;
	dwc3_writel(dwc, DWC3_DCFG, reg);

	/* Enable MST by default if the device is capable of MST */
	if (DWC3_MST_CAPABLE(&dwc->hwparams)) {
		reg = dwc3_readl(dwc, DWC3_DCFG1);
		reg &= ~DWC3_DCFG1_DIS_MST_ENH;
		dwc3_writel(dwc, DWC3_DCFG1, reg);
	}

	/* Start with SuperSpeed Default */
	dwc3_gadget_ep0_desc.wMaxPacketSize = cpu_to_le16(512);

	ret = dwc3_gadget_start_config(dwc, 0);
	if (ret) {
		dev_err(dwc->dev, "failed to config endpoints\n");
		return ret;
	}

	dep = dwc->eps[0];
	dep->flags = 0;
	ret = __dwc3_gadget_ep_enable(dep, DWC3_DEPCFG_ACTION_INIT);
	if (ret) {
		dev_err(dwc->dev, "failed to enable %s\n", dep->name);
		goto err0;
	}

	dep = dwc->eps[1];
	dep->flags = 0;
	ret = __dwc3_gadget_ep_enable(dep, DWC3_DEPCFG_ACTION_INIT);
	if (ret) {
		dev_err(dwc->dev, "failed to enable %s\n", dep->name);
		goto err1;
	}

	/* begin to receive SETUP packets */
	dwc->ep0state = EP0_SETUP_PHASE;
	dwc->ep0_bounced = false;
	dwc->link_state = DWC3_LINK_STATE_SS_DIS;
	dwc->delayed_status = false;
	dwc3_ep0_out_start(dwc);

	dwc3_gadget_enable_irq(dwc);
	dwc3_enable_susphy(dwc, true);

	return 0;

err1:
	__dwc3_gadget_ep_disable(dwc->eps[0]);

err0:
	return ret;
}

static int dwc3_gadget_run_stop(struct dwc3 *dwc, int is_on)
{
	u32			reg;
	u32			timeout = 2000;
	u32			saved_config = 0;

	if (pm_runtime_suspended(dwc->dev))
		return 0;

	/*
	 * When operating in USB 2.0 speeds (HS/FS), ensure that
	 * GUSB2PHYCFG.ENBLSLPM and GUSB2PHYCFG.SUSPHY are cleared before starting
	 * or stopping the controller. This resolves timeout issues that occur
	 * during frequent role switches between host and device modes.
	 *
	 * Save and clear these settings, then restore them after completing the
	 * controller start or stop sequence.
	 *
	 * This solution was discovered through experimentation as it is not
	 * mentioned in the dwc3 programming guide. It has been tested on an
	 * Exynos platforms.
	 */
	reg = dwc3_readl(dwc, DWC3_GUSB2PHYCFG(0));
	if (reg & DWC3_GUSB2PHYCFG_SUSPHY) {
		saved_config |= DWC3_GUSB2PHYCFG_SUSPHY;
		reg &= ~DWC3_GUSB2PHYCFG_SUSPHY;
	}

	if (reg & DWC3_GUSB2PHYCFG_ENBLSLPM) {
		saved_config |= DWC3_GUSB2PHYCFG_ENBLSLPM;
		reg &= ~DWC3_GUSB2PHYCFG_ENBLSLPM;
	}

	if (saved_config)
		dwc3_writel(dwc, DWC3_GUSB2PHYCFG(0), reg);

	reg = dwc3_readl(dwc, DWC3_DCTL);
	if (is_on) {
		if (DWC3_VER_IS_WITHIN(DWC3, ANY, 187A)) {
			reg &= ~DWC3_DCTL_TRGTULST_MASK;
			reg |= DWC3_DCTL_TRGTULST_RX_DET;
		}

		if (!DWC3_VER_IS_PRIOR(DWC3, 194A))
			reg &= ~DWC3_DCTL_KEEP_CONNECT;
		reg |= DWC3_DCTL_RUN_STOP;

		__dwc3_gadget_set_speed(dwc);
		dwc->pullups_connected = true;
	} else {
		reg &= ~DWC3_DCTL_RUN_STOP;

		dwc->pullups_connected = false;
	}

	dwc3_pre_run_stop(dwc, is_on);
	dwc3_gadget_dctl_write_safe(dwc, reg);

	do {
		usleep_range(1000, 2000);
		reg = dwc3_readl(dwc, DWC3_DSTS);
		reg &= DWC3_DSTS_DEVCTRLHLT;
	} while (--timeout && !(!is_on ^ !reg));

	if (saved_config) {
		reg = dwc3_readl(dwc, DWC3_GUSB2PHYCFG(0));
		reg |= saved_config;
		dwc3_writel(dwc, DWC3_GUSB2PHYCFG(0), reg);
	}

	if (!timeout)
		return -ETIMEDOUT;

	return 0;
}

static int dwc3_gadget_soft_disconnect(struct dwc3 *dwc)
{
	unsigned long flags;
	int ret;

	spin_lock_irqsave(&dwc->lock, flags);
	if (!dwc->pullups_connected) {
		spin_unlock_irqrestore(&dwc->lock, flags);
		return 0;
	}

	dwc->connected = false;

	/*
	 * Attempt to end pending SETUP status phase, and not wait for the
	 * function to do so.
	 */
	if (dwc->delayed_status)
		dwc3_ep0_send_delayed_status(dwc);

	/*
	 * In the Synopsys DesignWare Cores USB3 Databook Rev. 3.30a
	 * Section 4.1.8 Table 4-7, it states that for a device-initiated
	 * disconnect, the SW needs to ensure that it sends "a DEPENDXFER
	 * command for any active transfers" before clearing the RunStop
	 * bit.
	 */
	dwc3_stop_active_transfers(dwc);
	spin_unlock_irqrestore(&dwc->lock, flags);

	/*
	 * Per databook, when we want to stop the gadget, if a control transfer
	 * is still in process, complete it and get the core into setup phase.
	 * In case the host is unresponsive to a SETUP transaction, forcefully
	 * stall the transfer, and move back to the SETUP phase, so that any
	 * pending endxfers can be executed.
	 */
	if (dwc->ep0state != EP0_SETUP_PHASE) {
		reinit_completion(&dwc->ep0_in_setup);

		ret = wait_for_completion_timeout(&dwc->ep0_in_setup,
				msecs_to_jiffies(DWC3_PULL_UP_TIMEOUT));
		if (ret == 0) {
			dev_warn(dwc->dev, "wait for SETUP phase timed out\n");
			spin_lock_irqsave(&dwc->lock, flags);
			dwc3_ep0_reset_state(dwc);
			spin_unlock_irqrestore(&dwc->lock, flags);
		}
	}

	/*
	 * Note: if the GEVNTCOUNT indicates events in the event buffer, the
	 * driver needs to acknowledge them before the controller can halt.
	 * Simply let the interrupt handler acknowledges and handle the
	 * remaining event generated by the controller while polling for
	 * DSTS.DEVCTLHLT.
	 */
	ret = dwc3_gadget_run_stop(dwc, false);

	/*
	 * Stop the gadget after controller is halted, so that if needed, the
	 * events to update EP0 state can still occur while the run/stop
	 * routine polls for the halted state.  DEVTEN is cleared as part of
	 * gadget stop.
	 */
	spin_lock_irqsave(&dwc->lock, flags);
	__dwc3_gadget_stop(dwc);
	spin_unlock_irqrestore(&dwc->lock, flags);

	usb_gadget_set_state(dwc->gadget, USB_STATE_NOTATTACHED);

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
	ret = __dwc3_gadget_start(dwc);
	if (ret) {
		dev_err(dwc->dev, "gadget endpoint start failed: %d\n", ret);
		return ret;
	}
	return dwc3_gadget_run_stop(dwc, true);
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

int dwc3_gadget_resume(struct dwc3 *dwc)
{
	if (!dwc->gadget_driver || !dwc->softconnect)
		return 0;

	return dwc3_gadget_soft_connect(dwc);
}

static int dwc3_resume_common(struct dwc3 *dwc, pm_message_t msg)
{
	int		ret = 0;
	u32		reg;
	int		i;

	switch (dwc->current_dr_role) {
	case DWC3_GCTL_PRTCAP_DEVICE:
		ret = dwc3_core_init_for_resume(dwc);
		if (ret)
			return ret;

		dwc3_set_prtcap(dwc, DWC3_GCTL_PRTCAP_DEVICE, true);
		ret = dwc3_gadget_resume(dwc);
		break;
	case DWC3_GCTL_PRTCAP_HOST:
		if (!PMSG_IS_AUTO(msg) &&
		    (!device_may_wakeup(dwc->dev) || dwc->needs_full_reinit)) {
			ret = dwc3_core_init_for_resume(dwc);
			if (ret)
				return ret;
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
			return ret;

		dwc3_set_prtcap(dwc, dwc->current_dr_role, true);

		dwc3_otg_init(dwc);
		if (dwc->current_otg_role == DWC3_OTG_ROLE_HOST) {
			dwc3_otg_host_init(dwc);
		} else if (dwc->current_otg_role == DWC3_OTG_ROLE_DEVICE) {
			ret = dwc3_gadget_resume(dwc);
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

	if (ret)
		dev_err(dwc->dev, "gadget resume failed: %d\n", ret);

	return ret;
}
