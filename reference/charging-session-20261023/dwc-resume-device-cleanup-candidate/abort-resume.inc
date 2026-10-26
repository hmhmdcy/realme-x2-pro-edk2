/* Failed DEVICE resume is terminal until a fresh core binding. This helper
 * does not reconnect and does not acquire runtime PM from a PM callback.
 */
int dwc3_gadget_abort_resume(struct dwc3 *dwc)
{
	unsigned long flags;
	bool pending;
	int ret;

	mutex_lock(&dwc->connect_mutex);
	ret = dwc3_gadget_soft_disconnect(dwc);
	spin_lock_irqsave(&dwc->lock, flags);
	/* soft_disconnect returns early when pullups are false. Stop IRQ/EP0
	 * even for a failure before RUN_STOP was issued.
	 */
	__dwc3_gadget_stop(dwc);
	dwc->connected = false;
	WRITE_ONCE(dwc->resume_failed, true);
	dwc->err_state = DWC3_ERR_UNRECOVERABLE;
	spin_unlock_irqrestore(&dwc->lock, flags);

	/* request/free are serialized by this mutex. Keep exactly our own
	 * disabled depth through failure, independent of a pending-event IRQ.
	 */
	if (dwc->gadget_driver && !dwc->resume_irq_parked) {
		disable_irq_nosync(dwc->irq_gadget);
		dwc->resume_irq_parked = true;
	}
	synchronize_irq(dwc->irq_gadget);
	/* The suspended hard handler sets pending before get/disable. Only
	 * after joining it does pending prove both of those operations ended.
	 * This is the only setter and normal resume is the only consumer.
	 */
	spin_lock_irqsave(&dwc->lock, flags);
	pending = dwc->pending_events;
	dwc->pending_events = false;
	spin_unlock_irqrestore(&dwc->lock, flags);
	if (pending) {
		pm_runtime_put_noidle(dwc->dev);
		/* Release the old pending-event depth, retaining our park if
		 * still bound. If unbound, no handler remains to use old MMIO.
		 */
		enable_irq(dwc->irq_gadget);
	}
	mutex_unlock(&dwc->connect_mutex);
	return ret;
}
