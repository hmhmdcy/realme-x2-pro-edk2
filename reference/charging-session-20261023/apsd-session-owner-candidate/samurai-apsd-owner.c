// SPDX-License-Identifier: GPL-2.0-only
/* Optional, single-controller DWC lifetime consumer. Not enabled on device.
 * No PD/route or EUD/PHY pre-remove lease exists in the fixed source yet.
 * The entry fence below therefore refuses EVERY hardware attempt, including
 * with an installed bus backend. Do not remove it to "enable" this candidate.
 */
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/pm_runtime.h>
#include <linux/power_supply.h>
#include <linux/property.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/ktime.h>
#include <linux/usb/samurai-apsd-backend.h>
#include "core.h"
#include "samurai-apsd-owner.h"
#include "samurai-apsd-once.h"
#include "eud-com-window.h"
#include "phy-qcom-snps-femto-v2-window.h"

struct samurai_apsd_owner {
	struct dwc3 *dwc;
	struct delayed_work work;
	struct notifier_block notifier;
	spinlock_t lock;
	unsigned int blocked;
	bool abort, retiring, registered, quarantined, extra_pm;
	const struct samurai_apsd_bus_ops *bus;
	void *bus_ctx;
	struct samurai_apsd_once once;
	struct eud_com_window_result eud;
	struct dwc3_gadget_window_result dwc_window;
	struct qcom_snps_hsphy_window_result phy;
	int primary_error, phy_error, dwc_error, eud_error;
};

/* Public bind/unbind/bus registration and all lifecycle joins serialize here.
 * Worker/notifier NEVER take this mutex, so cancel_work_sync cannot deadlock
 * with a worker waiting for this registry. Only the work function owns tokens.
 * Lifecycle callers may touch tokens only after cancel_delayed_work_sync.
 */
static DEFINE_MUTEX(owner_registry);
static struct samurai_apsd_owner *bound_owner;
static struct device *bus_dev;
static const struct samurai_apsd_bus_ops *bus_ops;
static void *bus_ctx;
/* Logical UDC teardown/rebind does not create a physical attach epoch. */
static struct samurai_apsd_once protocol_history;

static u64 owner_now_ms(void)
{
	return ktime_to_ms(ktime_get_boottime());
}

static bool owner_aborted(struct samurai_apsd_owner *o)
{
	unsigned long flags;
	bool aborted;

	spin_lock_irqsave(&o->lock, flags);
	aborted = o->abort || o->blocked || o->quarantined;
	spin_unlock_irqrestore(&o->lock, flags);
	return aborted;
}

static void owner_queue(struct samurai_apsd_owner *o, unsigned long delay)
{
	unsigned long flags;

	spin_lock_irqsave(&o->lock, flags);
	if (o->registered && !o->blocked && !o->abort && !o->quarantined)
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

/* This is a proven-missing prerequisite, NOT a fake successful lease or a
 * callback-presence test. OEM TCPM audit d4cf7b6b names the real invalidation
 * sites. No provider implements them or EUD/PHY pre-remove joining here.
 * A later revision must replace the entire contract with audited generation
 * acquire/revalidate/release and those driver lifecycle hooks as one change.
 */
static int owner_entry_gate(struct samurai_apsd_owner *o)
{
	if (!o->bus || !o->bus->read_sample || !o->bus->rerun_once)
		return -ENODEV;
	return -EOPNOTSUPP;
}

/* Only this worker or its joined lifecycle owner calls component functions.
 * No registry spinlock, DWC/connect mutex, PHY mutex or EUD lock is held.
 * A failed restore retains the downstream quiet tokens; it is NOT restored.
 */
static int owner_restore(struct samurai_apsd_owner *o, bool retiring)
{
	int ret;

	if (o->phy.cookie) {
		ret = qcom_snps_hsphy_window_end(o->dwc->usb2_generic_phy[0],
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
	if (o->eud.cookie) {
		ret = eud_com_quiet_end(o->eud.cookie, &o->eud);
		o->eud_error = ret;
		if (ret)
			return ret;
		o->eud.cookie = 0;
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

	ret = pm_runtime_get_if_active(o->dwc->dev);
	if (ret <= 0)
		return ret < 0 ? ret : -EAGAIN;
	o->extra_pm = true; /* stays through EUD restore, beyond DWC end's put */
	ret = eud_com_quiet_begin(&o->eud);
	if (ret || owner_aborted(o))
		return ret ? ret : -ECANCELED;
	ret = dwc3_gadget_window_begin(o->dwc, &o->dwc_window);
	if (ret || owner_aborted(o))
		return ret ? ret : -ECANCELED;
	if (!o->dwc_window.halted)
		return -EIO;
	ret = qcom_snps_hsphy_window_begin(o->dwc->usb2_generic_phy[0], &o->phy);
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
	if (!sample.present) {
		if (o->once.phase != SAMURAI_APSD_DETACHED)
			samurai_apsd_detach(&o->once);
		return -ENOLINK;
	}
	if (o->once.phase == SAMURAI_APSD_DETACHED) {
		ret = samurai_apsd_attach(&o->once, owner_now_ms());
		if (ret)
			return ret;
	}
	return samurai_apsd_sample(&o->once, o->once.epoch, owner_now_ms(),
			sample.serial, sample.raw[0], sample.raw[1]);
}

static void owner_work(struct work_struct *work)
{
	struct samurai_apsd_owner *o = container_of(to_delayed_work(work),
			struct samurai_apsd_owner, work);
	int ret, restore;

	if (owner_aborted(o))
		return;
	ret = owner_read(o);
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
			ret = o->bus->rerun_once(o->bus_ctx, o->once.epoch);
			samurai_apsd_write_done(&o->once, o->once.epoch,
					owner_now_ms(), ret);
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
	if (ret) {
		owner_quarantine(o);
		dev_err(o->dwc->dev, "APSD owner retained quiet: primary=%d phy=%d dwc=%d eud=%d\n",
			o->primary_error, o->phy_error, o->dwc_error, o->eud_error);
	}
	return ret;
}

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
	o->dwc = dwc;
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
		kfree(o);
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
	protocol_history = o->once;
	/* A retained failed PHY/EUD token is orphaned, not auto-restored through
	 * removed MMIO. Keep the tombstone and refuse a replacement controller.
	 */
	if (o->phy.cookie || o->eud.cookie || o->extra_pm) {
		owner_quarantine(o);
		o->dwc = NULL;
		o->bus = NULL;
		goto out;
	}
	bound_owner = NULL;
	kfree(o);
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
