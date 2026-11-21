// SPDX-License-Identifier: GPL-2.0-only
/*
 * Read-only PM8150B Type-C/APSD register probe for comparing the known-good
 * #506 boot with charging integration candidates. It never writes regmap state.
 */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/regmap.h>

#define TYPEC_NODE "/soc@0/spmi@c440000/pmic@2/typec@1500"

static const unsigned int apsd_regs[] = {
	0x1307, 0x1308, 0x1310, 0x1358, 0x1362,
	0x1506, 0x1509, 0x150a, 0x150b, 0x150d,
};

static int __init apsd_regprobe_init(void)
{
	struct platform_device *pdev;
	struct device_node *node;
	struct regmap *map;
	unsigned int value;
	int ret;
	int i;

	node = of_find_node_by_path(TYPEC_NODE);
	if (!node) {
		pr_err("apsd-regprobe: device node missing\n");
		return -ENODEV;
	}

	pdev = of_find_device_by_node(node);
	of_node_put(node);
	if (!pdev) {
		pr_err("apsd-regprobe: platform device missing\n");
		return -ENODEV;
	}

	map = dev_get_regmap(pdev->dev.parent, NULL);
	pr_info("apsd-regprobe: device=%s parent=%s map=%px driver=%s\n",
		dev_name(&pdev->dev),
		pdev->dev.parent ? dev_name(pdev->dev.parent) : "<none>",
		map, pdev->dev.driver ? pdev->dev.driver->name : "<unbound>");
	if (!map) {
		platform_device_put(pdev);
		return -ENODEV;
	}

	for (i = 0; i < ARRAY_SIZE(apsd_regs); i++) {
		value = 0;
		ret = regmap_read(map, apsd_regs[i], &value);
		pr_info("apsd-regprobe: reg[0x%04x]=0x%08x ret=%d\n",
			apsd_regs[i], value, ret);
	}

	platform_device_put(pdev);
	return 0;
}

static void __exit apsd_regprobe_exit(void)
{
	pr_info("apsd-regprobe: unloaded\n");
}

module_init(apsd_regprobe_init);
module_exit(apsd_regprobe_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Read-only PM8150B APSD register probe");
