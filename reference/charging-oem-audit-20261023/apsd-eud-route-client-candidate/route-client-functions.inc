/* Provider callbacks publish a permanent fence before lifecycle serialization.
 * A route-only withdrawal may restore a live gadget normally. An already
 * retiring UDC keeps its original cancel/shutdown sequence and quiet tokens.
 */
static void owner_route_fence(struct samurai_apsd_owner *o)
{
	unsigned long flags;

	spin_lock_irqsave(&o->lock, flags);
	o->blocked |= DWC3_APSD_ROUTE;
	o->abort = true;
	o->quarantined = true;
	spin_unlock_irqrestore(&o->lock, flags);
}

static int owner_route_release(struct samurai_apsd_owner *o)
{
	int ret;

	if (!o->route_client)
		return 0;
	ret = samurai_eud_route_client_unregister(o->route_client);
	if (!ret)
		o->route_client = NULL;
	return ret;
}

static int owner_route_cancel_join(void *context)
{
	struct samurai_apsd_owner *o = context;
	int ret;

	owner_route_fence(o);
	mutex_lock(&owner_registry);
	if (o->dwc)
		ret = owner_join(o, DWC3_APSD_ROUTE, READ_ONCE(o->retiring));
	else {
		cancel_delayed_work_sync(&o->work);
		ret = (o->phy.cookie || o->dwc_window.cookie || o->route_lease.client || o->extra_pm) ? -ESHUTDOWN : 0;
		if (!ret)
			owner_pd_release(o);
	}
	/* A successful DWC cancel can still retain its shutdown-owned token.
	 * Never acknowledge that as a fully joined/released route capability. */
	if (!ret && (o->phy.cookie || o->dwc_window.cookie || o->route_lease.client || o->extra_pm))
		ret = -EBUSY;
	if (!ret)
		ret = owner_route_release(o);
	if (ret)
		o->route_error = ret;
	mutex_unlock(&owner_registry);
	return ret;
}

static int owner_route_resolve(struct samurai_apsd_owner *o)
{
	static const struct samurai_eud_route_client_ops ops = {
		.get_unless_zero = owner_pd_get,
		.put = owner_pd_put,
		.cancel_join = owner_route_cancel_join,
	};
	struct samurai_eud_route_status state;
	struct device_node *node;
	struct platform_device *pdev;
	int ret;

	if (!IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_EUD_OFF_CLIENT))
		return -EOPNOTSUPP;
	if (!o->route_device) {
		node = of_parse_phandle(o->dwc->dev->of_node, "samurai,apsd-eud-route", 0);
		if (!node)
			return -EINVAL;
		pdev = of_find_device_by_node(node);
		of_node_put(node);
		if (!pdev)
			return -EAGAIN;
		o->route_device = &pdev->dev;
	}
	if (!o->route_client) {
		ret = samurai_eud_route_client_register(o->route_device, o->dwc->dev, &ops, o, &o->route_client);
		if (ret == -ENODEV)
			return -EAGAIN;
		if (ret)
			return ret;
	}
	ret = samurai_eud_route_status(o->route_client, &state);
	if (!ret && (state.revoked || !state.exclusive))
		ret = -ESHUTDOWN;
	if (ret == -ESHUTDOWN)
		owner_route_fence(o);
	return ret;
}
