struct dwc3_recovery_result {
	const char *stage;
	u64 start_seq, end_seq;
	bool pending;
};

int dwc3_event_buffers_setup(struct dwc3 *dwc)
{
	struct dwc3_event_buffer	*evt;
	u32				reg;

	if (!dwc->ev_buf)
		return 0;

	evt = dwc->ev_buf;
	evt->lpos = 0;
	dwc3_writel(dwc, DWC3_GEVNTADRLO(0),
		    lower_32_bits(evt->dma));
	dwc3_writel(dwc, DWC3_GEVNTADRHI(0),
		    upper_32_bits(evt->dma));
	dwc3_writel(dwc, DWC3_GEVNTSIZ(0),
		    DWC3_GEVNTSIZ_SIZE(evt->length));

	/* Clear any stale event */
	reg = dwc3_readl(dwc, DWC3_GEVNTCOUNT(0));
	dwc3_writel(dwc, DWC3_GEVNTCOUNT(0), reg);
	return 0;
}

void dwc3_event_buffers_cleanup(struct dwc3 *dwc)
{
	struct dwc3_event_buffer	*evt;
	u32				reg;

	if (!dwc->ev_buf)
		return;
	/*
	 * Exynos platforms may not be able to access event buffer if the
	 * controller failed to halt on dwc3_core_exit().
	 */
	reg = dwc3_readl(dwc, DWC3_DSTS);
	if (!(reg & DWC3_DSTS_DEVCTRLHLT))
		return;

	evt = dwc->ev_buf;

	evt->lpos = 0;

	dwc3_writel(dwc, DWC3_GEVNTADRLO(0), 0);
	dwc3_writel(dwc, DWC3_GEVNTADRHI(0), 0);
	dwc3_writel(dwc, DWC3_GEVNTSIZ(0), DWC3_GEVNTSIZ_INTMASK
			| DWC3_GEVNTSIZ_SIZE(0));

	/* Clear any stale event */
	reg = dwc3_readl(dwc, DWC3_GEVNTCOUNT(0));
	dwc3_writel(dwc, DWC3_GEVNTCOUNT(0), reg);
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

static void dwc3_gadget_disable_irq(struct dwc3 *dwc)
{
	/* mask all interrupts */
	dwc3_writel(dwc, DWC3_DEVTEN, 0x00);
}

static void __dwc3_gadget_stop(struct dwc3 *dwc)
{
	dwc3_gadget_disable_irq(dwc);
	__dwc3_gadget_ep_disable(dwc->eps[0]);
	__dwc3_gadget_ep_disable(dwc->eps[1]);
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
	unsigned long flags;
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
		/* No RUN_STOP was issued by this attempt. Clear device IRQs and
		 * both EP0 enables even when the partial start failed before the
		 * software pullup flag was set: soft_disconnect() would skip it.
		 * The event buffer/core stay valid for an already-running IRQ;
		 * this is not a proof of physical HALT or a core PM unwind.
		 */
		spin_lock_irqsave(&dwc->lock, flags);
		__dwc3_gadget_stop(dwc);
		spin_unlock_irqrestore(&dwc->lock, flags);
		dev_err(dwc->dev, "gadget endpoint start failed: %d; RUN_STOP skipped\n",
			ret);
		return ret;
	}
	return dwc3_gadget_run_stop(dwc, true);
}

static void dwc3_schedule_err_recovery(struct dwc3 *dwc)
{
	/* Called with dwc->lock held. Count every real IRQ error, including
	 * requests coalesced by schedule_work() into an already-pending work.
	 */
	dwc->err_event_seq++;
	dwc->err_state = DWC3_ERR_RECOVERY;
	schedule_work(&dwc->err_recovery_work);
}

static int dwc3_gadget_recover_locked(struct dwc3 *dwc, bool claim,
				      struct dwc3_recovery_result *result)
{
	unsigned long flags;
	int ret = 0;

