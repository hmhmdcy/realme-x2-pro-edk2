// SPDX-License-Identifier: GPL-2.0-only
/* RMX1931 input observer: no PMIC, charger, USB role or PD writes. */
#include <linux/device.h>
#include <linux/err.h>
#include <linux/module.h>
#include <linux/pm.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/power_supply.h>
#include <linux/property.h>
#include <linux/regmap.h>
#include <linux/slab.h>
#include <linux/workqueue.h>

#include "samurai-usb-input-decode.h"

static bool register_board;
module_param(register_board, bool, 0444);
MODULE_PARM_DESC(register_board, "Create a PM8150B read-only input device using observed board wiring");
static struct platform_device *samurai_usb_board;
static bool native_retained;
module_param(native_retained, bool, 0444);
MODULE_PARM_DESC(native_retained, "Native DWC3 reference requires this provider until next boot");

struct samurai_usb_input {
	struct regmap *map;
	struct power_supply *psy;
	struct mutex lock;
	struct delayed_work work;
	struct samurai_usb_budget last;
	int last_error;
	bool last_valid;
	bool udc_valid;
	bool paused;
	int udc_current_ua;
};

static int samurai_usb_read_status(struct samurai_usb_input *input,
				   struct samurai_usb_status *s)
{
	static const unsigned int registers[] = {
		0x1307, 0x1308, 0x1310, 0x1506, 0x1509, 0x150b, 0x150d,
	};
	unsigned char *fields[] = {
		&s->apsd, &s->result, &s->plugin, &s->cc,
		&s->attached, &s->misc, &s->legacy,
	};
	unsigned int value, i;
	int ret;

	for (i = 0; i < ARRAY_SIZE(registers); i++) {
		ret = regmap_read(input->map, registers[i], &value);
		if (ret)
			return ret;
		*fields[i] = value;
	}
	return 0;
}

static int samurai_usb_get_budget(struct samurai_usb_input *input,
				  struct samurai_usb_budget *budget)
{
	struct samurai_usb_status before, after;
	int ret;

	mutex_lock(&input->lock);
	if (input->paused) {
		input->udc_valid = false;
		mutex_unlock(&input->lock);
		return -ENODATA;
	}
	ret = samurai_usb_read_status(input, &before);
	if (!ret)
		ret = samurai_usb_read_status(input, &after);
	if (!ret && !samurai_usb_status_equal(&before, &after))
		ret = -EAGAIN;
	if (!ret)
		ret = samurai_usb_decode(&after, budget);
	if (ret || !budget->online)
		input->udc_valid = false;
	if (!ret)
		ret = samurai_usb_apply_udc(budget, input->udc_valid, input->udc_current_ua);
	mutex_unlock(&input->lock);
	return ret;
}

static enum power_supply_usb_type samurai_usb_type(enum samurai_usb_kind kind)
{
	switch (kind) {
	case SAMURAI_USB_SDP: return POWER_SUPPLY_USB_TYPE_SDP;
	case SAMURAI_USB_CDP: return POWER_SUPPLY_USB_TYPE_CDP;
	case SAMURAI_USB_DCP: return POWER_SUPPLY_USB_TYPE_DCP;
	case SAMURAI_USB_TYPE_C: return POWER_SUPPLY_USB_TYPE_C;
	default: return POWER_SUPPLY_USB_TYPE_UNKNOWN;
	}
}

static enum power_supply_property samurai_usb_properties[] = {
	POWER_SUPPLY_PROP_ONLINE,
	POWER_SUPPLY_PROP_USB_TYPE,
	POWER_SUPPLY_PROP_CURRENT_MAX,
	POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT,
};

static int samurai_usb_get_property(struct power_supply *psy,
				    enum power_supply_property property,
				    union power_supply_propval *value)
{
	struct samurai_usb_input *input = power_supply_get_drvdata(psy);
	struct samurai_usb_budget budget;
	int ret = samurai_usb_get_budget(input, &budget);

	if (ret)
		return ret == -EAGAIN ? -ENODATA : ret;
	switch (property) {
	case POWER_SUPPLY_PROP_ONLINE:
		value->intval = budget.online;
		return 0;
	case POWER_SUPPLY_PROP_USB_TYPE:
		value->intval = samurai_usb_type(budget.kind);
		return 0;
	case POWER_SUPPLY_PROP_CURRENT_MAX:
		if (budget.current_ua < 0)
			return budget.current_ua;
		value->intval = budget.current_ua;
		return 0;
	case POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT:
		mutex_lock(&input->lock);
		ret = input->udc_valid ? 0 : -ENODATA;
		value->intval = input->udc_current_ua;
		mutex_unlock(&input->lock);
		return ret;
	default:
		return -EINVAL;
	}
}

