// SPDX-License-Identifier: GPL-2.0-only
/* Offline managed-charging candidate for RMX1931. See README before deployment.
 * No match for the installed mps,mp2650 observer; no probe-time OEM init replay.
 */
#include <linux/delay.h>
#include <linux/i2c.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/pm.h>
#include <linux/power_supply.h>
#include <linux/property.h>
#include <linux/workqueue.h>

#include "mp2650-core.h"
#include "charge-cycle.h"
#include "gauge-i2c.h"
#include "charging-notify.h"

static bool control;
module_param(control, bool, 0444);
MODULE_PARM_DESC(control, "Enable managed writes; default is shadow mode");
static bool runtime_board;
module_param(runtime_board, bool, 0444);
MODULE_PARM_DESC(runtime_board, "Use the observed RMX1931 board wiring without changing DT");

struct sm_charger {
	struct i2c_client *client, *gauge;
	struct power_supply *input, *protection, *psy, *battery;
	char *battery_name;
	struct mutex lock;
	struct delayed_work work;
	struct sm_io io;
	struct sm_sample sample;
	struct sm_target target;
	int cell_ceiling_uv, current_cap_ua, input_cap_ua;
	int last_error, stop_error;
	bool auto_requested, latched, paused, sample_full;
	bool source_inhibit;
	ktime_t sampled_at;
	struct sm_charge_cycle cycle;
	struct sm_thermal_state thermal;
	enum sm_policy_reason thermal_reason;
	struct notifier_block supply_notifier;
	bool notifier_registered;
	struct sm_notify_state notified;
	bool notified_valid;
};

static int sm_read(void *ctx, unsigned int reg)
{
	struct sm_charger *c = ctx;

	return i2c_smbus_read_byte_data(c->client, reg);
}

static int sm_write(void *ctx, unsigned int reg, unsigned int value)
{
	struct sm_charger *c = ctx;

	return i2c_smbus_write_byte_data(c->client, reg, value);
}

static int sm_gauge_sample(struct sm_charger *c, struct sm_sample *s)
{
	struct i2c_client *g = c->gauge;
	unsigned char packet[36];
	int temp, pack, flags, ret;

	i2c_lock_bus(g->adapter, I2C_LOCK_SEGMENT);
	temp = sm_gauge_word_locked(g, 0x06, false, 0);
	pack = sm_gauge_word_locked(g, 0x08, false, 0);
	flags = sm_gauge_word_locked(g, 0x0a, false, 0);
	if (temp < 0 || pack < 0 || flags < 0) {
		ret = temp < 0 ? temp : pack < 0 ? pack : flags;
		goto out;
	}
	ret = sm_gauge_mac_locked(g, 0x0071, packet);
	if (ret) goto out;
	s->temp_decic = temp - 2731;
	s->pack_uv = pack * 1000;
	s->gauge_flags = flags;
	s->cell1_uv = sm_le16(packet + 2) * 1000;
	s->cell2_uv = sm_le16(packet + 4) * 1000;
out:
	i2c_unlock_bus(g->adapter, I2C_LOCK_SEGMENT);
	return ret;
}

static int sm_psy_int(struct power_supply *psy,
		      enum power_supply_property property, int *value)
{
	union power_supply_propval v;
	int ret = power_supply_get_property(psy, property, &v);

	if (!ret) *value = v.intval;
	return ret;
}

