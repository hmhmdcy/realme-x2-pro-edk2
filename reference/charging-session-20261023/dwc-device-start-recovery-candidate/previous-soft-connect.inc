static int previous_soft_connect(struct dwc3 *dwc)
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
