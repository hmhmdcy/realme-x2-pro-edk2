// SPDX-License-Identifier: GPL-2.0-only
/* Optional, single-controller DWC lifetime consumer, default off.
 * The separately opted-in PD5V client prepares real disabled-PD control only
 * after physical off. The explicit EUD-off route profile joins real supplier
 * revocation and validates its original lease again at the final transfer.
 */
#include <linux/module.h>
#include <linux/kref.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/mutex.h>
#include <linux/pm_runtime.h>
#include <linux/power_supply.h>
#include <linux/property.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/ktime.h>
#include <linux/usb/samurai-apsd-backend.h>
#include "core.h"
#include <linux/usb/samurai-pd5v.h>
#include <linux/usb/samurai-tcpm-apsd.h>
#include <linux/regmap.h>
#include "samurai-usb-input-decode.h"
#include "samurai-apsd-owner.h"
#include "samurai-apsd-once.h"
#include <linux/usb/samurai-eud-route.h>
#include "phy-qcom-snps-femto-v2-window.h"

enum owner_pd_phase {
 OWNER_PD_OFF, OWNER_PD_WAIT_BINDING, OWNER_PD_WAIT_FIRST_OFF,
 OWNER_PD_WAIT_ATTACH, OWNER_PD_SINK_EPOCH, OWNER_PD_FAILED,
};
struct samurai_apsd_owner {
	struct dwc3 *dwc;
 struct kref ref;
 struct device *typec;
 struct samurai_pd5v_lease pd_lease;
 enum owner_pd_phase pd_phase;
 u64 pd_binding;
 bool pd_bridge, pd_prepared;
 int pd_error;
	struct delayed_work work;
	struct notifier_block notifier;
	spinlock_t lock;
	unsigned int blocked;
	bool abort, retiring, registered, quarantined, extra_pm;
	const struct samurai_apsd_bus_ops *bus;
	void *bus_ctx;
	struct samurai_apsd_once once;
 struct samurai_apsd_bus_sample last_sample;
 struct samurai_apsd_attempt attempt;
 struct samurai_apsd_transfer_result transfer;
 void *attempt_bus;
 struct samurai_pd5v *attempt_pd;
 u64 attempt_generation;
 bool attempt_active;
	struct device *route_device;
	struct samurai_eud_route_client *route_client;
	struct samurai_eud_route_lease route_lease;
	struct dwc3_gadget_window_result dwc_window;
	struct qcom_snps_hsphy_window_result phy;
	struct qcom_snps_hsphy_window_client *phy_client;
	int primary_error, phy_error, dwc_error, route_error;
};

/* Public bind/unbind/bus registration and all lifecycle joins serialize here.
 * Worker/notifier NEVER take this mutex, so cancel_work_sync cannot deadlock
 * with a worker waiting for this registry. Only the work function owns tokens.
 * Lifecycle callers may touch tokens only after cancel_delayed_work_sync.
 */
static DEFINE_MUTEX(owner_registry);
/* Full TCPM publishes before joining the original worker. No provider or
 * native getter is called from this fence. Keep it across unbind/probe error:
 * there is no proved physical-detach rearm implementation in this candidate.
 */
static bool tcpm_fenced;
static struct device *tcpm_supplier;
static struct samurai_apsd_owner *bound_owner;
static struct device *bus_dev;
static const struct samurai_apsd_bus_ops *bus_ops;
static void *bus_ctx;
/* Logical UDC teardown/rebind does not create a physical attach epoch. */
static struct samurai_apsd_once protocol_history;
static u64 pd_history_binding;
static bool pd_history_prepared;
static int owner_join(struct samurai_apsd_owner *, unsigned int, bool);
static void owner_queue(struct samurai_apsd_owner *, unsigned long);

static void owner_free(struct kref *ref)
{
 struct samurai_apsd_owner *o = container_of(ref, struct samurai_apsd_owner, ref);
 if (o->typec)
  put_device(o->typec);
 if (o->route_device)
  put_device(o->route_device);
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
static void owner_pd_release(struct samurai_apsd_owner *o)
{
 if (IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT) && o->pd_lease.owner)
  samurai_pd5v_release(&o->pd_lease);
}

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

