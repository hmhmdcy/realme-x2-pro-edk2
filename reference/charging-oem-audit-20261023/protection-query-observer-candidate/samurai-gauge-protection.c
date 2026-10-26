// SPDX-License-Identifier: GPL-2.0-only
/* Fresh, read-only factory-family safety/PF/FET-state provider. */
#include <linux/i2c.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/power_supply.h>
#include <linux/property.h>
#include "gauge-i2c.h"

static bool register_board;
module_param(register_board, bool, 0444);
MODULE_PARM_DESC(register_board, "Create the RMX1931 observation device without changing DT");

/* Fixed observation recipe, never a user-supplied MAC selector. */
static const unsigned int sm_evidence_commands[] = {
	0x0001, 0x0051, 0x0053, 0x0054, 0x0057, 0x0050, 0x0052, 0x0056,
};
enum sm_evidence_stage {
	SM_EVIDENCE_NONE, SM_EVIDENCE_ID_FRAME, SM_EVIDENCE_ID_VALUE,
	SM_EVIDENCE_BATTERY_BEFORE, SM_EVIDENCE_STATUS_FRAME,
	SM_EVIDENCE_BATTERY_AFTER, SM_EVIDENCE_COMPLETE,
};
struct sm_mac_evidence {
	bool attempted, terminal;
	unsigned int stage, frames_attempted;
	int error, battery_before, battery_after;
	bool battery_before_valid, battery_after_valid;
	u64 started_ns, battery_before_ns, battery_after_ns, ended_ns;
	struct sm_mac_receipt frames[ARRAY_SIZE(sm_evidence_commands)];
};

struct sm_protection {
	struct i2c_client *gauge;
	struct mutex lock;
	unsigned int id, safety, permanent, operation, manufacturing;
	int last_error;
	struct sm_mac_evidence evidence;
};

static struct platform_device *sm_board;

static int sm_protection_read(struct sm_protection *p)
{
	static const unsigned int commands[] = { 1, 0x51, 0x53, 0x54, 0x57 };
	unsigned int *values[] = { &p->id, &p->safety, &p->permanent,
		&p->operation, &p->manufacturing };
	unsigned char packet[36];
	int ret = 0;

	i2c_lock_bus(p->gauge->adapter, I2C_LOCK_SEGMENT);
	for (int i = 0; i < ARRAY_SIZE(commands); i++) {
		ret = sm_gauge_mac_locked(p->gauge, commands[i], packet);
		if (ret) break;
		*values[i] = sm_mac_data_size(commands[i]) == 2 ?
			sm_le16(packet + 2) : sm_le32(packet + 2);
	}
	i2c_unlock_bus(p->gauge->adapter, I2C_LOCK_SEGMENT);
	if (!ret)
		ret = sm_gauge_protection_state(p->id, p->safety, p->permanent,
			p->operation, p->manufacturing);
	p->last_error = ret;
	return ret;
}

/* Caller holds p->lock. One attempt, including failure, per bound instance.
 * Do not change normal health values/last_error, policy, latch or timer here.
 */
static int sm_protection_capture_locked(struct sm_protection *p)
{
	struct sm_mac_evidence *e = &p->evidence;
	int ret;

	if (e->attempted) return -EALREADY;
	*e = (struct sm_mac_evidence){ .attempted = true };
	e->started_ns = ktime_get_boottime_ns();
	for (unsigned int i = 0; i < ARRAY_SIZE(sm_evidence_commands); i++) {
		e->frames[i].command = sm_evidence_commands[i];
		e->frames[i].expected_size = sm_mac_observe_data_size(sm_evidence_commands[i]);
	}
	i2c_lock_bus(p->gauge->adapter, I2C_LOCK_SEGMENT);
	e->stage = SM_EVIDENCE_ID_FRAME;
	e->frames_attempted = 1;
	ret = sm_gauge_mac_observe_locked(p->gauge, 0x0001, &e->frames[0]);
	if (ret) goto out;
	e->stage = SM_EVIDENCE_ID_VALUE;
	if (sm_le16(e->frames[0].raw + 2) != 0x2719) { ret = -ENODEV; goto out; }
	e->stage = SM_EVIDENCE_BATTERY_BEFORE;
	ret = sm_gauge_word_locked(p->gauge, 0x0a, false, 0);
	e->battery_before_ns = ktime_get_boottime_ns();
	if (ret < 0) goto out;
	e->battery_before = ret; e->battery_before_valid = true;
	for (unsigned int i = 1; i < ARRAY_SIZE(sm_evidence_commands); i++) {
		e->stage = SM_EVIDENCE_STATUS_FRAME;
		e->frames_attempted = i + 1;
		ret = sm_gauge_mac_observe_locked(p->gauge, sm_evidence_commands[i], &e->frames[i]);
		if (ret) goto out;
	}
	e->stage = SM_EVIDENCE_BATTERY_AFTER;
	ret = sm_gauge_word_locked(p->gauge, 0x0a, false, 0);
	e->battery_after_ns = ktime_get_boottime_ns();
	if (ret < 0) goto out;
	e->battery_after = ret; e->battery_after_valid = true;
	ret = 0; e->stage = SM_EVIDENCE_COMPLETE;
out:
	i2c_unlock_bus(p->gauge->adapter, I2C_LOCK_SEGMENT);
	e->error = ret; e->ended_ns = ktime_get_boottime_ns(); e->terminal = true;
	return ret;
}

