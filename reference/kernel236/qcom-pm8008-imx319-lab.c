// SPDX-License-Identifier: GPL-2.0-only
/* RMX1931 experimental P outputs L1/L4 only; Q uses its original driver. */
#include <linux/delay.h>
#include <linux/i2c.h>
#include <linux/mfd/qcom-pm8008-imx319-lab.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/regmap.h>
#include <linux/regulator/driver.h>
#include <linux/string.h>
#include <linux/unaligned.h>

#define PM8008_GLOBAL_ENABLE 0x0950
#define PM8008_GLOBAL_BIT BIT(0)
#define PM8008_LDO_BASE(n) (0x4000 + (n) * 0x100)
#define PM8008_LDO_READY 0x08
#define PM8008_LDO_STEP 0x3b
#define PM8008_LDO_VSET 0x40
#define PM8008_LDO_ENABLE 0x46
#define PM8008_LDO_BIT BIT(7)

struct pm8008_lab_rail {
	struct pm8008_imx319_lab_state *state;
	struct regulator_desc desc;
	unsigned int index;
	int target_uV;
	unsigned int step_rate;
};

static const struct linear_range pm8008_lab_nldo[] = {
	REGULATOR_LINEAR_RANGE(528000, 0, 122, 8000),
};
static const struct linear_range pm8008_lab_pldo[] = {
	REGULATOR_LINEAR_RANGE(1504000, 0, 237, 8000),
};

static int pm8008_lab_valid(struct pm8008_lab_rail *rail)
{
	struct pm8008_imx319_lab_state *s = rail->state;

	if (!s || s->magic != PM8008_IMX319_LAB_MAGIC ||
	    s->mask != PM8008_IMX319_LAB_MASK ||
	    (rail->index != 0 && rail->index != 3) ||
	    rail->target_uV != (rail->index == 0 ? 1104000 : 2800000))
		return -EINVAL;
	return 0;
}

/* Whole-chip ENABLE audit is the only read of the five excluded outputs. */
static int pm8008_lab_enable_mask(struct pm8008_imx319_lab_state *s,
				  unsigned long *mask)
{
	unsigned int value;
	int ret, i;

	*mask = 0;
	for (i = 0; i < 7; i++) {
		ret = regmap_read(s->secondary,
				  PM8008_LDO_BASE(i) + PM8008_LDO_ENABLE, &value);
		if (ret) {
			s->fault = true;
			return ret;
		}
		if (value & PM8008_LDO_BIT)
			*mask |= BIT(i);
	}
	return 0;
}

static int pm8008_lab_voltage_raw(struct pm8008_lab_rail *rail)
{
	struct pm8008_imx319_lab_state *s = rail->state;
	u8 data[2];
	int ret;

	if (s->reset_held)
		return -EIO;
	ret = regmap_bulk_read(s->secondary,
			       PM8008_LDO_BASE(rail->index) + PM8008_LDO_VSET,
			       data, sizeof(data));
	if (ret) {
		s->fault = true;
		return ret;
	}
	return get_unaligned_le16(data) * 1000;
}

/* Caller holds the parent lock. Preserve uncertainty until a real OFF read. */
static int pm8008_lab_clear(struct pm8008_imx319_lab_state *s, unsigned int index)
{
	unsigned int value;
	int ret, read_ret;

	if (s->reset_held) {
		s->attempted_mask &= ~BIT(index);
		s->enabled_mask &= ~BIT(index);
		return 0;
	}
	ret = regmap_update_bits(s->secondary,
				 PM8008_LDO_BASE(index) + PM8008_LDO_ENABLE,
				 PM8008_LDO_BIT, 0);
	read_ret = regmap_read(s->secondary,
			       PM8008_LDO_BASE(index) + PM8008_LDO_ENABLE, &value);
	if (!read_ret && !(value & PM8008_LDO_BIT)) {
		s->attempted_mask &= ~BIT(index);
		s->enabled_mask &= ~BIT(index);
	} else if (!read_ret) {
		read_ret = -EIO;
	}
	if (ret || read_ret)
		s->fault = true;
	return ret ? ret : read_ret;
}

static int pm8008_lab_global_read(struct pm8008_imx319_lab_state *s,
				 unsigned int *value)
{
	int ret;

	ret = regmap_read(s->primary, PM8008_GLOBAL_ENABLE, value);
	if (!ret && (*value & ~PM8008_GLOBAL_BIT))
		ret = -EINVAL;
	if (ret)
		s->fault = true;
	return ret;
}

