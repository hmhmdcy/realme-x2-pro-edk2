struct dwc3_recovery_result {
	const char *stage;
	u64 start_seq, end_seq;
	bool pending;
};

static void dwc3_schedule_err_recovery(struct dwc3 *dwc)
{
	/* Called with dwc->lock held. Count every real IRQ error, including
	 * requests coalesced by schedule_work() into an already-pending work.
	 */
	dwc->err_event_seq++;
	dwc->err_state = DWC3_ERR_RECOVERY;
	schedule_work(&dwc->err_recovery_work);
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