static ssize_t mac_evidence_capture_store(struct device *dev,
	struct device_attribute *attr, const char *buf, size_t count)
{
	struct sm_protection *p = dev_get_drvdata(dev);
	int ret;

	if (!sysfs_streq(buf, "capture")) return -EINVAL;
	mutex_lock(&p->lock);
	ret = sm_protection_capture_locked(p);
	mutex_unlock(&p->lock);
	return ret ? ret : count;
}
static DEVICE_ATTR(mac_evidence_capture, 0200, NULL, mac_evidence_capture_store);

/* Pure cached reads: even attempted=0 never starts an I2C transaction. */
static ssize_t mac_evidence_show(struct device *dev,
	struct device_attribute *attr, char *buf)
{
	struct sm_protection *p = dev_get_drvdata(dev);
	struct sm_mac_evidence *e = &p->evidence;
	ssize_t n;

	mutex_lock(&p->lock);
	n = sysfs_emit(buf, "schema=1 attempted=%d terminal=%d stage=%u error=%d "
		"frames_attempted=%u started_ns=%llu ended_ns=%llu "
		"battery_before_valid=%d battery_before=0x%x battery_before_ns=%llu "
		"battery_after_valid=%d battery_after=0x%x battery_after_ns=%llu "
		"compatibility_verified=0\n", e->attempted, e->terminal, e->stage, e->error,
		e->frames_attempted, e->started_ns, e->ended_ns,
		e->battery_before_valid, e->battery_before, e->battery_before_ns,
		e->battery_after_valid, e->battery_after, e->battery_after_ns);
	for (unsigned int i = 0; i < ARRAY_SIZE(sm_evidence_commands); i++) {
		struct sm_mac_receipt *r = &e->frames[i];

		n += sysfs_emit_at(buf, n, "frame=%u cmd=0x%04x attempted=%d expected_size=%d "
			"select_attempted=%d select_rc=%d read_attempted=%d read_rc=%d "
			"full_read=%d validate_attempted=%d validate_rc=%d "
			"started_ns=%llu select_end_ns=%llu read_end_ns=%llu ended_ns=%llu raw=",
			i, sm_evidence_commands[i], r->attempted, r->expected_size,
			r->select_attempted, r->select_rc, r->read_attempted, r->read_rc,
			r->full_read, r->validate_attempted, r->validate_rc,
			r->started_ns, r->select_end_ns, r->read_end_ns, r->ended_ns);
		if (r->full_read) n += sysfs_emit_at(buf, n, "%*phN\n", 36, r->raw);
		else n += sysfs_emit_at(buf, n, "unavailable\n");
	}
	mutex_unlock(&p->lock);
	return n;
}
static DEVICE_ATTR(mac_evidence, 0400, mac_evidence_show, NULL);

static int sm_protection_get(struct power_supply *psy,
			     enum power_supply_property property,
			     union power_supply_propval *value)
{
	struct sm_protection *p = power_supply_get_drvdata(psy);
	int ret;

	if (property == POWER_SUPPLY_PROP_MODEL_NAME) {
		value->strval = "samurai-factory-2719-protection-status";
		return 0;
	}
	mutex_lock(&p->lock);
	ret = sm_protection_read(p); /* No cached Good on a failed transfer. */
	if (!ret) {
		if (property == POWER_SUPPLY_PROP_PRESENT) value->intval = 1;
		else if (property == POWER_SUPPLY_PROP_HEALTH) value->intval = POWER_SUPPLY_HEALTH_GOOD;
		else ret = -EINVAL;
	}
	mutex_unlock(&p->lock);
	return ret;
}

static ssize_t protection_state_show(struct device *dev,
	struct device_attribute *attr, char *buf)
{
	struct sm_protection *p = dev_get_drvdata(dev);
	ssize_t length;