static int pm8008_lab_restore_global(struct pm8008_imx319_lab_state *s)
{
	unsigned long mask;
	unsigned int value;
	int ret, read_ret;

	/* Isolation by reset is not restoration of the original register state. */
	if (s->reset_held)
		return 0;
	ret = pm8008_lab_enable_mask(s, &mask);
	if (ret)
		return ret;
	if ((mask & ~s->mask) || mask != s->enabled_mask ||
	    s->attempted_mask != s->enabled_mask) {
		s->fault = true;
		return -EBUSY;
	}
	if (!s->global_attempted || s->global_original || mask)
		return 0;
	ret = pm8008_lab_global_read(s, &value);
	if (ret)
		return ret;
	ret = regmap_update_bits(s->primary, PM8008_GLOBAL_ENABLE, PM8008_GLOBAL_BIT, 0);
	read_ret = pm8008_lab_global_read(s, &value);
	if (!read_ret && !(value & PM8008_GLOBAL_BIT))
		s->global_attempted = false;
	else if (!read_ret)
		read_ret = -EIO;
	if (ret || read_ret)
		s->fault = true;
	return ret ? ret : read_ret;
}

/* Called only after OFF/global recovery failed; no pulse, release or Q action. */
static int pm8008_lab_isolate(struct pm8008_imx319_lab_state *s)
{
	int ret;

	s->fault = true;
	s->ready = false;
	if (s->reset_held)
		return 0;
	if (s->reset_attempted)
		return s->reset_error ? s->reset_error : -EIO;
	if (!s->assert_p_reset || !s->reset_cookie)
		return -EINVAL;
	s->reset_attempted = true;
	ret = s->assert_p_reset(s->reset_cookie);
	s->reset_error = ret;
	if (!ret) {
		s->reset_held = true;
		s->attempted_mask = 0;
		s->enabled_mask = 0;
	}
	return ret;
}

static int pm8008_lab_get_voltage(struct regulator_dev *rdev)
{
	struct pm8008_lab_rail *rail = rdev_get_drvdata(rdev);
	int ret = pm8008_lab_valid(rail);

	if (ret)
		return ret;
	mutex_lock(&rail->state->lock);
	ret = pm8008_lab_voltage_raw(rail);
	mutex_unlock(&rail->state->lock);
	return ret;
}

static int pm8008_lab_set_voltage_sel(struct regulator_dev *rdev, unsigned int sel)
{
	struct pm8008_lab_rail *rail = rdev_get_drvdata(rdev);
	struct pm8008_imx319_lab_state *s = rail->state;
	unsigned int value;
	u8 data[2];
	int ret = pm8008_lab_valid(rail);

	if (ret)
		return ret;
	ret = regulator_list_voltage_linear_range(rdev, sel);
	if (ret < 0 || ret != rail->target_uV)
		return -EINVAL;
	mutex_lock(&s->lock);
	if (s->fault || s->removing) {
		ret = -EIO;
		goto out;
	}
	ret = regmap_read(s->secondary,
			  PM8008_LDO_BASE(rail->index) + PM8008_LDO_ENABLE, &value);
	if (ret)
		goto fault;
	if (value & PM8008_LDO_BIT) {
		ret = -EBUSY;
		goto fault;
	}
	put_unaligned_le16(rail->target_uV / 1000, data);
	ret = regmap_bulk_write(s->secondary,
				PM8008_LDO_BASE(rail->index) + PM8008_LDO_VSET,
				data, sizeof(data));
	if (ret)
		goto fault;
	ret = pm8008_lab_voltage_raw(rail);
	if (ret < 0)
		goto fault;
	if (ret != rail->target_uV) {
		ret = -EIO;
		goto fault;
	}
	ret = 0;
	goto out;
fault:
	s->fault = true;
out:
	mutex_unlock(&s->lock);
	return ret;
}

static int pm8008_lab_is_enabled(struct regulator_dev *rdev)
{
	struct pm8008_lab_rail *rail = rdev_get_drvdata(rdev);
	struct pm8008_imx319_lab_state *s = rail->state;
	unsigned int value;
	int ret = pm8008_lab_valid(rail);

	if (ret)
		return ret;
	mutex_lock(&s->lock);
	if (s->fault) {
		ret = -EIO;
		goto out;
	}
	ret = regmap_read(s->secondary,
			  PM8008_LDO_BASE(rail->index) + PM8008_LDO_ENABLE, &value);
	if (ret)
		s->fault = true;
	else
		ret = !!(value & PM8008_LDO_BIT);
out:
	mutex_unlock(&s->lock);
	return ret;
}

