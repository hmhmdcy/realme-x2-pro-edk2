static void previous_dwc3_schedule_err_recovery(struct dwc3 *dwc)
{
	/* Called with dwc->lock held. Count every real IRQ error, including
	 * requests coalesced by schedule_work() into an already-pending work.
	 */
	dwc->err_event_seq++;
	dwc->err_state = DWC3_ERR_RECOVERY;
	schedule_work(&dwc->err_recovery_work);
}

static int previous_dwc3_gadget_recover_locked(struct dwc3 *dwc, bool claim,
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
	spin_unlock_irqrestore(&dwc->lock, flags);
	/* The IRQ already requested work; explicitly preserve an execution
	 * opportunity even when its request coalesced with a running worker.
	 * One call only: no synchronous second recovery or new retry loop.
	 */
	if (result->pending)
		schedule_work(&dwc->err_recovery_work);
	return ret;
}

static void previous_dwc3_err_recovery_work(struct work_struct *work)
{
	struct dwc3 *dwc = container_of(work, struct dwc3, err_recovery_work);
	struct dwc3_recovery_result result;
	int ret;

	mutex_lock(&dwc->connect_mutex);
	ret = previous_dwc3_gadget_recover_locked(dwc, false, &result);
	mutex_unlock(&dwc->connect_mutex);
	if (ret || result.pending)
		dev_err(dwc->dev,
			"controller recovery stage=%s error=%d seq=%llu->%llu pending_at_publish=%u\n",
			result.stage, ret, (unsigned long long)result.start_seq,
			(unsigned long long)result.end_seq, result.pending);
}

void previous_dwc3_gadget_exit(struct dwc3 *dwc)
{
	if (!dwc->gadget)
		return;

	cancel_work_sync(&dwc->err_recovery_work);
	mutex_destroy(&dwc->connect_mutex);
	dwc3_enable_susphy(dwc, true);
	usb_del_gadget(dwc->gadget);
	dwc3_gadget_free_endpoints(dwc);
	usb_put_gadget(dwc->gadget);
	dma_free_coherent(dwc->sysdev, DWC3_BOUNCE_SIZE, dwc->bounce,
			  dwc->bounce_addr);
	kfree(dwc->setup_buf);
	dma_free_coherent(dwc->sysdev, sizeof(*dwc->ep0_trb) * 2,
			  dwc->ep0_trb, dwc->ep0_trb_addr);
}
