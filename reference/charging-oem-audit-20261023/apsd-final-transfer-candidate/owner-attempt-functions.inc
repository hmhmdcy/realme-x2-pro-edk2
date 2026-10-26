/* The original worker owns this embedded identity until rerun returns.
 * All teardown joins that worker before touching its tokens or bus context.
 */
static int owner_attempt_validate(const struct samurai_apsd_attempt *attempt,
		const struct samurai_apsd_bus_sample *fresh)
{
	struct samurai_apsd_owner *o = attempt->context;
	struct qcom_snps_hsphy_window_result phy;
	int ret;

	if (!IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT) ||
	    !IS_BUILTIN(CONFIG_TYPEC_QCOM_PMIC))
		return -EOPNOTSUPP;
	if (attempt != &o->attempt || !o->attempt_active ||
	    !o->dwc || !o->bus || o->attempt_bus != o->bus_ctx ||
	    attempt->epoch != o->once.epoch || !o->once.attempted ||
	    o->once.phase != SAMURAI_APSD_WRITING ||
	    attempt->expected.serial != o->last_sample.serial ||
	    memcmp(attempt->expected.raw, o->last_sample.raw, sizeof(fresh->raw)) ||
	    fresh->serial <= attempt->expected.serial ||
	    owner_now_ms() >= o->once.deadline_ms)
		return -ESTALE;
	if (owner_aborted(o))
		return -ECANCELED;
	if (!o->pd_bridge || o->pd_phase != OWNER_PD_SINK_EPOCH ||
	    !o->pd_prepared || o->attempt_pd != o->pd_lease.owner ||
	    o->attempt_generation != o->pd_lease.generation)
		return -ESTALE;
	ret = samurai_pd5v_validate(&o->pd_lease);
	if (ret)
		return ret;
	if (!o->phy_client || !o->phy.cookie || !o->phy.high_z ||
	    !o->dwc_window.cookie || !o->dwc_window.halted || !o->extra_pm)
		return -ESTALE;
	ret = qcom_snps_hsphy_window_status(o->phy_client, &phy);
	if (ret)
		return ret;
	if (phy.revoked || !phy.high_z || phy.cookie != o->phy.cookie)
		return -ESHUTDOWN;
	/* Route capability is still absent. The actual entry gate continues to
	 * refuse every production attempt, including this last boundary.
	 */
	ret = owner_entry_gate(o);
	if (ret)
		return ret;
	return owner_aborted(o) ? -ECANCELED : 0;
}

static int owner_transfer(struct samurai_apsd_owner *o)
{
	int ret, ack;

	o->attempt = (struct samurai_apsd_attempt) {
		.context = o, .epoch = o->once.epoch, .expected = o->last_sample,
		.validate = owner_attempt_validate,
	};
	o->attempt_bus = o->bus_ctx;
	o->attempt_pd = o->pd_lease.owner;
	o->attempt_generation = o->pd_lease.generation;
	o->attempt_active = true;
	memset(&o->transfer, 0, sizeof(o->transfer));
	ret = o->bus->rerun_once(o->bus_ctx, &o->attempt, &o->transfer);
	o->attempt_active = false;
	ack = samurai_apsd_write_done(&o->once, o->once.epoch, owner_now_ms(), ret);
	if (!ret)
		ret = ack;
	/* Feed a real post-write clear immediately, rather than losing it before
	 * the next poll. Old DONE cannot complete the existing once protocol.
	 */
	if (!ret && o->transfer.post_valid) {
		if (owner_aborted(o))
			ret = -ECANCELED;
		else
			ret = samurai_apsd_sample(&o->once, o->once.epoch, owner_now_ms(),
				o->transfer.after.serial, o->transfer.after.raw[0],
				o->transfer.after.raw[1]);
	}
	return ret;
}
