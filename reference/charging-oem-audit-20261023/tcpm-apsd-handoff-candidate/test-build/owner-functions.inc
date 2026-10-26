static bool owner_aborted(struct samurai_apsd_owner *o)
{
	unsigned long flags;
	bool aborted;

	spin_lock_irqsave(&o->lock, flags);
	aborted = o->abort || o->blocked || o->quarantined || READ_ONCE(tcpm_fenced);
	spin_unlock_irqrestore(&o->lock, flags);
	return aborted;
}

static void owner_queue(struct samurai_apsd_owner *o, unsigned long delay)
{
	unsigned long flags;

	spin_lock_irqsave(&o->lock, flags);
	if (o->registered && !o->blocked && !o->abort && !o->quarantined &&
	    !READ_ONCE(tcpm_fenced))
		mod_delayed_work(system_wq, &o->work, delay);
	spin_unlock_irqrestore(&o->lock, flags);
}

static int owner_join(struct samurai_apsd_owner *o, unsigned int reason, bool retiring)
{
	unsigned long flags;
	int ret;

	spin_lock_irqsave(&o->lock, flags);
	o->blocked |= reason;
	o->abort = true;
	o->retiring |= retiring;
	spin_unlock_irqrestore(&o->lock, flags);
	cancel_delayed_work_sync(&o->work);
	if (o->once.phase != SAMURAI_APSD_DETACHED && o->once.attempted)
		samurai_apsd_cancel(&o->once, o->once.epoch);
	ret = owner_restore(o, retiring);
 if (!ret)
  owner_pd_release(o);
	if (ret) {
		owner_quarantine(o);
		dev_err(o->dwc->dev, "APSD owner retained quiet: primary=%d phy=%d dwc=%d route=%d\n",
			o->primary_error, o->phy_error, o->dwc_error, o->route_error);
	}
	return ret;
}

int samurai_apsd_tcpm_quiesce(struct device *typec, struct regmap *map)
{
	struct device_node *node;
	int ret = 0;

	if (!typec || !typec->parent || !map ||
	    !of_machine_is_compatible("realme,samurai") ||
	    !of_device_is_compatible(typec->of_node, "qcom,pm8150b-typec") ||
	    dev_get_regmap(typec->parent, NULL) != map)
		return -EXDEV;
	mutex_lock(&owner_registry);
	if (tcpm_supplier) {
		ret = -EBUSY;
		goto out;
	}
	if (bus_dev && (bus_dev->parent != typec->parent ||
		dev_get_regmap(bus_dev->parent, NULL) != map)) {
		ret = -EXDEV;
		goto out;
	}
	if (bound_owner && bound_owner->dwc) {
		node = of_parse_phandle(bound_owner->dwc->dev->of_node,
				"samurai,apsd-typec", 0);
		if (node != typec->of_node)
			ret = -EXDEV;
		of_node_put(node);
		if (ret)
			goto out;
	}
	tcpm_supplier = get_device(typec);
	/* Every acquisition/validation and later bind sees revocation first. */
	WRITE_ONCE(tcpm_fenced, true);
	if (bound_owner && bound_owner->dwc)
		ret = owner_join(bound_owner, DWC3_APSD_PD, false);
	if (ret) {
		put_device(tcpm_supplier);
		tcpm_supplier = NULL;
	}
out:
	mutex_unlock(&owner_registry);
	return ret;
}

void samurai_apsd_tcpm_release(struct device *typec)
{
	struct device *supplier = NULL;

	mutex_lock(&owner_registry);
	if (tcpm_supplier == typec) {
		supplier = tcpm_supplier;
		tcpm_supplier = NULL;
	}
	/* Never clear tcpm_fenced on remove, RX-off, PM, reset, or a software
	 * USB disconnect. Those do not prove physical detach/vSafe0V.
	 */
	mutex_unlock(&owner_registry);
	put_device(supplier);
}