static int samurai_usb_set_property(struct power_supply *psy,
				    enum power_supply_property property,
				    const union power_supply_propval *value)
{
	struct samurai_usb_input *input = power_supply_get_drvdata(psy);
	int ret = 0;

	if (property != POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT) return -EINVAL;
	mutex_lock(&input->lock);
	input->udc_valid = false;
	if (input->paused) ret = -EBUSY;
	else if (value->intval < 0 || value->intval > 500000) ret = -ERANGE;
	else {
		input->udc_current_ua = value->intval;
		input->udc_valid = true;
	}
	mutex_unlock(&input->lock);
	power_supply_changed(psy);
	return ret;
}

static const struct power_supply_desc samurai_usb_desc = {
	.name = "samurai-usb-input",
	.type = POWER_SUPPLY_TYPE_USB,
	.usb_types = BIT(POWER_SUPPLY_USB_TYPE_UNKNOWN) |
		BIT(POWER_SUPPLY_USB_TYPE_SDP) | BIT(POWER_SUPPLY_USB_TYPE_CDP) |
		BIT(POWER_SUPPLY_USB_TYPE_DCP) | BIT(POWER_SUPPLY_USB_TYPE_C),
	.properties = samurai_usb_properties,
	.num_properties = ARRAY_SIZE(samurai_usb_properties),
	.get_property = samurai_usb_get_property,
	/* No writable sysfs property: the existing DWC3 kernel callback supplies
	 * this software allowance through power_supply_set_property().
	 */
	.set_property = samurai_usb_set_property,
};

static void samurai_usb_poll(struct work_struct *work)
{
	struct samurai_usb_input *input = container_of(to_delayed_work(work),
						      struct samurai_usb_input, work);
	struct samurai_usb_budget budget = { 0 };
	int ret = samurai_usb_get_budget(input, &budget);
	bool changed = !input->last_valid || ret != input->last_error ||
		(!ret && (budget.online != input->last.online ||
			  budget.kind != input->last.kind ||
			  budget.current_ua != input->last.current_ua));

	input->last = budget;
	input->last_error = ret;
	input->last_valid = true;
	if (changed)
		power_supply_changed(input->psy);
	mutex_lock(&input->lock);
	if (!input->paused)
		schedule_delayed_work(&input->work, msecs_to_jiffies(1000));
	mutex_unlock(&input->lock);
}

static void samurai_usb_stop(void *data)
{
	struct samurai_usb_input *input = data;

	mutex_lock(&input->lock);
	input->paused = true;
	input->udc_valid = false;
	mutex_unlock(&input->lock);
	cancel_delayed_work_sync(&input->work);
}

static int samurai_usb_suspend(struct device *dev)
{
	samurai_usb_stop(dev_get_drvdata(dev));
	return 0;
}

static int samurai_usb_resume(struct device *dev)
{
	struct samurai_usb_input *input = dev_get_drvdata(dev);
	mutex_lock(&input->lock);
	input->udc_valid = false;
	input->paused = false;
	mutex_unlock(&input->lock);
	mod_delayed_work(system_wq, &input->work, 0);
	return 0;
}
static DEFINE_SIMPLE_DEV_PM_OPS(samurai_usb_pm_ops, samurai_usb_suspend, samurai_usb_resume);

static void samurai_usb_retain_for_native_consumer(struct device *dev)
{
	struct device_node *node;
	const char *name;

	/* DWC3 owns its supply reference for the controller's lifetime. Current
	 * power_supply_unregister() warns if such a reference remains; unloading
	 * this module would also invalidate its property callbacks. Do not permit
	 * that lifecycle after native wiring has been selected in the boot DT.
	 */
	node = of_find_node_by_path("/soc@0/usb@a6f8800/usb@a600000");
	if (node && !of_property_read_string(node, "usb-psy-name", &name) &&
	    !strcmp(name, "samurai-usb-input") && !native_retained) {
		__module_get(THIS_MODULE);
		native_retained = true;
		dev_info(dev, "native DWC3 supply retained until next boot\n");
	}
	of_node_put(node);
}