static int owner_route_pause_join(void *context)
{
	struct samurai_apsd_owner *o = context;
	unsigned long flags;
	int ret;

	/* Sleep is reversible; unlike removal it must not quarantine the owner. */
	spin_lock_irqsave(&o->lock, flags);
	o->blocked |= DWC3_APSD_ROUTE;
	o->abort = true;
	spin_unlock_irqrestore(&o->lock, flags);
	mutex_lock(&owner_registry);
	if (o->dwc)
		ret = owner_join(o, DWC3_APSD_ROUTE, READ_ONCE(o->retiring));
	else {
		cancel_delayed_work_sync(&o->work);
		ret = (o->phy.cookie || o->dwc_window.cookie || o->route_lease.client || o->extra_pm) ? -ESHUTDOWN : 0;
		if (!ret)
			owner_pd_release(o);
	}
	if (!ret && (o->phy.cookie || o->dwc_window.cookie || o->route_lease.client || o->extra_pm))
		ret = -EBUSY;
	if (ret) {
		o->route_error = ret;
		owner_route_fence(o);
	}
	mutex_unlock(&owner_registry);
	return ret;
}

static void owner_route_resume(void *context)
{
	struct samurai_apsd_owner *o = context;
	unsigned long flags;

	mutex_lock(&owner_registry);
	spin_lock_irqsave(&o->lock, flags);
	o->blocked &= ~DWC3_APSD_ROUTE;
	if (!o->blocked && !o->retiring && !o->quarantined)
		o->abort = false;
	spin_unlock_irqrestore(&o->lock, flags);
	/* PD/PHY/UDC keep their own blocked generations and physical-off history.
	 * This queues observation only; it does not reinitialize those suppliers. */
	if (o->dwc)
		owner_queue(o, 0);
	mutex_unlock(&owner_registry);
}

static int owner_route_resolve(struct samurai_apsd_owner *o)
{
	static const struct samurai_eud_route_client_ops ops = {
		.get_unless_zero = owner_pd_get,
		.put = owner_pd_put,
		.cancel_join = owner_route_cancel_join,
		.pause_join = owner_route_pause_join,
		.resume = owner_route_resume,
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
	if (!ret && state.paused)
		return -EAGAIN;
	if (!ret && (state.revoked || !state.exclusive))
		ret = -ESHUTDOWN;
	if (ret == -ESHUTDOWN)
		owner_route_fence(o);
	return ret;
}

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
		if (o->phy.cookie || o->dwc_window.cookie || o->route_lease.client || o->extra_pm)
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


static u64 owner_now_ms(void)
{
	return ktime_to_ms(ktime_get_boottime());
}

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

static void owner_quarantine(struct samurai_apsd_owner *o)
{
	unsigned long flags;

	spin_lock_irqsave(&o->lock, flags);
	o->quarantined = true;
	spin_unlock_irqrestore(&o->lock, flags);
}

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
  if (!o->phy.cookie && !o->dwc_window.cookie && !o->route_lease.client && !o->extra_pm)
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

/* The explicit profile needs all actual providers, never a caller Boolean. */
static int owner_entry_gate(struct samurai_apsd_owner *o)
{
	struct samurai_eud_route_status state;
	int ret;

	if (!o->bus || !o->bus->read_sample || !o->bus->rerun_once)
		return -ENODEV;
	if (!IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_EUD_OFF_CLIENT) ||
	    !o->route_client || !o->pd_bridge || !o->pd_prepared ||
	    o->pd_phase != OWNER_PD_SINK_EPOCH || !o->pd_lease.owner)
		return -EOPNOTSUPP;
	if (owner_aborted(o))
		return -ECANCELED;
	ret = samurai_pd5v_validate(&o->pd_lease);
	if (ret)
		return ret;
	ret = samurai_eud_route_status(o->route_client, &state);
	if (ret)
		return ret;
	if (state.revoked || !state.exclusive)
		return -ESHUTDOWN;
	return o->route_lease.client ? samurai_eud_route_validate(&o->route_lease) : 0;
}

/* Only this worker or its joined lifecycle owner calls component functions.
 * No registry spinlock, DWC/connect mutex, PHY mutex or EUD lock is held.
 * A failed restore retains the downstream quiet tokens; it is NOT restored.
 */
static int owner_restore(struct samurai_apsd_owner *o, bool retiring)
{
	int ret;

	if (o->phy.cookie) {
		/* Independent supplier/UDC joins must not retry an already failed
		 * restore or replace its original hardware error. */
		if (o->phy_error)
			return o->phy_error;
		ret = qcom_snps_hsphy_window_end(o->phy_client,
				o->phy.cookie, &o->phy);
		o->phy_error = ret;
		if (ret)
			return ret;
		o->phy.cookie = 0;
	}
	if (o->dwc_window.cookie) {
		if (retiring) {
			ret = dwc3_gadget_window_cancel(o->dwc,
					o->dwc_window.cookie, &o->dwc_window);
			o->dwc_error = ret;
			/* Existing window_shutdown, not end, consumes this token.
			 * Never reconnect briefly while UDC is being unbound.
			 */
			return ret;
		}
		ret = dwc3_gadget_window_end(o->dwc, o->dwc_window.cookie,
				&o->dwc_window);
		o->dwc_error = ret;
		if (ret)
			return ret;
		o->dwc_window.cookie = 0;
	}
	if (o->route_lease.client) {
		ret = samurai_eud_route_end(&o->route_lease);
		o->route_error = ret;
		if (ret)
			return ret;
	}
	if (o->extra_pm) {
		pm_runtime_put(o->dwc->dev);
		o->extra_pm = false;
	}
	return 0;
}

