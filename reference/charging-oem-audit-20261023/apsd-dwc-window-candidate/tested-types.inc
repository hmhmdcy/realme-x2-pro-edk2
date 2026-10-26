enum dwc3_gadget_window_state {
	DWC3_WINDOW_IDLE,
	DWC3_WINDOW_CLAIMED,
	DWC3_WINDOW_HALTED,
	DWC3_WINDOW_RESTORING,
	DWC3_WINDOW_FAILED,
	DWC3_WINDOW_SHUTDOWN,
};

/* DWC3-internal state, not UAPI or an exported kernel/module ABI. */
struct dwc3_gadget_window {
	u64 cookie;
	enum dwc3_gadget_window_state state;
	bool pm_ref;
	bool halted;
	bool cancelled;
	bool recovery_pending;
	int halt_error;
	int restore_error;
};

struct dwc3_gadget_window_result {
	u64 cookie;
	enum dwc3_gadget_window_state state;
	bool halted;
	bool cancelled;
	bool restore_wanted;
	int halt_error;
	int restore_error;
};

