/* Only process-context owner worker/lifecycle uses this real lease.
 * PD5V invokes cancel outside its mutex with an extra actual kref pin. */
static void owner_pd_cancel_join(void *context)
{
 struct samurai_apsd_owner *o = context;
 unsigned long flags;
 int ret = 0;

 mutex_lock(&owner_registry);
 if (o->dwc)
  ret = owner_join(o, DWC3_APSD_PD, false);
 else {
  /* Unbind already joined the worker. Never retry old MMIO via an orphan. */
  cancel_delayed_work_sync(&o->work);
  if (!o->phy.cookie && !o->dwc_window.cookie && !o->eud.cookie && !o->extra_pm)
   owner_pd_release(o);
 }
 if (!ret) {
  spin_lock_irqsave(&o->lock, flags);
  o->blocked &= ~DWC3_APSD_PD;
  if (!o->blocked && !o->retiring && !o->quarantined)
   o->abort = false;
  spin_unlock_irqrestore(&o->lock, flags);
  /* This can only observe blocked metadata until Type-C complete. It cannot
   * enable/reset/retry PD; the real control instance preserves its history. */
  owner_queue(o, msecs_to_jiffies(1000));
 }
 mutex_unlock(&owner_registry);
}

static int owner_pd_resolve(struct samurai_apsd_owner *o)
{
 struct device_node *np;
 struct platform_device *pdev;
 if (o->typec)
  return 0;
 np = of_parse_phandle(o->dwc->dev->of_node, "samurai,apsd-typec", 0);
 if (!np)
  return -EINVAL;
 pdev = of_find_device_by_node(np);
 of_node_put(np);
 if (!pdev)
  return -EPROBE_DEFER;
 o->typec = &pdev->dev; /* caller owns of_find_device_by_node's reference */
 return 0;
}

static int owner_pd_observe(struct samurai_apsd_owner *o,
 const struct samurai_apsd_bus_sample *sample)
{
 struct samurai_pd5v_status status = { };
 struct samurai_pd5v_client client = {
  .context = o, .get_unless_zero = owner_pd_get,
  .put = owner_pd_put, .cancel_join = owner_pd_cancel_join,
 };
 struct samurai_usb_status wire;
 struct samurai_usb_budget budget;
 int ret;

 if (!IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT) ||
     !IS_BUILTIN(CONFIG_TYPEC_QCOM_PMIC))
  return -EOPNOTSUPP;
 if (o->pd_phase == OWNER_PD_FAILED)
  return o->pd_error ? o->pd_error : -EIO;
 if (owner_aborted(o))
  return -ECANCELED;
 ret = owner_pd_resolve(o);
 if (ret == -EPROBE_DEFER)
  return -EAGAIN;
 if (ret)
  goto failed;
 if (!bus_dev)
  return -ENODEV;
 ret = qcom_pmic_typec_5v_status(o->typec, bus_dev, &status);
 if (ret == -ENODEV) {
  o->pd_error = ret;
  o->pd_phase = OWNER_PD_WAIT_BINDING;
  return -EAGAIN;
 }
 if (ret)
  goto failed;
 if (status.binding_id != o->pd_binding) {
  o->pd_binding = status.binding_id;
  o->pd_prepared = status.binding_id == pd_history_binding && pd_history_prepared;
 }
 if (status.error) {
  ret = status.error;
  goto failed;
 }
 if (status.blocked) {
  o->pd_error = -EBUSY;
  return -EAGAIN;
 }
 if (!o->pd_lease.owner) {
  /* Even an initialized replacement must see a real off before a new
   * eligible epoch. Rebind of this same prepared instance is different. */
  if (sample->present && (!status.initialized || !o->pd_prepared)) {
   o->pd_phase = OWNER_PD_WAIT_FIRST_OFF;
   return -EAGAIN;
  }
  if (owner_aborted(o))
   return -ECANCELED;
  ret = qcom_pmic_typec_5v_acquire(o->typec, &client, &o->pd_lease);
  if (ret) {
   /* Read-only metadata distinguishes pre-takeover instability from a
    * failed/unknown power or write attempt. Never pardon the latter. */
   int check = qcom_pmic_typec_5v_status(o->typec, bus_dev, &status);
   if (!check && !status.error && (ret == -EAGAIN || ret == -EBUSY)) {
    o->pd_error = ret;
    o->pd_phase = OWNER_PD_WAIT_FIRST_OFF;
    return -EAGAIN;
   }
   if (!check && status.error)
    ret = status.error;
   goto failed;
  }
  ret = qcom_pmic_typec_5v_status(o->typec, bus_dev, &status);
  if (ret)
   goto failed;
  if (status.binding_id != o->pd_binding) {
   /* Removal/reprobe may win between metadata and acquire. The real new
    * lease is valid, but it cannot inherit this client's old off history. */
   owner_pd_release(o);
   o->pd_binding = status.binding_id;
   o->pd_prepared = false;
   o->pd_error = -ESTALE;
   o->pd_phase = OWNER_PD_WAIT_FIRST_OFF;
   return -EAGAIN;
  }
  if (!sample->present)
   o->pd_prepared = true; /* actual first acquire verified vSafe0/off */
 }
 if (owner_aborted(o))
  return -ECANCELED;
 ret = samurai_pd5v_validate(&o->pd_lease);
 if (ret) {
  int check = qcom_pmic_typec_5v_status(o->typec, bus_dev, &status);
  /* PM may publish revocation while this worker is finishing acquisition.
   * Its cancel_join will release the lease after joining us. A known
   * blocked binding with no actual error is cancellation, not a new fault. */
  if (ret == -ESTALE && !check && status.blocked && !status.error) {
   o->pd_error = ret;
   o->pd_phase = OWNER_PD_WAIT_BINDING;
   return -EAGAIN;
  }
  if (!check && status.error)
   ret = status.error;
  goto failed;
 }
 if (!sample->present) {
  o->pd_phase = OWNER_PD_WAIT_ATTACH;
  return 0;
 }
 memcpy(&wire, sample->raw, sizeof(wire));
 ret = samurai_usb_decode(&wire, &budget);
 if (ret || !budget.online) {
  o->pd_error = ret ? ret : -EAGAIN;
  return -EAGAIN;
 }
 if (!o->pd_prepared) {
  o->pd_phase = OWNER_PD_WAIT_FIRST_OFF;
  return -EAGAIN;
 }
 o->pd_phase = OWNER_PD_SINK_EPOCH;
 return 0;
failed:
 o->pd_error = ret;
 o->pd_phase = OWNER_PD_FAILED;
 return ret;
}
