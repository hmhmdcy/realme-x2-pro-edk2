/* PHY withdrawal publishes its permanent fence before waiting on any DWC
 * lifecycle serialization. This is retirement, never a reconnect request. */
static void owner_phy_fence(struct samurai_apsd_owner *o)
{
	unsigned long flags;

	spin_lock_irqsave(&o->lock, flags);
	o->blocked |= DWC3_APSD_PHY;
	o->abort = true;
	o->retiring = true;
	o->quarantined = true;
	spin_unlock_irqrestore(&o->lock, flags);
}

/* The caller already joined its API users. EBUSY deliberately retains both
 * handle and owner until exact restoration or completed supplier revocation. */
static int owner_phy_release(struct samurai_apsd_owner *o)
{
	int ret;

	if (!o->phy_client)
		return 0;
	ret = qcom_snps_hsphy_window_client_unregister(o->phy_client);
	if (!ret)
		o->phy_client = NULL;
	return ret;
}

static int owner_phy_cancel_join(void *context)
{
	struct samurai_apsd_owner *o = context;
	int ret = 0, release;

	/* Provider pins the actual context until this callback returns. It holds
	 * no provider/registry/PHY mutex while invoking us. */
	owner_phy_fence(o);
	mutex_lock(&owner_registry);
	if (o->dwc) {
		ret = owner_join(o, DWC3_APSD_PHY, true);
	} else {
		/* DWC unbind already joined us. Do not retry retained tokens through
		 * removed DWC MMIO, even if the PHY storage has not gone away yet. */
		cancel_delayed_work_sync(&o->work);
		if (o->phy.cookie || o->dwc_window.cookie || o->eud.cookie || o->extra_pm)
			ret = -ESHUTDOWN;
		else
			owner_pd_release(o);
	}
	release = owner_phy_release(o);
	if (!ret)
		ret = release;
	if (ret)
		o->phy_error = ret;
	mutex_unlock(&owner_registry);
	return ret;
}

static int owner_phy_resolve(struct samurai_apsd_owner *o)
{
	struct qcom_snps_hsphy_window_result state;
	static const struct qcom_snps_hsphy_window_client_ops ops = {
		.get_unless_zero = owner_pd_get,
		.put = owner_pd_put,
		.cancel_join = owner_phy_cancel_join,
	};
	int ret;

	if (!o->phy_client) {
		if (!o->dwc->usb2_generic_phy[0])
			return -EAGAIN;
		ret = qcom_snps_hsphy_window_client_register(o->dwc->usb2_generic_phy[0],
				&ops, o, &o->phy_client);
		if (ret == -ENODEV || ret == -EBUSY)
			return -EAGAIN;
		if (ret)
			return ret;
	}
	ret = qcom_snps_hsphy_window_status(o->phy_client, &state);
	if (!ret && state.revoked)
		ret = -ESHUTDOWN;
	if (ret == -ESHUTDOWN)
		owner_phy_fence(o);
	return ret;
}
