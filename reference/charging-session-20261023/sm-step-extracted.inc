static int sm_step_locked(struct sm_charger *c)
{
	struct sm_target target = { 0 }, validation_target;
	enum sm_policy_reason reason = SM_POLICY_REASON_NONE;
	int ret, validation, source, thermal_hold = 0;

	ret = sm_collect(c, &c->sample);
	c->sampled_at = ktime_get_boottime();
	/* Full starts a new OEM charge period only after every other policy
	 * predicate has succeeded. Do not let Full clear an existing hard latch.
	 */
	validation = ret;
	if (!validation)
		validation = sm_policy_with_reason(&c->sample, c->cell_ceiling_uv,
				       c->current_cap_ua, c->input_cap_ua,
				       &validation_target, &reason);
	/* Only eligible fresh samples move the thermal hysteresis. A MAC, IO,
	 * global voltage or timeout error never becomes a recoverable hold.
	 */
	if (c->sample.online && (!validation || sm_policy_reason_is_thermal(reason))) {
		thermal_hold = sm_thermal_gate(&c->thermal, c->sample.temp_decic, 1);
		if (!validation && thermal_hold)
			validation = -ERANGE;
	}
	source = c->sample.online ? 1 : !ret && c->sample.valid ? 0 : -1;
	c->sample.session_seconds = sm_cycle_update(&c->cycle,
		ktime_get_boottime_ns(), source,
		sm_cycle_full_allowed(c->sample_full, c->latched, validation));
	if (!ret)
		ret = sm_policy_with_reason(&c->sample, c->cell_ceiling_uv,
				c->current_cap_ua, c->input_cap_ua, &target, &reason);
	if (!ret && thermal_hold) {
		ret = -ERANGE;
		reason = SM_POLICY_REASON_TEMPERATURE;
		target.enable = 0;
	}
	c->thermal_reason = sm_policy_reason_is_thermal(reason) ? reason : SM_POLICY_REASON_NONE;
	/* Reset/configuration/suspend may temporarily remove an SDP allowance.
	 * Stop immediately, then resume only after fresh accepted source data.
	 * Such transitions must not clear an existing electrical/IO fault latch.
	 */
	c->latched = sm_sample_latch(c->latched, ret,
		c->source_inhibit || sm_policy_reason_is_thermal(reason), c->sample.fault);
	/* Shadow mode evaluates the same policy but performs no charger writes. */
	if (control) {
		if (ret || c->latched || !c->auto_requested || !target.enable) {
			c->stop_error = sm_stop(&c->io);
			if (c->stop_error) c->latched = true;
			if (!ret) ret = c->stop_error;
			target.enable = 0;
		} else {
			ret = sm_apply(&c->io, &target, &c->stop_error);
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