static int sm_collect(struct sm_charger *c, struct sm_sample *s)
{
	int online, status, present, health, ret, budget_after, online_after;

	*s = (struct sm_sample){ 0 };
	c->source_inhibit = false;
	c->sample_full = false;
	ret = sm_psy_int(c->input, POWER_SUPPLY_PROP_ONLINE, &online);
	if (ret) { c->source_inhibit = true; return ret; }
	status = sm_read(c, 0x13);
	if (status < 0) return status;
	if (!!online != !!(status & 0x02)) { c->source_inhibit = true; return -EAGAIN; }
	s->online = !!online;
	if (!s->online) {
		/* Only an agreed physical detach resets the session and fault latch. */
		sm_cycle_update(&c->cycle, ktime_get_boottime_ns(), 0, 0);
		c->latched = false;
		c->thermal.hold = SM_THERMAL_NONE;
		s->valid = s->protection_ok = 1;
		return 0;
	}
	ret = sm_psy_int(c->input, POWER_SUPPLY_PROP_CURRENT_MAX, &s->budget_ua);
	if (ret) { c->source_inhibit = true; return ret; }
	if (s->budget_ua < 50000) { c->source_inhibit = true; return -ENODATA; }
	if (c->protection) {
		ret = sm_psy_int(c->protection, POWER_SUPPLY_PROP_PRESENT, &present);
		if (ret) return ret;
		ret = sm_psy_int(c->protection, POWER_SUPPLY_PROP_HEALTH, &health);
		if (ret) return ret;
		s->protection_ok = present == 1 && health == POWER_SUPPLY_HEALTH_GOOD;
	}
	ret = sm_gauge_sample(c, s);
	if (ret) return ret;
	/* One owning read per poll, cached for sysfs; never discard a prior fault. */
	ret = sm_read(c, 0x14);
	if (ret < 0) return ret;
	s->fault = ret;
	/* A changing source budget/attachment cannot authorize this sample. */
	ret = sm_psy_int(c->input, POWER_SUPPLY_PROP_ONLINE, &online_after);
	if (ret) { c->source_inhibit = true; return ret; }
	ret = sm_psy_int(c->input, POWER_SUPPLY_PROP_CURRENT_MAX, &budget_after);
	if (ret) { c->source_inhibit = true; return ret; }
	status = sm_read(c, 0x13);
	if (status < 0) return status;
	if (!online_after || !(status & 2) || budget_after != s->budget_ua) {
		c->source_inhibit = true;
		return -EAGAIN;
	}
	c->sample_full = (status & 0x0c) == 0x0c;
	s->valid = 1;
	return 0;
}

/* Caller holds c->lock. Sysfs limits are applied synchronously, too. */
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

/* Called after the safety step, with c->lock held and no I2C bus lock held.
 * bq27xxx STATUS reads its own signed current/FC flags; do not infer net battery
 * charging from CHG_EN or the charger's switching state.
 */
static bool sm_notification_locked(struct sm_charger *c)
{
	struct sm_notify_state state = {
		.health = c->last_error || c->latched || c->stop_error ?
			POWER_SUPPLY_HEALTH_UNSPEC_FAILURE : POWER_SUPPLY_HEALTH_GOOD,
		.error = c->last_error,
		.stop_error = c->stop_error,
		.latched = c->latched,
		.source_inhibit = c->source_inhibit,
		.auto_requested = c->auto_requested,
		.valid = c->sample.valid,
		.online = c->sample.online,
		.protection_ok = c->sample.protection_ok,
		.fault = c->sample.fault,
		.target_enable = c->target.enable,
		.input_ua = c->target.input_ua,
		.current_ua = c->target.current_ua,
		.cell_uv = c->target.cell_uv,
	};
	bool changed;
	int reg;

	/* Sample after sm_step_locked() has completed any hardware writes. */
	reg = sm_read(c, 0x13);
	if (reg < 0)
		state.charger_error = reg;
	else
		state.charger_status = reg & 0x0e; /* ONLINE and CHG_STAT only */
	state.battery_error = sm_psy_int(c->battery, POWER_SUPPLY_PROP_STATUS,
				       &state.battery_status);
	changed = !c->notified_valid || sm_notify_changed(&c->notified, &state);
	c->notified = state;
	c->notified_valid = true;
	return changed;
}

