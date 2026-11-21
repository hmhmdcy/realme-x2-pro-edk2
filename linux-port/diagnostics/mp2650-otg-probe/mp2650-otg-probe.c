// SPDX-License-Identifier: GPL-2.0-only
/*
 * Temporary RMX1931 MP2650 OTG probe.
 *
 * This module is deliberately narrow: it drives PM8150 GPIO4 high and
 * flips MP2650 REG08.OTG_EN.  It does not touch charger current, voltage,
 * BATTFET, timers, watchdogs or fault configuration.  Unloading the module
 * clears OTG_EN and releases GPIO4.
 */
#include <linux/device.h>
#include <linux/gpio.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/string.h>

#define MP2650_REG_CHG_CFG0	0x08
#define MP2650_OTG_EN		BIT(5)
#define PM8150_GPIO4		515

static bool enable = true;
module_param(enable, bool, 0444);
MODULE_PARM_DESC(enable, "Enable MP2650 OTG during module load");

static struct i2c_client *mp2650_client;
static bool gpio_held;
static int saved_reg08;
static bool reg08_saved;

static int mp2650_match(struct device *dev, const void *data)
{
	return !strcmp(dev_name(dev), data);
}

static int mp2650_set_otg(bool on)
{
	int old, value, ret, after;

	if (!reg08_saved) {
		old = i2c_smbus_read_byte_data(mp2650_client,
					       MP2650_REG_CHG_CFG0);
		if (old < 0)
			return old;
		saved_reg08 = old;
		reg08_saved = true;
	} else {
		old = i2c_smbus_read_byte_data(mp2650_client,
					       MP2650_REG_CHG_CFG0);
		if (old < 0)
			return old;
	}

	/*
	 * The stock 2S configuration drives OTG through the MPS path.  Test
	 * whether the charger also requires CHG_EN to be released while
	 * OTG_EN is asserted; restore the saved byte on unload.
	 */
	value = on ? ((old & ~BIT(4)) | MP2650_OTG_EN) : saved_reg08;
	ret = i2c_smbus_write_byte_data(mp2650_client,
					MP2650_REG_CHG_CFG0, value);
	if (ret < 0)
		return ret;

	after = i2c_smbus_read_byte_data(mp2650_client, MP2650_REG_CHG_CFG0);
	if (after < 0)
		return after;

	pr_info("mp2650-otg-probe: REG08 %02x -> %02x (OTG=%d)\n",
		old, after, on);
	return after == value ? 0 : -EIO;
}

static int __init mp2650_otg_probe_init(void)
{
	struct device *dev;
	int ret;

	dev = bus_find_device(&i2c_bus_type, NULL, "0-005c", mp2650_match);
	if (!dev)
		return -ENODEV;

	mp2650_client = i2c_verify_client(dev);
	if (!mp2650_client)
		return -ENODEV;

	if (!enable) {
		ret = mp2650_set_otg(false);
		if (ret)
			pr_err("mp2650-otg-probe: clear failed: %d\n", ret);
		return ret;
	}

	ret = gpio_request_one(PM8150_GPIO4, GPIOF_OUT_INIT_HIGH,
			       "mp2650-otg-probe");
	if (ret) {
		pr_err("mp2650-otg-probe: GPIO4 request failed: %d\n", ret);
		return ret;
	}
	gpio_held = true;

	ret = mp2650_set_otg(true);
	if (ret) {
		pr_err("mp2650-otg-probe: OTG_EN set failed: %d\n", ret);
		gpio_set_value(PM8150_GPIO4, 0);
		gpio_free(PM8150_GPIO4);
		gpio_held = false;
		return ret;
	}

	pr_info("mp2650-otg-probe: GPIO4 high, REG08.OTG_EN=1\n");
	return 0;
}

static void __exit mp2650_otg_probe_exit(void)
{
	int ret;

	if (!mp2650_client) {
		return;
	}

	ret = mp2650_set_otg(false);
	if (ret)
		pr_err("mp2650-otg-probe: OTG_EN clear failed: %d\n", ret);

	if (gpio_held) {
		gpio_set_value(PM8150_GPIO4, 0);
		gpio_free(PM8150_GPIO4);
	}
	put_device(&mp2650_client->dev);
	pr_info("mp2650-otg-probe: unloaded\n");
}

module_init(mp2650_otg_probe_init);
module_exit(mp2650_otg_probe_exit);

MODULE_DESCRIPTION("RMX1931 MP2650 OTG enable probe");
MODULE_LICENSE("GPL");
