// SPDX-License-Identifier: GPL-2.0-only
/* RMX1931 input observer: no PMIC, charger, USB role or PD writes. */
#include <linux/device.h>
#include <linux/err.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/power_supply.h>
#include <linux/property.h>
#include <linux/regmap.h>
#include <linux/slab.h>
#include <linux/workqueue.h>

#include "samurai-usb-input-decode.h"

struct samurai_usb_input {
	struct regmap *map;
	struct power_supply *psy;
	struct mutex lock;
	struct delayed_work work;
	struct samurai_usb_budget last;
	int last_error;
	bool last_valid;
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
	ret = samurai_usb_read_status(input, &before);
	if (!ret)
		ret = samurai_usb_read_status(input, &after);
	if (!ret && !samurai_usb_status_equal(&before, &after))
		ret = -EAGAIN;
	if (!ret)
		ret = samurai_usb_decode(&after, budget);
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
	default:
		return -EINVAL;
	}
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
	schedule_delayed_work(&input->work, msecs_to_jiffies(1000));
}

static void samurai_usb_stop(void *data)
{
	struct samurai_usb_input *input = data;

	cancel_delayed_work_sync(&input->work);
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
	if (of_property_read_u32(dev->of_node, "reg", &base) || base != 0x1300)
		return -EINVAL;
	input = devm_kzalloc(dev, sizeof(*input), GFP_KERNEL);
	if (!input)
		return -ENOMEM;
	input->map = dev_get_regmap(dev->parent, NULL);
	if (!input->map)
		return -ENODEV;
	mutex_init(&input->lock);
	INIT_DELAYED_WORK(&input->work, samurai_usb_poll);
	config.drv_data = input;
	config.fwnode = dev_fwnode(dev);
	input->psy = devm_power_supply_register(dev, &samurai_usb_desc, &config);
	if (IS_ERR(input->psy))
		return PTR_ERR(input->psy);
	/* LIFO devres: stop polling before the supply and PMIC map are released. */
	ret = devm_add_action_or_reset(dev, samurai_usb_stop, input);
	if (ret)
		return ret;
	schedule_delayed_work(&input->work, 0);
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
	},
};

module_platform_driver(samurai_usb_driver);
MODULE_DESCRIPTION("RMX1931 read-only PM8150B USB input budget observer");
MODULE_LICENSE("GPL");