static int samurai_usb_probe(struct platform_device *pdev)
{
	struct power_supply_config config = { 0 };
	struct samurai_usb_input *input;
	struct device *dev = &pdev->dev;
	u32 base;
	int ret;

	if (!of_machine_is_compatible("realme,samurai") ||
	    !of_device_is_compatible(dev->parent->of_node, "qcom,pm8150b"))
		return -ENODEV;
	if (!of_node_name_eq(dev->parent->of_node, "pmic") ||
	    of_property_read_u32(dev->parent->of_node, "reg", &base) || base != 2)
		return -ENODEV;
	if (device_property_read_u32(dev, "reg", &base) || base != 0x1300)
		return -EINVAL;
	input = devm_kzalloc(dev, sizeof(*input), GFP_KERNEL);
	if (!input)
		return -ENOMEM;
	input->map = dev_get_regmap(dev->parent, NULL);
	if (!input->map)
		return -ENODEV;
	mutex_init(&input->lock);
	platform_set_drvdata(pdev, input);
	INIT_DELAYED_WORK(&input->work, samurai_usb_poll);
	config.drv_data = input;
	/* A runtime software node already has a link named for its platform
	 * parent. Reusing it for a same-named power_supply creates duplicate
	 * sysfs links and unbalanced software-node removal references.
	 * DT nodes retain the established firmware associations.
	 */
	config.fwnode = dev->of_node ? dev_fwnode(dev) : NULL;
	input->psy = devm_power_supply_register(dev, &samurai_usb_desc, &config);
	if (IS_ERR(input->psy))
		return PTR_ERR(input->psy);
	/* LIFO devres: stop polling before the supply and PMIC map are released. */
	ret = devm_add_action_or_reset(dev, samurai_usb_stop, input);
	if (ret)
		return ret;
	schedule_delayed_work(&input->work, 0);
	samurai_usb_retain_for_native_consumer(dev);
	dev_info(dev, "read-only PM8150B USB input budget registered\n");
	return 0;
}

static const struct of_device_id samurai_usb_match[] = {
	{ .compatible = "realme,rmx1931-usb-input" },
	{ }
};
MODULE_DEVICE_TABLE(of, samurai_usb_match);

static struct platform_driver samurai_usb_driver = {
	.probe = samurai_usb_probe,
	.driver = {
		.name = "samurai-usb-input",
		.of_match_table = samurai_usb_match,
		.pm = pm_sleep_ptr(&samurai_usb_pm_ops),
		.suppress_bind_attrs = true,
	},
};

static int samurai_usb_parent_match(struct device *dev, const void *unused)
{
	u32 sid;
	return dev->parent && dev->parent->of_node &&
		of_device_is_compatible(dev->parent->of_node, "qcom,pm8150b") &&
		!of_property_read_u32(dev->parent->of_node, "reg", &sid) && sid == 2;
}

static int __init samurai_usb_init(void)
{
	static const struct property_entry props[] = {
		PROPERTY_ENTRY_U32("reg", 0x1300), { }
	};
	struct platform_device_info info = { .name = "samurai-usb-input",
		.id = PLATFORM_DEVID_NONE, .properties = props };
	struct device *child;
	int ret = platform_driver_register(&samurai_usb_driver);

	if (ret || !register_board) return ret;
	if (!of_machine_is_compatible("realme,samurai")) { ret = -ENODEV; goto fail; }
	child = bus_find_device(&platform_bus_type, NULL, NULL, samurai_usb_parent_match);
	if (!child) { ret = -ENODEV; goto fail; }
	info.parent = child->parent;
	samurai_usb_board = platform_device_register_full(&info);
	put_device(child);
	if (IS_ERR(samurai_usb_board)) { ret = PTR_ERR(samurai_usb_board); goto fail; }
	return 0;
fail:
	platform_driver_unregister(&samurai_usb_driver);
	return ret;
}

static void __exit samurai_usb_exit(void)
{
	if (register_board && !IS_ERR_OR_NULL(samurai_usb_board))
		platform_device_unregister(samurai_usb_board);
	platform_driver_unregister(&samurai_usb_driver);
}
module_init(samurai_usb_init);
module_exit(samurai_usb_exit);
MODULE_DESCRIPTION("RMX1931 read-only PM8150B USB input budget observer");
MODULE_LICENSE("GPL");
