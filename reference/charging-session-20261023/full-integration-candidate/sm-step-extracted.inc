static int sm_step_locked(struct sm_charger *c)
{
	struct sm_target target = { 0 }, validation_target;
	struct sm_oem_full_sample full_sample;
	enum sm_policy_reason reason = SM_POLICY_REASON_NONE;
	int ret, validation, source, thermal_hold = 0;
	bool healthy_full;
	u64 now;

	ret = sm_collect(c, &c->sample);
	c->sampled_at = ktime_get_boottime();
	now = ktime_get_boottime_ns();
	c->full_holding = false;
	c->hold_requested = false;
	/* Established timeout is checked before any new Full interpretation. */
	c->sample.session_seconds = c->cycle.timed_out ? SM_OEM_MAX_SECONDS : 0;
	validation = ret;
	if (!validation)
		validation = sm_policy_with_reason(&c->sample, c->cell_ceiling_uv,
				c->current_cap_ua, c->input_cap_ua, &validation_target, &reason);
	if (c->sample.online && (!validation || sm_policy_reason_is_thermal(reason))) {
		thermal_hold = sm_thermal_gate(&c->thermal, c->sample.temp_decic, 1);
		if (!validation && thermal_hold)
			validation = -ERANGE;
	}
	source = c->sample.online ? 1 : !ret && c->sample.valid ? 0 : -1;
	/* OEM Full handling precedes this period's time accumulation. A newly
	 * completed sixth software sample may finish a not-yet-timed-out cycle
	 * at its boundary. Existing timed_out was validated above and cannot reset.
	 */
	full_sample = (struct sm_oem_full_sample){
		.valid = c->sample.valid,
		.source_known = source >= 0,
		.online = c->sample.online,
		.protection_good = c->sample.protection_ok,
		.policy_good = !validation,
		.hard_latched = c->latched,
		.timeout = c->cycle.timed_out,
		.hardware_full = c->sample_full,
		.temp_decic = c->sample.temp_decic,
		.max_cell_uv = c->sample.cell1_uv > c->sample.cell2_uv ?
			c->sample.cell1_uv : c->sample.cell2_uv,
		.gauge_current_ua = c->sample.gauge_current_ua,
		.cell_target_uv = !validation ? validation_target.cell_uv : 0,
		.gauge_flags = c->sample.gauge_flags,
	};
	c->full_result = sm_oem_full_step(&c->full_state, now, &full_sample);
	/* Physical detach is a normal stop/reset, never a new telemetry fault. */
	if (c->full_result.stop_all && !validation && !c->latched && source != 0) {
		ret = -ENODATA;
		validation = ret;
		reason = SM_POLICY_REASON_NONE;
	}
	healthy_full = sm_cycle_full_allowed(c->sample_full ||
		((c->full_result.full || c->full_result.recharge) && !c->full_result.stop_all),
		c->latched, validation);
	c->sample.session_seconds = sm_cycle_update(&c->cycle, now, source, healthy_full);
	if (!ret)
		ret = sm_policy_with_reason(&c->sample, c->cell_ceiling_uv,
				c->current_cap_ua, c->input_cap_ua, &target, &reason);
	if (!ret && thermal_hold) {
		ret = -ERANGE;
		reason = SM_POLICY_REASON_TEMPERATURE;
		target.enable = 0;
	}
	c->thermal_reason = sm_policy_reason_is_thermal(reason) ? reason : SM_POLICY_REASON_NONE;
	c->gauge_charge_stop = reason == SM_POLICY_REASON_GAUGE_CHARGE_STOP;
	/* TCA is an immediate stop request; it never masks a prior hard latch,
	 * becomes normal Full, erases raw flags, or bypasses a failed bus stop.
	 */
	c->latched = sm_sample_latch(c->latched, ret,
		c->source_inhibit || sm_policy_reason_is_thermal(reason) || c->gauge_charge_stop,
		c->sample.fault);
	c->hold_requested = !ret && !c->latched && c->auto_requested &&
		c->full_result.hold_charge_only;
	if (c->hold_requested)
		target.enable = 0; /* Desired CHG, distinct from healthy converter hold. */
	if (control) {
		if (ret || c->latched || !c->auto_requested ||
		    (!target.enable && !c->hold_requested)) {
			c->stop_error = sm_stop(&c->io);
			if (c->stop_error) c->latched = true;
			if (!ret) ret = c->stop_error;
			target.enable = 0;
		} else {
			if (c->hold_requested) {
				ret = sm_apply_charge_hold(&c->io, &target, &c->stop_error);
				c->full_holding = !ret;
			} else {
				ret = sm_apply(&c->io, &target, &c->stop_error);
			}
			if (ret) {
				c->latched = true;
				target.enable = 0;
			}
		}
	}
	c->target = target;
	c->last_error = ret;
	if (ret || c->stop_error)
		dev_warn_ratelimited(&c->client->dev,
			"policy/io error=%d stop error=%d latched=%d shadow=%d\n",
			ret, c->stop_error, c->latched, !control);
	return ret;
}
