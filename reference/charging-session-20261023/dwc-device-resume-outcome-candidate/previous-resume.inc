int previous_gadget_resume(struct dwc3 *dwc)
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