static int pm8008_lab_enable(struct regulator_dev *rdev)
{
	struct pm8008_lab_rail *rail = rdev_get_drvdata(rdev);
	struct pm8008_imx319_lab_state *s = rail->state;
	unsigned long mask;
	unsigned int value, delay_us;
	int ret = pm8008_lab_valid(rail), cleanup_ret, i;

	if (ret)
		return ret;
	mutex_lock(&s->lock);
	if (s->fault || s->removing || !s->ready) {
		ret = s->fault || s->removing ? -EIO : -EAGAIN;
		goto out;
	}
	ret = pm8008_lab_enable_mask(s, &mask);
	if (ret)
		goto out;
	if ((mask & ~s->mask) || mask != s->enabled_mask ||
	    s->attempted_mask != s->enabled_mask || (mask & BIT(rail->index))) {
		ret = -EBUSY;
		goto fault;
	}
	ret = pm8008_lab_voltage_raw(rail);
	if (ret < 0)
		goto out;
	if (ret != rail->target_uV) {
		ret = -EINVAL;
		goto fault;
	}
	ret = pm8008_lab_global_read(s, &value);
	if (ret)
		goto fault;
	if (!(value & PM8008_GLOBAL_BIT)) {
		if (mask) {
			ret = -EBUSY;
			goto fault;
		}
		s->global_attempted = true;
		ret = regmap_update_bits(s->primary, PM8008_GLOBAL_ENABLE,
					 PM8008_GLOBAL_BIT, PM8008_GLOBAL_BIT);
		if (ret)
			goto rollback_global;
		ret = pm8008_lab_global_read(s, &value);
		if (ret || !(value & PM8008_GLOBAL_BIT)) {
			if (!ret)
				ret = -EIO;
			goto rollback_global;
		}
	}
	s->attempted_mask |= BIT(rail->index);
	ret = regmap_update_bits(s->secondary,
				 PM8008_LDO_BASE(rail->index) + PM8008_LDO_ENABLE,
				 PM8008_LDO_BIT, PM8008_LDO_BIT);
	if (ret)
		goto rollback;
	delay_us = 20 + DIV_ROUND_UP(rail->target_uV, rail->step_rate);
	for (i = 0; i < 10; i++) {
		usleep_range(delay_us, delay_us + 100);
		ret = regmap_read(s->secondary,
				  PM8008_LDO_BASE(rail->index) + PM8008_LDO_READY,
				  &value);
		if (ret)
			goto rollback;
		if (value & PM8008_LDO_BIT) {
			s->enabled_mask |= BIT(rail->index);
			ret = 0;
			goto out;
		}
	}
	ret = -ETIME;
rollback:
	s->fault = true;
	cleanup_ret = pm8008_lab_clear(s, rail->index);
	if (cleanup_ret) {
		dev_err(s->parent, "lab output OFF not verified: %d\n", cleanup_ret);
		pm8008_lab_isolate(s);
	}
rollback_global:
	s->fault = true;
	cleanup_ret = pm8008_lab_restore_global(s);
	if (cleanup_ret) {
		dev_err(s->parent, "lab global restore failed: %d\n", cleanup_ret);
		pm8008_lab_isolate(s);
	}
	goto out;
fault:
	s->fault = true;
out:
	mutex_unlock(&s->lock);
	return ret;
}

static int pm8008_lab_disable(struct regulator_dev *rdev)
{
	struct pm8008_lab_rail *rail = rdev_get_drvdata(rdev);
	struct pm8008_imx319_lab_state *s = rail->state;
	int ret = pm8008_lab_valid(rail), global_ret;

	if (ret)
		return ret;
	mutex_lock(&s->lock);
	ret = pm8008_lab_clear(s, rail->index);
	global_ret = pm8008_lab_restore_global(s);
	if ((ret || global_ret) && !pm8008_lab_isolate(s)) {
		/* Known reset assertion provides OFF for balancing this reference. */
		ret = 0;
		global_ret = 0;
	}
	mutex_unlock(&s->lock);
	return ret ? ret : global_ret;
}

static const struct regulator_ops pm8008_lab_ops = {
	.list_voltage = regulator_list_voltage_linear_range,
	.map_voltage = regulator_map_voltage_linear_range,
	.get_voltage = pm8008_lab_get_voltage,
	.set_voltage_sel = pm8008_lab_set_voltage_sel,
	.is_enabled = pm8008_lab_is_enabled,
	.enable = pm8008_lab_enable,
	.disable = pm8008_lab_disable,
};

