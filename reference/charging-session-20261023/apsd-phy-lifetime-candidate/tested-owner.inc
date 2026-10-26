static void owner_free(struct kref *ref)
{
 struct samurai_apsd_owner *o = container_of(ref, struct samurai_apsd_owner, ref);
 if (o->typec)
  put_device(o->typec);
 kfree(o);
}

static bool owner_pd_get(void *context)
{
 struct samurai_apsd_owner *o = context;
 return kref_get_unless_zero(&o->ref);
}

static void owner_pd_put(void *context)
{
 struct samurai_apsd_owner *o = context;
 kref_put(&o->ref, owner_free);
}

static bool owner_phy_binding_matches(struct samurai_apsd_owner *o,
 const struct qcom_snps_hsphy_window_binding *b)
{
 return o->phy_binding.phy == b->phy &&
  o->phy_binding.provider_id == b->provider_id &&
  o->phy_binding.client_id == b->client_id && b->context == o;
}

static int owner_phy_cancel_join(void *context,
 const struct qcom_snps_hsphy_window_binding *binding,
 enum qcom_snps_hsphy_window_reason reason)
{
 struct samurai_apsd_owner *o = context;
 bool terminal = reason == QCOM_HSPHY_WINDOW_REMOVE ||
  reason == QCOM_HSPHY_WINDOW_SHUTDOWN;
 int ret = 0;

 mutex_lock(&owner_registry);
 if (!owner_phy_binding_matches(o, binding))
  goto out; /* client already unregistered after its own complete join */
 if (o->dwc)
  ret = owner_join(o, DWC3_APSD_PHY, terminal);
 else {
  cancel_delayed_work_sync(&o->work);
  /* Never retry orphan hardware via a removed DWC/generic PHY owner. */
  if (o->phy.cookie)
   ret = -ESHUTDOWN;
 }
 if (reason == QCOM_HSPHY_WINDOW_REMOVE || reason == QCOM_HSPHY_WINDOW_SHUTDOWN)
  owner_quarantine(o);
out:
 mutex_unlock(&owner_registry);
 return ret;
}

static void owner_phy_complete(void *context,
 const struct qcom_snps_hsphy_window_binding *binding)
{
 struct samurai_apsd_owner *o = context;
 unsigned long flags;

 mutex_lock(&owner_registry);
 if (o->dwc && owner_phy_binding_matches(o, binding)) {
  spin_lock_irqsave(&o->lock, flags);
  o->blocked &= ~DWC3_APSD_PHY;
  if (!o->blocked && !o->retiring && !o->quarantined)
   o->abort = false;
  spin_unlock_irqrestore(&o->lock, flags);
  owner_queue(o, 0); /* metadata/sample only; entry gate still refuses */
 }
 mutex_unlock(&owner_registry);
}

static int owner_phy_attach(struct samurai_apsd_owner *o)
{
 const struct qcom_snps_hsphy_window_client client = {
  .context = o, .get_unless_zero = owner_pd_get, .put = owner_pd_put,
  .cancel_join = owner_phy_cancel_join, .complete = owner_phy_complete,
 };
 return qcom_snps_hsphy_window_client_register(o->dwc->usb2_generic_phy[0],
  &client, &o->phy_binding);
}

static void owner_phy_detach(struct samurai_apsd_owner *o)
{
 if (o->phy_binding.phy)
  qcom_snps_hsphy_window_client_unregister(&o->phy_binding);
}

static int owner_entry_gate(struct samurai_apsd_owner *o)
{
	if (!o->bus || !o->bus->read_sample || !o->bus->rerun_once)
		return -ENODEV;
 /* Real PD acquisition is separate from these still-missing capabilities.
  * This unconditional refusal MUST remain: no EUD/DWC/PHY begin or1341 path
  * becomes reachable through the new PD bridge. */
 return -EOPNOTSUPP; /* route + final-write contract absent; PHY lifetime alone grants nothing */
}