	lockdep_assert_held(&dwc->connect_mutex);
	spin_lock_irqsave(&dwc->lock, flags);
	result->start_seq = dwc->err_event_seq;
	result->end_seq = result->start_seq;
	result->pending = false;
	/* A synchronous resume failure cannot itself revive an old failure.
	 * A real IRQ still uses the original schedule_err_recovery policy.
	 */
	if (dwc->err_state == DWC3_ERR_UNRECOVERABLE) {
		result->stage = "existing-unrecoverable(policy-EIO)";
		spin_unlock_irqrestore(&dwc->lock, flags);
		return -EIO;
	}
	if (!claim && dwc->err_state != DWC3_ERR_RECOVERY) {
		result->stage = "stale-work";
		spin_unlock_irqrestore(&dwc->lock, flags);
		return 0;
	}
	dwc->err_state = DWC3_ERR_RECOVERY;
	spin_unlock_irqrestore(&dwc->lock, flags);

	result->stage = "disconnect";
	ret = dwc3_gadget_soft_disconnect(dwc);
	dwc3_disconnect_gadget_sleepable(dwc);
	if (ret)
		goto publish;

	result->stage = "disconnect-only";
	if (dwc->softconnect) {
		u32 count;

		/* Join the existing IRQ handler before resetting its event buffer.
		 * This does not re-enable a pending runtime-suspend IRQ or prove
		 * that a latched event was consumed.
		 */
		synchronize_irq(dwc->irq_gadget);
		spin_lock_irqsave(&dwc->lock, flags);
		count = ++dwc->err_recovery_count;
		spin_unlock_irqrestore(&dwc->lock, flags);
		if (count > DWC3_ERR_RECOVERY_MAX) {
			result->stage = "count-limit(policy-EIO)";
			ret = -EIO;
			goto publish;
		}
		result->stage = "connect";
		ret = dwc3_gadget_soft_connect(dwc);
		if (!ret)
			result->stage = "connect-complete";
	}

publish:
	/* IRQ arrival and publication linearize on the existing spinlock.
	 * Never erase a real error delivered after this attempt's snapshot,
	 * including when this attempt itself failed. No new event => retain
	 * the original success/failure policy and existing count semantics.
	 */
	spin_lock_irqsave(&dwc->lock, flags);
	result->end_seq = dwc->err_event_seq;
	result->pending = result->end_seq != result->start_seq;
	if (result->pending)
		dwc->err_state = DWC3_ERR_RECOVERY;
	else
		dwc->err_state = ret ? DWC3_ERR_UNRECOVERABLE : DWC3_ERR_NONE;
	spin_unlock_irqrestore(&dwc->lock, flags);
	/* The IRQ already requested work; explicitly preserve an execution
	 * opportunity even when its request coalesced with a running worker.
	 * One call only: no synchronous second recovery or new retry loop.
	 */
	if (result->pending)
		schedule_work(&dwc->err_recovery_work);
	return ret;
}

static void dwc3_err_recovery_work(struct work_struct *work)
{
	struct dwc3 *dwc = container_of(work, struct dwc3, err_recovery_work);
	struct dwc3_recovery_result result;
	int ret;

	mutex_lock(&dwc->connect_mutex);
	ret = dwc3_gadget_recover_locked(dwc, false, &result);
	mutex_unlock(&dwc->connect_mutex);
	if (ret || result.pending)
		dev_err(dwc->dev,
			"controller recovery stage=%s error=%d seq=%llu->%llu pending_at_publish=%u\n",
			result.stage, ret, (unsigned long long)result.start_seq,
			(unsigned long long)result.end_seq, result.pending);
}