static void pm8008_lab_cleanup(void *data)
{
	struct pm8008_imx319_lab_state *s = data;
	int ret, first = 0, i;

	mutex_lock(&s->lock);
	s->ready = false;
	s->removing = true;
	for (i = 0; i < 7; i++) {
		if (!(s->mask & BIT(i)))
			continue;
		ret = pm8008_lab_clear(s, i);
		if (ret && !first)
			first = ret;
	}
	ret = pm8008_lab_restore_global(s);
	if (ret && !first)
		first = ret;
	if (first && !pm8008_lab_isolate(s))
		first = 0;
	s->claimed = false;
	if (first)
		dev_err(s->parent, "lab cleanup incomplete; P reset required: %d\n", first);
	mutex_unlock(&s->lock);
}

/* Reject extra outputs and all undeclared input supply/control assumptions. */
static int pm8008_lab_validate_dt(struct device *parent)
{
	struct device_node *regs, *node;
	struct property *property;
	unsigned long mask = 0;
	u32 low, high;
	int ret = -EINVAL;

	if (!parent->of_node || !of_device_is_compatible(parent->of_node, "qcom,pm8008") ||
	    !of_property_read_bool(parent->of_node, "realme,imx319-power-lab"))
		return -EINVAL;
	for_each_property_of_node(parent->of_node, property)
		if (strstr(property->name, "-supply"))
			return -EINVAL;
	regs = of_get_child_by_name(parent->of_node, "regulators");
	if (!regs)
		return -EINVAL;
	for_each_child_of_node(regs, node) {
		unsigned int index, target;

		if (!of_device_is_available(node))
			goto put_child;
		if (of_node_name_eq(node, "ldo1")) {
			index = 0;
			target = 1104000;
		} else if (of_node_name_eq(node, "ldo4")) {
			index = 3;
			target = 2800000;
		} else {
			goto put_child;
		}
		if (mask & BIT(index))
			goto put_child;
		for_each_property_of_node(node, property) {
			const char *name = property->name;

			/* OF unflatten adds this standard metadata to every LDO. */
			if (!strcmp(name, "name")) {
				const char *expected = index == 0 ? "ldo1" : "ldo4";

				if (property->length != 5 || !property->value ||
				    memcmp(property->value, expected, 5))
					goto put_child;
				continue;
			}
			if (strcmp(name, "regulator-name") && strcmp(name, "regulator-min-microvolt") &&
			    strcmp(name, "regulator-max-microvolt") && strcmp(name, "phandle") &&
			    strcmp(name, "linux,phandle"))
				goto put_child;
		}
		if (of_property_read_u32(node, "regulator-min-microvolt", &low) ||
		    of_property_read_u32(node, "regulator-max-microvolt", &high) ||
		    high != target || low != (index == 0 ? 1100000 : target))
			goto put_child;
		mask |= BIT(index);
	}
	ret = mask == PM8008_IMX319_LAB_MASK ? 0 : -EINVAL;
	goto put_regs;
put_child:
	of_node_put(node);
put_regs:
	of_node_put(regs);
	return ret;
}

