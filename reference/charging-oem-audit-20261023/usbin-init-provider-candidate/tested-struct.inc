enum samurai_usbin_stage {
	SUI_DISABLED, SUI_PROBE_ZERO, SUI_WAIT_FIRST_OFF,
	SUI_TRANSACTION, SUI_INITIALIZED, SUI_TERMINAL,
};

struct samurai_usb_input {
	struct regmap *map;
	struct power_supply *psy;
	struct mutex lock;
	struct delayed_work work;
	struct samurai_usb_budget last;
	int last_error;
	bool last_valid;
	bool udc_valid;
	bool paused;
	int udc_current_ua;
	/* Independent diagnostic history; never changes source/native allowance. */
	enum samurai_usbin_stage init_stage;
	struct ui_state init;
	unsigned int init_probe_before, init_probe_after;
	int init_probe_error;
	unsigned long long init_observed_ms;
	struct ui_snapshot init_observed;
};