	mutex_lock(&p->lock);
	sm_protection_read(p);
	length = sysfs_emit(buf, "id=0x%x safety=0x%x pf=0x%x operation=0x%x "
		"manufacturing=0x%x pf_enabled=%d error=%d\n", p->id, p->safety,
		p->permanent, p->operation, p->manufacturing,
		!!(p->manufacturing & 0x40), p->last_error);
	mutex_unlock(&p->lock);
	return length;
}
static DEVICE_ATTR_RO(protection_state);
static struct attribute *sm_protection_attrs[] = {
	&dev_attr_protection_state.attr, &dev_attr_mac_evidence_capture.attr,
	&dev_attr_mac_evidence.attr, NULL,
};
static const struct attribute_group sm_protection_group = { .attrs = sm_protection_attrs };
static const enum power_supply_property sm_protection_properties[] = {
	POWER_SUPPLY_PROP_PRESENT, POWER_SUPPLY_PROP_HEALTH, POWER_SUPPLY_PROP_MODEL_NAME,
};
static const struct power_supply_desc sm_protection_desc = {
	.name = "samurai-gauge-protection", .type = POWER_SUPPLY_TYPE_UNKNOWN,
	.properties = sm_protection_properties,
	.num_properties = ARRAY_SIZE(sm_protection_properties), .get_property = sm_protection_get,
	.no_thermal = true,
};

static void sm_protection_put(void *data) { put_device(data); }

static int sm_protection_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct device_node *node;
	struct power_supply_config config = { 0 };
	struct power_supply *psy;
	struct sm_protection *p;
	int ret;

	if (!of_machine_is_compatible("realme,samurai") ||
	    IS_ENABLED(CONFIG_BATTERY_BQ27XXX_DT_UPDATES_NVM)) return -ENODEV;
	p = devm_kzalloc(dev, sizeof(*p), GFP_KERNEL);
	if (!p) return -ENOMEM;
	node = dev->of_node ? of_parse_phandle(dev->of_node, "battery-gauge", 0) : NULL;
	if (!node && register_board)
		node = of_find_node_by_path("/soc@0/geniqup@cc0000/i2c@c94000/fuel-gauge@55");
	if (!node) return -EINVAL;
	p->gauge = of_find_i2c_device_by_node(node);
	of_node_put(node);
	if (!p->gauge) return -EPROBE_DEFER;
	ret = devm_add_action_or_reset(dev, sm_protection_put, &p->gauge->dev);
	if (ret) return ret;
	if (p->gauge->addr != 0x55 || !i2c_check_functionality(p->gauge->adapter,
		I2C_FUNC_I2C | I2C_FUNC_SMBUS_WORD_DATA)) return -EOPNOTSUPP;
	/* A device reference protects lifetime, not system-sleep ordering. Fresh
	 * MAC reads must wait for the gauge and its I2C parent to resume first.
	 */
	if (!device_link_add(dev, &p->gauge->dev, DL_FLAG_AUTOREMOVE_CONSUMER))
		return -ENOMEM;
	mutex_init(&p->lock);
	platform_set_drvdata(pdev, p);
	ret = sm_protection_read(p);
	if (ret) return dev_err_probe(dev, ret, "factory gauge protection protocol/state\n");
	config.drv_data = p;
	config.fwnode = dev_fwnode(dev);
	psy = devm_power_supply_register(dev, &sm_protection_desc, &config);
	if (IS_ERR(psy)) return PTR_ERR(psy);
	return devm_device_add_group(dev, &sm_protection_group);
}

static const struct of_device_id sm_protection_match[] = {
	{ .compatible = "realme,samurai-gauge-protection" }, { }
};
MODULE_DEVICE_TABLE(of, sm_protection_match);
static struct platform_driver sm_protection_driver = {
	.probe = sm_protection_probe,
	.driver = { .name = "samurai-gauge-protection", .of_match_table = sm_protection_match },
};
static int __init sm_protection_init(void)
{
	int ret = platform_driver_register(&sm_protection_driver);
	if (ret || !register_board) return ret;
	sm_board = platform_device_register_simple("samurai-gauge-protection", -1, NULL, 0);
	if (IS_ERR(sm_board)) {
		ret = PTR_ERR(sm_board);
		platform_driver_unregister(&sm_protection_driver);
	}
	return ret;
}
static void __exit sm_protection_exit(void)
{
	if (register_board && !IS_ERR_OR_NULL(sm_board)) platform_device_unregister(sm_board);
	platform_driver_unregister(&sm_protection_driver);
}
module_init(sm_protection_init);
module_exit(sm_protection_exit);
MODULE_DESCRIPTION("RMX1931 factory-family gauge protection status, no protection writes");
MODULE_LICENSE("GPL");