static void sm_poll(struct work_struct *work)
{
	struct sm_charger *c = container_of(to_delayed_work(work),
					 struct sm_charger, work);
	bool notify = false;

	mutex_lock(&c->lock);
	if (c->paused) goto out;
	sm_step_locked(c);
	notify = sm_notification_locked(c);
	schedule_delayed_work(&c->work, msecs_to_jiffies(1000));
out:
	mutex_unlock(&c->lock);
	if (notify)
		power_supply_changed(c->psy);
}

static int sm_supply_changed(struct notifier_block *nb, unsigned long event, void *data)
{
	struct sm_charger *c = container_of(nb, struct sm_charger, supply_notifier);
	if (event == PSY_EVENT_PROP_CHANGED && (data == c->input || data == c->protection) &&
	    !READ_ONCE(c->paused)) mod_delayed_work(system_wq, &c->work, 0);
	return NOTIFY_DONE;
}

/* Preserve the installed observer's stable-high/low/high ADC read protocol. */
static int sm_adc(struct sm_charger *c, unsigned int low_reg, int *code)
{
	int high, low, after;

	for (int attempt = 0; attempt < 3; attempt++) {
		high = sm_read(c, low_reg + 1);
		if (high < 0) return high;
		low = sm_read(c, low_reg);
		if (low < 0) return low;
		after = sm_read(c, low_reg + 1);
		if (after < 0) return after;
		if (high == after) {
			*code = (high << 2) | (low >> 6);
			return 0;
		}
	}
	return -ENODATA;
}

static int sm_get_property(struct power_supply *psy,
			   enum power_supply_property prop,
			   union power_supply_propval *v)
{
	struct sm_charger *c = power_supply_get_drvdata(psy);
	int value, after, code, ret = 0;

	mutex_lock(&c->lock);
	switch (prop) {
	case POWER_SUPPLY_PROP_CHARGE_BEHAVIOUR:
		if (!control) { ret = -ENODATA; break; }
		v->intval = c->auto_requested ? POWER_SUPPLY_CHARGE_BEHAVIOUR_AUTO :
			POWER_SUPPLY_CHARGE_BEHAVIOUR_INHIBIT_CHARGE;
		break;
	case POWER_SUPPLY_PROP_HEALTH:
		v->intval = c->last_error || c->latched || c->stop_error ?
			POWER_SUPPLY_HEALTH_UNSPEC_FAILURE : POWER_SUPPLY_HEALTH_GOOD;
		break;
	case POWER_SUPPLY_PROP_MODEL_NAME:
		v->strval = control ? "samurai-mp2650-control-candidate" :
			"samurai-mp2650-shadow-candidate";
		break;
	case POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT:
		value = sm_read(c, 0x00);
		if (value < 0) { ret = value; break; }
		v->intval = (value & 0x7f) * 50000;
		break;
	case POWER_SUPPLY_PROP_CONSTANT_CHARGE_CURRENT:
		value = sm_read(c, 0x02);
		if (value < 0) { ret = value; break; }
		v->intval = (value & 0x7f) * 50000;
		break;
	case POWER_SUPPLY_PROP_CONSTANT_CHARGE_VOLTAGE:
		value = sm_read(c, 0x04);
		if (value < 0) { ret = value; break; }
		v->intval = 2 * (3712500 + ((value & 0x7e) >> 1) * 12500);
		break;
	case POWER_SUPPLY_PROP_VOLTAGE_NOW:
	case POWER_SUPPLY_PROP_CURRENT_NOW:
		value = sm_read(c, 0x13);
		if (value < 0) { ret = value; break; }
		if (!(value & 2)) { ret = -ENODATA; break; }
		ret = sm_adc(c, prop == POWER_SUPPLY_PROP_VOLTAGE_NOW ? 0x1c : 0x1e, &code);
		if (ret) break;
		after = sm_read(c, 0x13);
		if (after < 0) { ret = after; break; }
		if (!(after & 2) || ((after ^ value) & 0x0c)) { ret = -ENODATA; break; }
		v->intval = code * (prop == POWER_SUPPLY_PROP_VOLTAGE_NOW ? 25000 : 6250);
		break;
	case POWER_SUPPLY_PROP_ONLINE:
	case POWER_SUPPLY_PROP_STATUS:
		value = sm_read(c, 0x13);
		if (value < 0) { ret = value; break; }
		if (prop == POWER_SUPPLY_PROP_ONLINE) {
			v->intval = !!(value & 2);
			break;
		}
		v->intval = POWER_SUPPLY_STATUS_NOT_CHARGING;
		if (value & 2) {
			if ((value & 0x0c) == 0x0c)
				v->intval = POWER_SUPPLY_STATUS_FULL;
			else if (value & 0x0c)
				v->intval = POWER_SUPPLY_STATUS_CHARGING;
		}
		break;
	default:
		ret = -EINVAL;
	}
	mutex_unlock(&c->lock);
	return ret;
}