static int owner_enter_windows(struct samurai_apsd_owner *o)
{
	int ret;

	if (!o->phy_client || !o->route_client)
		return -ENODEV;

	ret = pm_runtime_get_if_active(o->dwc->dev);
	if (ret <= 0)
		return ret < 0 ? ret : -EAGAIN;
	o->extra_pm = true; /* stays through route release, beyond DWC end's put */
	ret = samurai_eud_route_begin(o->route_client, &o->route_lease);
	if (ret || owner_aborted(o))
		return ret ? ret : -ECANCELED;
	ret = dwc3_gadget_window_begin(o->dwc, &o->dwc_window);
	if (ret || owner_aborted(o))
		return ret ? ret : -ECANCELED;
	if (!o->dwc_window.halted)
		return -EIO;
	ret = qcom_snps_hsphy_window_begin(o->phy_client, &o->phy);
	if (ret || owner_aborted(o))
		return ret ? ret : -ECANCELED;
	return o->phy.high_z ? 0 : -EIO;
}

static int owner_read(struct samurai_apsd_owner *o)
{
	struct samurai_apsd_bus_sample sample = { };
	int ret;

	if (!o->bus)
		return -ENODEV;
	ret = o->bus->read_sample(o->bus_ctx, &sample);
	if (ret)
		return ret;
	o->last_sample = sample;
	if (!sample.present) {
		if (o->once.phase != SAMURAI_APSD_DETACHED)
			samurai_apsd_detach(&o->once);
  if (o->pd_bridge) {
   ret = owner_pd_observe(o, &sample);
   if (ret)
    return ret;
  }
  return -ENOLINK;
 }
	if (o->pd_bridge) {
  ret = owner_pd_observe(o, &sample);
  if (ret)
   return ret;
 }
 if (o->once.phase == SAMURAI_APSD_DETACHED) {
		ret = samurai_apsd_attach(&o->once, owner_now_ms());
		if (ret)
			return ret;
	}
	return samurai_apsd_sample(&o->once, o->once.epoch, owner_now_ms(),
			sample.serial, sample.raw[0], sample.raw[1]);
}

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
	if (!o->route_lease.client || !o->phy_client || !o->phy.cookie || !o->phy.high_z ||
	    !o->dwc_window.cookie || !o->dwc_window.halted || !o->extra_pm)
		return -ESTALE;
	ret = qcom_snps_hsphy_window_status(o->phy_client, &phy);
	if (ret)
		return ret;
	if (phy.revoked || !phy.high_z || phy.cookie != o->phy.cookie)
		return -ESHUTDOWN;
	/* Revalidate the exact live route lease after PD/PHY and fresh wire checks. */
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


static void owner_work(struct work_struct *work)
{
	struct samurai_apsd_owner *o = container_of(to_delayed_work(work),
			struct samurai_apsd_owner, work);
	int ret, restore;

	if (owner_aborted(o))
		return;
	ret = owner_route_resolve(o);
	if (!ret)
		ret = owner_phy_resolve(o);
	if (ret == -EAGAIN) {
		owner_queue(o, msecs_to_jiffies(1000));
		return;
	}
	if (ret) {
		o->primary_error = ret;
		if (owner_restore(o, READ_ONCE(o->retiring)))
			owner_quarantine(o);
		return;
	}
	ret = owner_read(o);
 if (o->pd_bridge && (ret == -EAGAIN || ret == -ENOLINK) && o->pd_phase != OWNER_PD_FAILED) {
  owner_queue(o, msecs_to_jiffies(1000));
  return;
 }
	if (ret == SAMURAI_APSD_REQUEST && !o->once.attempted) {
		ret = owner_entry_gate(o);
		if (ret) {
			o->primary_error = ret;
			return; /* no begin, no claim, no write; never fake a lease */
		}
		ret = owner_enter_windows(o);
		if (!ret)
			ret = owner_read(o); /* new physical read, not cached READY */
		if (ret == SAMURAI_APSD_REQUEST)
			ret = owner_entry_gate(o); /* MUST include real lease recheck */
		else if (ret >= 0)
			ret = -EAGAIN;
		if (!ret && owner_aborted(o))
			ret = -ECANCELED;
		if (!ret)
			ret = samurai_apsd_claim(&o->once, o->once.epoch,
					owner_now_ms(), owner_now_ms() + 5000);
		if (!ret) {
			ret = owner_transfer(o);
		}
	}
	if (o->once.phase == SAMURAI_APSD_WAIT_CLEAR ||
	    o->once.phase == SAMURAI_APSD_WAIT_DONE) {
		if (ret >= 0 && !owner_aborted(o)) {
			owner_queue(o, msecs_to_jiffies(100));
			return;
		}
	}
	if (ret < 0 && ret != -ENOLINK) {
		o->primary_error = ret;
		if (o->once.attempted)
			samurai_apsd_fail(&o->once, o->once.epoch, ret);
	}
	restore = owner_restore(o, READ_ONCE(o->retiring));
	if (restore)
		owner_quarantine(o);
}

