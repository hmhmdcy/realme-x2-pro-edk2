/* Stack-only attempt receipts, not controller terminal state, HALT proof,
 * IRQ-depth ownership or permission to release core/PHY resources.
 */
struct dwc3_recovery_result {
	const char *stage;
	u64 start_seq, end_seq;
	bool pending;
	/* Only an actual soft_connect() return of zero sets this fact. */
	bool reconnected;
};

struct dwc3_device_resume_result {
	int primary;
	int recovery;
	bool requested;
	bool recovery_attempted;
	/* Completed at publication; a later IRQ/worker is still possible. */
	bool operation_completed;
	struct dwc3_recovery_result detail;
};

static inline int dwc3_gadget_resume(struct dwc3 *dwc)
{
	return 0;
}

static inline void dwc3_gadget_resume_result(struct dwc3 *dwc,
			       struct dwc3_device_resume_result *result)
{
	*result = (struct dwc3_device_resume_result) {
		.detail.stage = "host-only",
	};
}