static int sm_set_property(struct power_supply *psy,
			   enum power_supply_property prop,
			   const union power_supply_propval *v)
{
	struct sm_charger *c = power_supply_get_drvdata(psy);
	int ret = 0;

	if (!control) return -EROFS;
	mutex_lock(&c->lock);
	if (c->paused) { ret = -EBUSY; goto out; }
	switch (prop) {
	case POWER_SUPPLY_PROP_CHARGE_BEHAVIOUR:
		if (v->intval != POWER_SUPPLY_CHARGE_BEHAVIOUR_AUTO &&
		    v->intval != POWER_SUPPLY_CHARGE_BEHAVIOUR_INHIBIT_CHARGE) {
			ret = -EINVAL;
			break;
		}
		c->auto_requested = v->intval == POWER_SUPPLY_CHARGE_BEHAVIOUR_AUTO;
		/* Explicit operator recovery; the next poll must obtain fresh inputs. */
		if (c->auto_requested) c->latched = false;
		else {
			c->stop_error = sm_stop(&c->io);
			ret = c->stop_error;
		}
		break;
	case POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT:
		if (v->intval < 50000 || v->intval > SM_OEM_INPUT_MAX_UA)
			ret = -ERANGE;
		else c->input_cap_ua = v->intval;
		break;
	case POWER_SUPPLY_PROP_CONSTANT_CHARGE_CURRENT:
		if (v->intval < 200000 || v->intval > 1100000) ret = -ERANGE;
		else c->current_cap_ua = v->intval;
		break;
	default:
		ret = -EINVAL;
	}
	if (!ret) {
		ret = sm_step_locked(c);
		mod_delayed_work(system_wq, &c->work, msecs_to_jiffies(1000));
	}
out:
	mutex_unlock(&c->lock);
	power_supply_changed(c->psy);
	return ret;
}

static int sm_writeable(struct power_supply *psy, enum power_supply_property p)
{
	return control && (p == POWER_SUPPLY_PROP_CHARGE_BEHAVIOUR ||
		p == POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT ||
		p == POWER_SUPPLY_PROP_CONSTANT_CHARGE_CURRENT);
}

static const enum power_supply_property sm_properties[] = {
	POWER_SUPPLY_PROP_ONLINE, POWER_SUPPLY_PROP_STATUS, POWER_SUPPLY_PROP_HEALTH,
	POWER_SUPPLY_PROP_CHARGE_BEHAVIOUR, POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT,
	POWER_SUPPLY_PROP_CONSTANT_CHARGE_CURRENT,
	POWER_SUPPLY_PROP_CONSTANT_CHARGE_VOLTAGE,
	POWER_SUPPLY_PROP_VOLTAGE_NOW, POWER_SUPPLY_PROP_CURRENT_NOW,
	POWER_SUPPLY_PROP_MODEL_NAME,
};

static const struct power_supply_desc sm_desc = {
	.name = "mp2650-input", .type = POWER_SUPPLY_TYPE_USB,
	.properties = sm_properties, .num_properties = ARRAY_SIZE(sm_properties),
	.charge_behaviours = BIT(POWER_SUPPLY_CHARGE_BEHAVIOUR_AUTO) |
		BIT(POWER_SUPPLY_CHARGE_BEHAVIOUR_INHIBIT_CHARGE),
	.get_property = sm_get_property, .set_property = sm_set_property,
	.property_is_writeable = sm_writeable,
};

