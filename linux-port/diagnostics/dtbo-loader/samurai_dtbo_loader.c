// SPDX-License-Identifier: GPL-2.0
/*
 * Load a self-contained DT overlay at runtime for RMX1931 diagnostics.
 *
 * The production kernel has CONFIG_OF_OVERLAY but not CONFIG_OF_CONFIGFS.
 * This module provides the missing diagnostic loader without changing the
 * kernel or persistent device tree.
 */

#include <linux/firmware.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/spmi.h>

static char *dtbo_name = "typec-sink.dtbo";
module_param(dtbo_name, charp, 0444);
MODULE_PARM_DESC(dtbo_name, "firmware-relative path of the DT overlay");

static char *platform_driver = "qcom-pmic-typec-alt";
module_param(platform_driver, charp, 0444);
MODULE_PARM_DESC(platform_driver,
		 "optional platform driver name to force; empty uses normal matching");

static int overlay_id;
static struct platform_device *typec_pdev;
static struct device_node *typec_np;

static int __init samurai_dtbo_loader_init(void)
{
	const struct firmware *fw;
	struct spmi_device *sdev;
	struct device_node *pmic_np;
	int ret;

	typec_np = of_find_node_by_path(
		"/soc@0/spmi@c440000/pmic@2/typec@1500");
	if (!typec_np)
		return -ENODEV;

	of_node_set_flag(typec_np, OF_POPULATED);

	ret = request_firmware_direct(&fw, dtbo_name, NULL);
	if (ret) {
		pr_err("samurai-dtbo: failed to load %s: %d\n", dtbo_name, ret);
		goto err_clear_flag;
	}

	ret = of_overlay_fdt_apply(fw->data, fw->size, &overlay_id, NULL);
	release_firmware(fw);
	if (ret) {
		pr_err("samurai-dtbo: overlay apply failed: %d\n", ret);
		if (overlay_id)
			of_overlay_remove(&overlay_id);
		goto err_clear_flag;
	}

	of_node_clear_flag(typec_np, OF_POPULATED);

	pmic_np = of_get_parent(typec_np);
	if (!pmic_np) {
		ret = -ENODEV;
		goto err_remove_overlay;
	}

	sdev = spmi_find_device_by_of_node(pmic_np);
	of_node_put(pmic_np);
	if (!sdev) {
		pr_err("samurai-dtbo: no SPMI parent for Type-C node\n");
		ret = -ENODEV;
		goto err_remove_overlay;
	}

	typec_pdev = platform_device_alloc("samurai-pmic-typec",
					   PLATFORM_DEVID_AUTO);
	if (!typec_pdev) {
		ret = -ENOMEM;
		spmi_device_put(sdev);
		goto err_remove_overlay;
	}

	typec_pdev->dev.parent = &sdev->dev;
	platform_device_set_fwnode(typec_pdev, of_fwnode_handle(typec_np));
	if (platform_driver && *platform_driver) {
		ret = device_set_driver_override(&typec_pdev->dev,
						 platform_driver);
		if (ret) {
			platform_device_put(typec_pdev);
			typec_pdev = NULL;
			spmi_device_put(sdev);
			goto err_remove_overlay;
		}
	}

	ret = platform_device_add(typec_pdev);
	spmi_device_put(sdev);
	if (ret) {
		platform_device_put(typec_pdev);
		typec_pdev = NULL;
		goto err_remove_overlay;
	}

	pr_info("samurai-dtbo: applied %s as changeset %d\n",
		dtbo_name, overlay_id);
	return 0;

err_remove_overlay:
	of_node_clear_flag(typec_np, OF_POPULATED);
	if (overlay_id)
		of_overlay_remove(&overlay_id);
err_clear_flag:
	of_node_clear_flag(typec_np, OF_POPULATED);
	of_node_put(typec_np);
	typec_np = NULL;
	return ret;
}

static void __exit samurai_dtbo_loader_exit(void)
{
	int ret;

	if (!overlay_id)
		return;

	if (typec_pdev) {
		platform_device_unregister(typec_pdev);
		typec_pdev = NULL;
	}

	ret = of_overlay_remove(&overlay_id);
	if (ret)
		pr_err("samurai-dtbo: overlay removal failed: %d\n", ret);
	else
		pr_info("samurai-dtbo: overlay removed\n");

	of_node_put(typec_np);
	typec_np = NULL;
}

module_init(samurai_dtbo_loader_init);
module_exit(samurai_dtbo_loader_exit);

MODULE_DESCRIPTION("Runtime DT overlay loader for RMX1931 diagnostics");
MODULE_LICENSE("GPL");
