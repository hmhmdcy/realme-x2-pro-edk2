// SPDX-License-Identifier: GPL-2.0
/*
 * Diagnostic Type-C wake-boundary probe.
 *
 * This creates a device-link supplier that is suspended after the PM8150B
 * Type-C device.  Its suspend_late callback disables the Type-C state
 * machine after the Type-C driver has armed its wake IRQs, but before
 * machine_suspend.  The resulting PMIC CC event can then cross the real
 * PDC wake path; the RTC remains the safety wake.  This is not a cable
 * emulator and must never be shipped.
 */

#include <linux/device.h>
#include <linux/err.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/pm.h>
#include <linux/regmap.h>

#define TYPEC_MODE_CFG_REG	0x44
#define TYPEC_DISABLE_CMD	0x01
#define EN_SNK_ONLY		0x02

static char *typec_name = "c440000.spmi:pmic@2:typec@1500";
module_param(typec_name, charp, 0444);

static bool armed;
module_param(armed, bool, 0600);
MODULE_PARM_DESC(armed, "disable Type-C from suspend_late once");

static struct platform_driver near_driver;
static struct platform_device *near_pdev;
static struct device *typec_dev;
static struct device_link *typec_link;
static struct regmap *typec_regmap;
static unsigned int typec_base;
static unsigned int original_mode;
static bool active;

static int near_suspend_late(struct device *dev)
{
	int ret;

	if (!armed)
		return 0;

	ret = regmap_read(typec_regmap, typec_base + TYPEC_MODE_CFG_REG,
			  &original_mode);
	if (ret) {
		pr_err("typec_wake_near: mode read failed: %d\n", ret);
		return 0;
	}

	pr_info("typec_wake_near: suspend_late original=0x%02x\n",
		original_mode);
	ret = regmap_write(typec_regmap, typec_base + TYPEC_MODE_CFG_REG,
			   TYPEC_DISABLE_CMD);
	if (ret) {
		pr_err("typec_wake_near: disable write failed: %d\n", ret);
		return 0;
	}
	active = true;
	pr_info("typec_wake_near: Type-C disabled at wake boundary\n");
	return 0;
}

static int near_resume(struct device *dev)
{
	int ret;

	if (!active)
		return 0;

	ret = regmap_write(typec_regmap, typec_base + TYPEC_MODE_CFG_REG,
			   original_mode);
	if (ret)
		pr_err("typec_wake_near: restore write failed: %d\n", ret);
	else
		pr_info("typec_wake_near: restored mode=0x%02x\n",
			original_mode);
	active = false;
	return 0;
}

static const struct dev_pm_ops near_pm_ops = {
	.suspend_late = near_suspend_late,
	.resume = near_resume,
};

static int near_probe(struct platform_device *pdev)
{
	pr_info("typec_wake_near: dummy PM device probed\n");
	return 0;
}

static void near_remove(struct platform_device *pdev)
{
}

static struct platform_driver near_driver = {
	.probe = near_probe,
	.remove = near_remove,
	.driver = {
		.name = "typec-wake-near",
		.pm = &near_pm_ops,
	},
};

static int __init typec_wake_near_init(void)
{
	int ret;

	typec_dev = bus_find_device_by_name(&platform_bus_type, NULL,
					    typec_name);
	if (!typec_dev)
		return -ENODEV;
	typec_regmap = dev_get_regmap(typec_dev->parent, NULL);
	if (!typec_regmap) {
		put_device(typec_dev);
		typec_dev = NULL;
		return -ENODEV;
	}
	if (of_property_read_u32(typec_dev->of_node, "reg", &typec_base))
		typec_base = 0x1500;

	ret = platform_driver_register(&near_driver);
	if (ret)
		goto err_typec;
	near_pdev = platform_device_register_simple("typec-wake-near", -1,
						    NULL, 0);
	if (IS_ERR(near_pdev)) {
		ret = PTR_ERR(near_pdev);
		near_pdev = NULL;
		platform_driver_unregister(&near_driver);
		goto err_typec;
	}

	/* The Type-C device is the consumer; this dummy device is its supplier,
	 * so the dummy's suspend_late runs after Type-C's suspend callback.
	 */
	typec_link = device_link_add(typec_dev, &near_pdev->dev,
				     DL_FLAG_STATELESS);
	if (IS_ERR(typec_link)) {
		ret = PTR_ERR(typec_link);
		typec_link = NULL;
		platform_device_unregister(near_pdev);
		near_pdev = NULL;
		platform_driver_unregister(&near_driver);
		goto err_typec;
	}

	pr_info("typec_wake_near: linked %s after Type-C root\n",
		dev_name(&near_pdev->dev));
	return 0;

err_typec:
	put_device(typec_dev);
	typec_dev = NULL;
	return ret;
}

static void __exit typec_wake_near_exit(void)
{
	if (active) {
		regmap_write(typec_regmap, typec_base + TYPEC_MODE_CFG_REG,
			     original_mode);
		active = false;
	}
	if (typec_link)
		device_link_del(typec_link);
	if (near_pdev)
		platform_device_unregister(near_pdev);
	platform_driver_unregister(&near_driver);
	if (typec_dev)
		put_device(typec_dev);
}

module_init(typec_wake_near_init);
module_exit(typec_wake_near_exit);

MODULE_DESCRIPTION("Diagnostic PM8150B Type-C wake-boundary probe");
MODULE_AUTHOR("Codex");
MODULE_LICENSE("GPL");