static void sm_put_gauge(void *data) { put_device(data); }
static void sm_put_supply(void *data) { power_supply_put(data); }
static void sm_put_module(void *data) { module_put(data); }

static struct power_supply *sm_named_supply(struct device *dev, const char *name)
{
	struct power_supply *psy = power_supply_get_by_name(name);
	struct module *owner;
	struct device_link *link;
	int ret;

	if (!psy) return ERR_PTR(-EPROBE_DEFER);
	ret = devm_add_action_or_reset(dev, sm_put_supply, psy);
	if (ret) return ERR_PTR(ret);
	/* Prevent a manually loaded provider from unloading while referenced. */
	owner = psy->dev.parent && psy->dev.parent->driver ?
		psy->dev.parent->driver->owner : NULL;
	if (owner) {
		if (!try_module_get(owner)) return ERR_PTR(-ENODEV);
		ret = devm_add_action_or_reset(dev, sm_put_module, owner);
		if (ret) return ERR_PTR(ret);
	}
	/* Order system sleep after real suppliers are available. The device link
	 * is removed by the driver core on consumer unbind or failed probe.
	 */
	if (!psy->dev.parent) return ERR_PTR(-ENODEV);
	link = device_link_add(dev, psy->dev.parent, DL_FLAG_AUTOREMOVE_CONSUMER);
	if (!link) return ERR_PTR(-ENOMEM);
	return psy;
}

/* Root-readable diagnostic snapshot for the future shadow validation window.
 * Fields are an acquired sample, never a claim of independent protection.
 */
static ssize_t sm_telemetry_show(struct device *dev,
			       struct device_attribute *attr, char *buf)
{
	struct sm_charger *c = dev_get_drvdata(dev);
	ssize_t length;

	mutex_lock(&c->lock);
	length = sysfs_emit(buf,
		"shadow=%d valid=%d online=%d protection_ok=%d budget_ua=%d "
		"temp_decic=%d pack_uv=%d cell1_uv=%d cell2_uv=%d flags=%u "
		"fault=%u session_seconds=%u desired_enable=%d error=%d "
		"stop_error=%d latched=%d source_inhibit=%d thermal_inhibit=%d cycle_timeout=%d age_ms=%lld\n",
		!control, c->sample.valid, c->sample.online, c->sample.protection_ok,
		c->sample.budget_ua, c->sample.temp_decic, c->sample.pack_uv,
		c->sample.cell1_uv, c->sample.cell2_uv, c->sample.gauge_flags,
		c->sample.fault, c->sample.session_seconds, c->target.enable,
		c->last_error, c->stop_error, c->latched,
		c->source_inhibit, c->thermal_reason, c->cycle.timed_out,
		c->sample.valid ? ktime_to_ms(ktime_sub(ktime_get_boottime(), c->sampled_at)) : -1LL);
	mutex_unlock(&c->lock);
	return length;
}

static DEVICE_ATTR(telemetry, 0400, sm_telemetry_show, NULL);
static struct attribute *sm_attributes[] = { &dev_attr_telemetry.attr, NULL };
static const struct attribute_group sm_attribute_group = { .attrs = sm_attributes };

static void sm_cleanup(void *data)
{
	struct sm_charger *c = data;
	int ret;

	if (c->notifier_registered) {
		power_supply_unreg_notifier(&c->supply_notifier);
		c->notifier_registered = false;
	}
	mutex_lock(&c->lock);
	c->paused = true;
	mutex_unlock(&c->lock);
	cancel_delayed_work_sync(&c->work);
	if (control) {
		ret = sm_stop(&c->io);
		if (ret) dev_err(&c->client->dev, "remove could not prove stop: %d\n", ret);
	}
}