int dwc3_gadget_resume(struct dwc3 *dwc)
{
	struct dwc3_recovery_result result;
	int primary, recovery;

	if (!dwc->gadget_driver || !dwc->softconnect)
		return 0;
	/* HOST is not a gadget caller; keep OTG's original connect behavior. */
	if (dwc->current_dr_role != DWC3_GCTL_PRTCAP_DEVICE)
		return dwc3_gadget_soft_connect(dwc);

	mutex_lock(&dwc->connect_mutex);
	/* Preserve the original first attempt, even with an old error state.
	 * Only the new synchronous recovery claim refuses to revive it.
	 */
	primary = dwc3_gadget_soft_connect(dwc);
	if (primary) {
		recovery = dwc3_gadget_recover_locked(dwc, true, &result);
		dev_err(dwc->dev,
			"DEVICE resume primary=%d recovery=%d stage=%s seq=%llu->%llu pending_at_publish=%u\n",
			primary, recovery, result.stage,
			(unsigned long long)result.start_seq,
			(unsigned long long)result.end_seq, result.pending);
	}
	mutex_unlock(&dwc->connect_mutex);
	/* Existing core PM common ignores this gadget errno and retains its
	 * powered success policy, SUSPHY and runtime pending-event tail.
	 */
	return primary;
}

static irqreturn_t dwc3_check_event_buf(struct dwc3_event_buffer *evt)
{
	struct dwc3 *dwc = evt->dwc;
	u32 amount;
	u32 count;

	if (pm_runtime_suspended(dwc->dev)) {
		dwc->pending_events = true;
		/*
		 * Trigger runtime resume. The get() function will be balanced
		 * after processing the pending events in dwc3_process_pending
		 * events().
		 */
		pm_runtime_get(dwc->dev);
		disable_irq_nosync(dwc->irq_gadget);
		return IRQ_HANDLED;
	}

	/*
	 * With PCIe legacy interrupt, test shows that top-half irq handler can
	 * be called again after HW interrupt deassertion. Check if bottom-half
	 * irq event handler completes before caching new event to prevent
	 * losing events.
	 */
	if (evt->flags & DWC3_EVENT_PENDING)
		return IRQ_HANDLED;

	count = dwc3_readl(dwc, DWC3_GEVNTCOUNT(0));
	count &= DWC3_GEVNTCOUNT_MASK;
	if (!count)
		return IRQ_NONE;

	if (count > evt->length) {
		dev_err(dwc->dev, "invalid count(%u) > evt->length(%u)\n",
			count, evt->length);
		/*
		 * This is a fatal error - the driver and controller are out of
		 * sync on which event has been consumed. Reinitializing the
		 * controller is required to recover. Write the bogus count back
		 * to GEVNTCOUNT to clear the IRQ source, consistent with the
		 * stale event clearing in dwc3_event_buffers_setup(), then
		 * schedule error recovery.
		 */
		spin_lock(&dwc->lock);
		dwc3_schedule_err_recovery(dwc);
		spin_unlock(&dwc->lock);
		dwc3_writel(dwc, DWC3_GEVNTCOUNT(0), count);
		return IRQ_HANDLED;
	}

	evt->count = count;
	evt->flags |= DWC3_EVENT_PENDING;

	/* Mask interrupt */
	dwc3_writel(dwc, DWC3_GEVNTSIZ(0),
		    DWC3_GEVNTSIZ_INTMASK | DWC3_GEVNTSIZ_SIZE(evt->length));

	amount = min(count, evt->length - evt->lpos);
	memcpy(evt->cache + evt->lpos, evt->buf + evt->lpos, amount);

	if (amount < count)
		memcpy(evt->cache, evt->buf, count - amount);

	dwc3_writel(dwc, DWC3_GEVNTCOUNT(0), count);

	return IRQ_WAKE_THREAD;
}

static int dwc3_resume_common(struct dwc3 *dwc, pm_message_t msg)
{
	int		ret;
	u32		reg;
	int		i;

	switch (dwc->current_dr_role) {
	case DWC3_GCTL_PRTCAP_DEVICE:
		ret = dwc3_core_init_for_resume(dwc);
		if (ret)
			return ret;

		dwc3_set_prtcap(dwc, DWC3_GCTL_PRTCAP_DEVICE, true);
		dwc3_gadget_resume(dwc);
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

	return 0;
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