static int owner_notify(struct notifier_block *nb, unsigned long event, void *data)
{
	struct samurai_apsd_owner *o = container_of(nb, struct samurai_apsd_owner,
			notifier);
	struct power_supply *psy = data;

	if (event == PSY_EVENT_PROP_CHANGED && psy && psy->desc &&
	    !strcmp(psy->desc->name, "samurai-usb-input"))
		owner_queue(o, 0);
	return NOTIFY_OK;
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

/* First full-PD takeover runs before tcpm_register_port(). The caller
 * holds no TCPM port, input, notifier, PHY or route lock. owner_registry only
 * serializes original lifecycle owners; the joined worker never takes it.
 * The real Type-C device is retained until its devres release action runs.
 */
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
EXPORT_SYMBOL_GPL(samurai_apsd_tcpm_quiesce);

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
EXPORT_SYMBOL_GPL(samurai_apsd_tcpm_release);

int samurai_apsd_bus_register(struct device *dev,
		const struct samurai_apsd_bus_ops *ops, void *ctx)
{
	unsigned long flags;
	int ret = 0;

	if (!dev || !ops || !ops->read_sample || !ops->rerun_once || !ctx)
		return -EINVAL;
	mutex_lock(&owner_registry);
	if (bus_dev) {
		ret = -EBUSY;
		goto out;
	}
	bus_dev = dev;
	bus_ops = ops;
	bus_ctx = ctx;
	if (bound_owner && bound_owner->dwc &&
	    !READ_ONCE(bound_owner->quarantined)) {
		/* Bind may already have queued a no-backend read. Join it before
		 * publishing ctx/ops as a pair, and never race a callback's ctx.
		 */
		owner_join(bound_owner, DWC3_APSD_EXIT, false);
		bound_owner->bus = ops;
		bound_owner->bus_ctx = ctx;
		spin_lock_irqsave(&bound_owner->lock, flags);
		bound_owner->blocked &= ~DWC3_APSD_EXIT;
		if (!bound_owner->blocked && !bound_owner->quarantined)
			bound_owner->abort = false;
		spin_unlock_irqrestore(&bound_owner->lock, flags);
		owner_queue(bound_owner, 0);
	}
out:
	mutex_unlock(&owner_registry);
	return ret;
}
EXPORT_SYMBOL_GPL(samurai_apsd_bus_register);

void samurai_apsd_bus_unregister(struct device *dev, void *ctx)
{
	mutex_lock(&owner_registry);
	if (bus_dev != dev || bus_ctx != ctx)
		goto out;
	if (bound_owner && bound_owner->dwc) {
		owner_join(bound_owner, DWC3_APSD_EXIT, false);
		bound_owner->bus = NULL;
		bound_owner->bus_ctx = NULL;
	}
	bus_dev = NULL;
	bus_ops = NULL;
	bus_ctx = NULL;
out:
	mutex_unlock(&owner_registry);
}
EXPORT_SYMBOL_GPL(samurai_apsd_bus_unregister);

void dwc3_apsd_owner_bind(struct dwc3 *dwc)
{
	struct samurai_apsd_owner *o;
	int ret;

	if (!device_property_read_bool(dwc->dev, "samurai,apsd-owner"))
		return;
	mutex_lock(&owner_registry);
	if (bound_owner)
		goto out;
	o = kzalloc(sizeof(*o), GFP_KERNEL);
	if (!o)
		goto out;
 kref_init(&o->ref);
	o->dwc = dwc;
 o->pd_bridge = device_property_read_bool(dwc->dev, "samurai,apsd-pd5v-bridge");
 if (o->pd_bridge) {
  o->pd_phase = OWNER_PD_WAIT_BINDING;
  if (!IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT) ||
      !IS_BUILTIN(CONFIG_TYPEC_QCOM_PMIC)) {
   o->pd_error = -EOPNOTSUPP;
   o->pd_phase = OWNER_PD_FAILED;
  }
 }
	o->bus = bus_ops;
	o->bus_ctx = bus_ctx;
	o->once = protocol_history;
	spin_lock_init(&o->lock);
	INIT_DELAYED_WORK(&o->work, owner_work);
	o->notifier.notifier_call = owner_notify;
	if (!dwc->gadget_driver)
		o->blocked = DWC3_APSD_UDC;
	ret = power_supply_reg_notifier(&o->notifier);
	if (ret) {
		kref_put(&o->ref, owner_free);
		goto out;
	}
	o->registered = true;
	bound_owner = o;
	owner_queue(o, 0);
out:
	mutex_unlock(&owner_registry);
}