static int sm_battery_notify_target(struct power_supply *psy, void *data)
{
	struct sm_charger *c = data;

	if (psy->desc->type != POWER_SUPPLY_TYPE_BATTERY ||
	    psy->dev.parent != &c->gauge->dev)
		return 0;
	if (c->battery_name)
		return -EEXIST;
	c->battery_name = devm_kstrdup(&c->client->dev, psy->desc->name, GFP_KERNEL);
	return c->battery_name ? 0 : -ENOMEM;
}

static int sm_probe(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct power_supply_config config = { 0 };
	struct device_node *node;
	struct sm_charger *c;
	int reg, ret;

	if (!of_machine_is_compatible("realme,samurai") || client->addr != 0x5c)
		return -ENODEV;
	if (!i2c_check_functionality(client->adapter, I2C_FUNC_SMBUS_BYTE_DATA))
		return -EOPNOTSUPP;
	/* Explicitly opt into the OEM MAC telemetry protocol after compatibility
	 * review. The observed extended 2719 identity alone is insufficient.
	 */
	if (!runtime_board && !device_property_read_bool(dev, "realme,bq28z610-cells-0071"))
		return dev_err_probe(dev, -EINVAL, "cell telemetry protocol not selected\n");
	c = devm_kzalloc(dev, sizeof(*c), GFP_KERNEL);
	if (!c) return -ENOMEM;
	c->client = client;
	c->io = (struct sm_io){ c, sm_read, sm_write };
	mutex_init(&c->lock);
	sm_cycle_init(&c->cycle, ktime_get_boottime_ns());
	INIT_DELAYED_WORK(&c->work, sm_poll);
	i2c_set_clientdata(client, c);
	c->input = runtime_board ? sm_named_supply(dev, "samurai-usb-input") :
		devm_power_supply_get_by_reference(dev, "input-supply");
	if (IS_ERR(c->input)) return dev_err_probe(dev, PTR_ERR(c->input), "input supply\n");
	if (runtime_board || device_property_present(dev, "protection-supply")) {
		c->protection = runtime_board ? sm_named_supply(dev, "samurai-gauge-protection") :
			devm_power_supply_get_by_reference(dev, "protection-supply");
		if (IS_ERR(c->protection))
			return dev_err_probe(dev, PTR_ERR(c->protection), "protection supply\n");
	}
	if (!c->input || (control && !c->protection))
		return dev_err_probe(dev, -EINVAL, "control requires a real protection supply\n");
	node = of_parse_phandle(dev->of_node, "battery-gauge", 0);
	if (!node && runtime_board)
		node = of_find_node_by_path("/soc@0/geniqup@cc0000/i2c@c94000/fuel-gauge@55");
	if (!node) return -EINVAL;
	c->gauge = of_find_i2c_device_by_node(node);
	of_node_put(node);
	if (!c->gauge) return -EPROBE_DEFER;
	ret = devm_add_action_or_reset(dev, sm_put_gauge, &c->gauge->dev);
	if (ret) return ret;
	if (c->gauge == client || c->gauge->addr != 0x55 ||
	    IS_ENABLED(CONFIG_BATTERY_BQ27XXX_DT_UPDATES_NVM) ||
	    !i2c_check_functionality(c->gauge->adapter,
		I2C_FUNC_SMBUS_WORD_DATA | I2C_FUNC_I2C))
		return -EOPNOTSUPP;
	if (!device_link_add(dev, &c->gauge->dev, DL_FLAG_AUTOREMOVE_CONSUMER))
		return -ENOMEM;
	ret = sm_preconditions(&c->io);
	if (ret) return dev_err_probe(dev, ret, "unsupported inherited charger state\n");
	reg = sm_read(c, 0x04);
	if (reg < 0) return reg;
	c->cell_ceiling_uv = 3712500 + ((reg & 0x7e) >> 1) * 12500;
	c->current_cap_ua = 1100000;
	c->input_cap_ua = SM_OEM_INPUT_MAX_UA;
	c->last_error = -ENODATA;
	config.drv_data = c;
	config.fwnode = dev_fwnode(dev);
	/* Route external-power changes to the existing gauge's standard callback.
	 * Without this supplier relation bq27xxx can wait for its 360s poll, while
	 * the desktop continues to display the previous charging state. Match the
	 * actual gauge parent, never a guessed global battery name.
	 */
	ret = power_supply_for_each_psy(c, sm_battery_notify_target);
	if (ret)
		return ret;
	if (!c->battery_name)
		return -EPROBE_DEFER;
	c->battery = power_supply_get_by_name(c->battery_name);
	if (!c->battery)
		return -EPROBE_DEFER;
	ret = devm_add_action_or_reset(dev, sm_put_supply, c->battery);
	if (ret)
		return ret;
	if (c->battery->desc->type != POWER_SUPPLY_TYPE_BATTERY ||
	    c->battery->dev.parent != &c->gauge->dev)
		return -ENODEV;
	config.supplied_to = &c->battery_name;
	config.num_supplicants = 1;
	c->psy = devm_power_supply_register(dev, &sm_desc, &config);
	if (IS_ERR(c->psy)) return PTR_ERR(c->psy);
	ret = devm_device_add_group(dev, &sm_attribute_group);
	if (ret) return ret;
	c->supply_notifier.notifier_call = sm_supply_changed;
	ret = power_supply_reg_notifier(&c->supply_notifier);
	if (ret) return ret;
	c->notifier_registered = true;
	ret = devm_add_action_or_reset(dev, sm_cleanup, c);
	if (ret) return ret;
	schedule_delayed_work(&c->work, 0);
	dev_info(dev, "offline candidate bound in %s mode, initially inhibited\n",
		 control ? "control" : "shadow");
	return 0;
}

