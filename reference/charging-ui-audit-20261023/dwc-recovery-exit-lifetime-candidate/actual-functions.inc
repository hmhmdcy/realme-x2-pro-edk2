struct dwc3_recovery_result {
	const char *stage;
	u64 start_seq, end_seq;
	bool pending;
	/* Only an actual soft_connect() return of zero sets this fact. */
	bool reconnected;
};

static void dwc3_schedule_err_recovery(struct dwc3 *dwc)
{
	/* Called with dwc->lock held. Count every real IRQ error, including
	 * requests coalesced by schedule_work() into an already-pending work.
	 */
	dwc->err_event_seq++;
	dwc->err_state = DWC3_ERR_RECOVERY;
	if (!dwc->recovery_stopping)
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
	result->reconnected = false;
	/* Exit owns the closed recovery gate until the next gadget init.
	 * A queued old worker must not touch a retiring controller.
	 */
	if (dwc->recovery_stopping) {
		result->stage = "gadget-exit";
		spin_unlock_irqrestore(&dwc->lock, flags);
		return -ESHUTDOWN;
	}
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
		if (!ret) {
			result->reconnected = true;
			result->stage = "connect-complete";
		}
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
	/* Queue under the same lock as exit closes the producer gate.
	 * Joining the running worker alone cannot prevent a later IRQ or
	 * pending publication from rearming it. Keep the original pending
	 * generation/state, but no execution after this gadget retires.
	 */
	if (result->pending && !dwc->recovery_stopping)
		schedule_work(&dwc->err_recovery_work);
	spin_unlock_irqrestore(&dwc->lock, flags);
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

static int dwc3_gadget_pullup(struct usb_gadget *g, int is_on)
{
	struct dwc3		*dwc = gadget_to_dwc(g);
	int			ret;

	is_on = !!is_on;

	dwc->softconnect = is_on;

	/*
	 * Avoid issuing a runtime resume if the device is already in the
	 * suspended state during gadget disconnect.  DWC3 gadget was already
	 * halted/stopped during runtime suspend.
	 */
	if (!is_on) {
		pm_runtime_barrier(dwc->dev);
		if (pm_runtime_suspended(dwc->dev))
			return 0;
	}

	/*
	 * Check the return value for successful resume, or error.  For a
	 * successful resume, the DWC3 runtime PM resume routine will handle
	 * the run stop sequence, so avoid duplicate operations here.
	 */
	ret = pm_runtime_get_sync(dwc->dev);
	if (!ret || ret < 0) {
		pm_runtime_put(dwc->dev);
		if (ret < 0)
			pm_runtime_set_suspended(dwc->dev);
		return ret;
	}

	if (dwc->pullups_connected == is_on) {
		pm_runtime_put(dwc->dev);
		return 0;
	}

	synchronize_irq(dwc->irq_gadget);

	/* Serialize against dwc3_err_recovery_work() */
	mutex_lock(&dwc->connect_mutex);
	if (!is_on)
		ret = dwc3_gadget_soft_disconnect(dwc);
	else
		ret = dwc3_gadget_soft_connect(dwc);
	mutex_unlock(&dwc->connect_mutex);

	pm_runtime_put(dwc->dev);

	return ret;
}

static int dwc3_gadget_stop(struct usb_gadget *g)
{
	struct dwc3		*dwc = gadget_to_dwc(g);
	unsigned long		flags;

	if (dwc->sys_wakeup)
		device_wakeup_disable(dwc->sysdev);

	spin_lock_irqsave(&dwc->lock, flags);
	dwc->gadget_driver	= NULL;
	dwc->max_cfg_eps = 0;
	spin_unlock_irqrestore(&dwc->lock, flags);

	free_irq(dwc->irq_gadget, dwc->ev_buf);

	return 0;
}

void dwc3_gadget_exit(struct dwc3 *dwc)
{
	unsigned long flags;

	if (!dwc->gadget)
		return;

	/* Exclude both IRQ enqueue and recovery-publication requeue before
	 * joining. Never join while holding connect_mutex: the worker
	 * needs it. Leave it alive for usb_del_gadget() -> pullup/off ->
	 * udc_stop/free_irq; no recovery producer can rearm in that gap.
	 */
	spin_lock_irqsave(&dwc->lock, flags);
	dwc->recovery_stopping = true;
	spin_unlock_irqrestore(&dwc->lock, flags);
	cancel_work_sync(&dwc->err_recovery_work);
	dwc3_enable_susphy(dwc, true);
	usb_del_gadget(dwc->gadget);
	mutex_destroy(&dwc->connect_mutex);
	dwc3_gadget_free_endpoints(dwc);
	usb_put_gadget(dwc->gadget);
	dma_free_coherent(dwc->sysdev, DWC3_BOUNCE_SIZE, dwc->bounce,
			  dwc->bounce_addr);
	kfree(dwc->setup_buf);
	dma_free_coherent(dwc->sysdev, sizeof(*dwc->ep0_trb) * 2,
			  dwc->ep0_trb, dwc->ep0_trb_addr);
}