int dwc3_apsd_owner_pause(struct dwc3 *dwc, unsigned int reason)
{
	int ret = 0;

	mutex_lock(&owner_registry);
	if (bound_owner && bound_owner->dwc == dwc)
		ret = owner_join(bound_owner, reason, false);
	mutex_unlock(&owner_registry);
	return ret;
}

void dwc3_apsd_owner_resume(struct dwc3 *dwc, unsigned int reason)
{
	struct samurai_apsd_owner *o;
	unsigned long flags;

	mutex_lock(&owner_registry);
	o = bound_owner;
	if (o && o->dwc == dwc) {
		spin_lock_irqsave(&o->lock, flags);
		o->blocked &= ~reason;
		if (!o->blocked && !o->quarantined)
			o->abort = o->retiring = false;
		spin_unlock_irqrestore(&o->lock, flags);
		owner_queue(o, 0);
	}
	mutex_unlock(&owner_registry);
}

void dwc3_apsd_owner_stop_pre(struct dwc3 *dwc)
{
	mutex_lock(&owner_registry);
	if (bound_owner && bound_owner->dwc == dwc)
		owner_join(bound_owner, DWC3_APSD_UDC, true);
	mutex_unlock(&owner_registry);
}

void dwc3_apsd_owner_stop_post(struct dwc3 *dwc)
{
	struct samurai_apsd_owner *o;

	mutex_lock(&owner_registry);
	o = bound_owner;
	if (o && o->dwc == dwc) {
		/* Called only after original window_shutdown. UDC stop has also
		 * freed its IRQ; gadget exit may still have its halted IRQ bound.
		 * This is
		 * retirement, never a successful DWC restore receipt.
		 */
		o->dwc_window.cookie = 0;
		if (!o->phy.cookie && owner_restore(o, false))
			owner_quarantine(o);
	}
	mutex_unlock(&owner_registry);
}

void dwc3_apsd_owner_unbind(struct dwc3 *dwc)
{
	struct samurai_apsd_owner *o;

	mutex_lock(&owner_registry);
	o = bound_owner;
	if (!o || o->dwc != dwc)
		goto out;
	owner_join(o, DWC3_APSD_EXIT, true);
	power_supply_unreg_notifier(&o->notifier);
	o->registered = false;
	cancel_delayed_work_sync(&o->work);
	if (owner_phy_release(o))
		owner_quarantine(o);
	if (owner_route_release(o))
		owner_quarantine(o);
	protocol_history = o->once;
 pd_history_binding = o->pd_binding;
 pd_history_prepared = o->pd_prepared;
	/* A retained failed PHY/route token is orphaned, not auto-restored through
	 * removed MMIO. Keep the tombstone and refuse a replacement controller.
	 */
	if (o->phy.cookie || o->route_lease.client || o->extra_pm) {
		owner_quarantine(o);
		o->dwc = NULL;
		o->bus = NULL;
		goto out;
	}
	bound_owner = NULL;
 o->dwc = NULL;
	kref_put(&o->ref, owner_free);
out:
	mutex_unlock(&owner_registry);
}

void dwc3_apsd_owner_core_exit(struct dwc3 *dwc)
{
	/* This also fences non-PM remove/error unwind paths before PHY/MMIO exit.
	 * PM callers already checked pause's error and refuse suspend on failure.
	 * Remove cannot be called a successful restore if this returns an error.
	 */
	dwc3_apsd_owner_pause(dwc, DWC3_APSD_CORE);
}