static int sm_suspend(struct device *dev)
{
	struct sm_charger *c = dev_get_drvdata(dev);
	int ret = 0;

	mutex_lock(&c->lock);
	c->paused = true;
	mutex_unlock(&c->lock);
	cancel_delayed_work_sync(&c->work);
	mutex_lock(&c->lock);
	if (control) ret = sm_stop(&c->io);
	if (ret) {
		c->stop_error = c->last_error = ret;
		c->latched = true;
		c->paused = false;
		mod_delayed_work(system_wq, &c->work, 0);
	}
	mutex_unlock(&c->lock);
	return ret;
}

static int sm_resume(struct device *dev)
{
	struct sm_charger *c = dev_get_drvdata(dev);

	mutex_lock(&c->lock);
	c->paused = false;
	/* The first fresh post-resume sample is always reported. */
	c->notified_valid = false;
	mod_delayed_work(system_wq, &c->work, 0);
	mutex_unlock(&c->lock);
	return 0;
}

static void sm_shutdown(struct i2c_client *client) { sm_cleanup(i2c_get_clientdata(client)); }
static DEFINE_SIMPLE_DEV_PM_OPS(sm_pm_ops, sm_suspend, sm_resume);
static const struct of_device_id sm_match[] = {
	{ .compatible = "realme,samurai-mp2650-managed" }, { }
};
MODULE_DEVICE_TABLE(of, sm_match);
/* Explicitly loaded runtime_board can adopt the existing, first unbound
 * observer client. All board/protocol/provider checks still run at probe.
 */
static const struct i2c_device_id sm_ids[] = { { "mp2650" }, { } };
MODULE_DEVICE_TABLE(i2c, sm_ids);
static struct i2c_driver sm_driver = {
	.driver = { .name = "samurai-mp2650", .of_match_table = sm_match,
		.pm = pm_sleep_ptr(&sm_pm_ops) },
	.probe = sm_probe, .shutdown = sm_shutdown, .id_table = sm_ids,
};
module_i2c_driver(sm_driver);
MODULE_DESCRIPTION("RMX1931 OEM-profile managed MP2650 charging candidate");
MODULE_LICENSE("GPL");