static int pm8008_lab_probe(struct platform_device *pdev)
{
	const struct platform_device_id *id = platform_get_device_id(pdev);
	const struct pm8008_imx319_lab_data *pdata = dev_get_platdata(&pdev->dev);
	struct pm8008_imx319_lab_state *s;
	struct i2c_client *client;
	struct regulator_config config = {};
	struct pm8008_lab_rail *rail;
	struct regulator_dev *rdev;
	unsigned long mask;
	unsigned int value;
	int ret, i;

	if (!id || id->driver_data != PM8008_IMX319_LAB_MASK || !pdata || !pdata->state)
		return -EINVAL;
	s = pdata->state;
	client = i2c_verify_client(pdev->dev.parent);
	if (!client || client->addr != 8 || (client->flags & I2C_CLIENT_TEN) ||
	    !client->dev.driver || strcmp(client->dev.driver->name, "pm8008") ||
	    s->magic != PM8008_IMX319_LAB_MAGIC || s->parent != &client->dev ||
	    s->mask != PM8008_IMX319_LAB_MASK ||
	    !s->assert_p_reset || !s->reset_cookie ||
	    !s->primary || !s->secondary || s->primary == s->secondary ||
	    dev_get_regmap(s->parent, "primary") != s->primary ||
	    dev_get_regmap(s->parent, "secondary") != s->secondary ||
	    regmap_get_device(s->primary) != s->parent ||
	    regmap_get_device(s->secondary) != s->parent)
		return -EINVAL;
	ret = pm8008_lab_validate_dt(s->parent);
	if (ret)
		return ret;
	mutex_lock(&s->lock);
	if (s->claimed || s->fault) {
		ret = s->fault ? -EIO : -EBUSY;
		goto unlock;
	}
	ret = pm8008_lab_enable_mask(s, &mask);
	if (ret)
		goto unlock;
	if (mask || s->attempted_mask || s->enabled_mask) {
		s->fault = true;
		ret = -EBUSY;
		goto unlock;
	}
	ret = pm8008_lab_global_read(s, &value);
	if (ret) {
		s->fault = true;
		goto unlock;
	}
	if (!s->global_initialized) {
		s->global_original = !!(value & PM8008_GLOBAL_BIT);
		s->global_initialized = true;
	}
	s->claimed = true;
	s->ready = false;
	s->removing = false;
unlock:
	mutex_unlock(&s->lock);
	if (ret)
		return ret;
	/* Installed before any registration/constraint VSET write. */
	ret = devm_add_action_or_reset(&pdev->dev, pm8008_lab_cleanup, s);
	if (ret)
		return ret;
	platform_set_drvdata(pdev, s);
	for (i = 0; i < 7; i++) {
		if (!(id->driver_data & BIT(i)))
			continue;
		rail = devm_kzalloc(&pdev->dev, sizeof(*rail), GFP_KERNEL);
		if (!rail)
			return -ENOMEM;
		rail->state = s;
		rail->index = i;
		rail->target_uV = i == 0 ? 1104000 : 2800000;
		rail->desc.name = i == 0 ? "ldo1" : "ldo4";
		rail->desc.of_match = rail->desc.name;
		rail->desc.regulators_node = "regulators";
		rail->desc.ops = &pm8008_lab_ops;
		rail->desc.type = REGULATOR_VOLTAGE;
		rail->desc.owner = THIS_MODULE;
		rail->desc.linear_ranges = i == 0 ? pm8008_lab_nldo : pm8008_lab_pldo;
		rail->desc.n_linear_ranges = 1;
		rail->desc.n_voltages = linear_range_values_in_range(rail->desc.linear_ranges);
		rail->desc.min_uV = rail->desc.linear_ranges->min;
		rail->desc.uV_step = rail->desc.linear_ranges->step;
		mutex_lock(&s->lock);
		ret = regmap_read(s->secondary, PM8008_LDO_BASE(i) + PM8008_LDO_STEP, &value);
		if (ret)
			s->fault = true;
		mutex_unlock(&s->lock);
		if (ret)
			return ret;
		rail->step_rate = 38400 >> (value & 3);
		rail->desc.ramp_delay = rail->step_rate;
		config.dev = s->parent;
		config.driver_data = rail;
		config.regmap = s->secondary;
		/* No fake VIN supplier: physical input ownership is unresolved. */
		rdev = devm_regulator_register(&pdev->dev, &rail->desc, &config);
		if (IS_ERR(rdev))
			return dev_err_probe(&pdev->dev, PTR_ERR(rdev), "lab regulator registration failed\n");
	}
	mutex_lock(&s->lock);
	ret = s->fault ? -EIO : 0;
	if (!ret)
		s->ready = true;
	mutex_unlock(&s->lock);
	return ret;
}

static void pm8008_lab_remove(struct platform_device *pdev)
{
	struct pm8008_imx319_lab_state *s = platform_get_drvdata(pdev);

	mutex_lock(&s->lock);
	s->ready = false;
	s->removing = true;
	mutex_unlock(&s->lock);
	/* devres unregisters both rdevs before the earlier cleanup action. */
}

static const struct platform_device_id pm8008_lab_ids[] = {
	{ "pm8008-reg-lab14", PM8008_IMX319_LAB_MASK },
	{ }
};
MODULE_DEVICE_TABLE(platform, pm8008_lab_ids);

static struct platform_driver pm8008_lab_driver = {
	.driver.name = "pm8008-imx319-lab",
	.probe = pm8008_lab_probe,
	.remove = pm8008_lab_remove,
	.id_table = pm8008_lab_ids,
};
module_platform_driver(pm8008_lab_driver);
MODULE_DESCRIPTION("RMX1931 experimental isolated PM8008 P L1/L4 regulators");
MODULE_LICENSE("GPL");
