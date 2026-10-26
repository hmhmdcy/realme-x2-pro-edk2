// SPDX-License-Identifier: GPL-2.0-only
/* Temporary independent MMCX consumer; no clock or regulator register writes. */
#include <linux/device.h>
#include <linux/err.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/pm_domain.h>
#include <linux/pm_runtime.h>
#include <dt-bindings/power/qcom-rpmpd.h>
#include <dt-bindings/power/qcom,rpmhpd.h>

static bool enable;
module_param(enable, bool, 0400);
MODULE_PARM_DESC(enable, "Explicitly enable temporary MMCX performance request");
static bool active;
module_param(active, bool, 0444);
static unsigned int requested_level;
module_param(requested_level, uint, 0444);
static struct device_node *camcc_node;
static struct device *consumer, *domain;
static bool runtime_held;

static void samurai_camera_perf_cleanup(void)
{
	int ret;

	if (domain) {
		ret = dev_pm_genpd_set_performance_state(domain, 0);
		if (ret)
			pr_err("samurai camera perf: release request failed: %d\n", ret);
		if (runtime_held) {
			ret = pm_runtime_put_sync(domain);
			if (ret < 0)
				pr_err("samurai camera perf: runtime put failed: %d\n", ret);
			runtime_held = false;
		}
		dev_pm_domain_detach(domain, true);
		domain = NULL;
	}
	if (consumer) {
		device_set_node(consumer, NULL);
		root_device_unregister(consumer);
		consumer = NULL;
	}
	of_node_put(camcc_node);
	camcc_node = NULL;
	active = false;
}

static int __init samurai_camera_perf_init(void)
{
	struct of_phandle_args spec;
	int ret;

	if (!enable)
		return -EPERM;
	if (!of_machine_is_compatible("realme,samurai"))
		return -ENODEV;
	camcc_node = of_find_node_by_path("/soc@0/clock-controller@ad00000");
	if (!camcc_node)
		return -ENODEV;
	ret = of_parse_phandle_with_args(camcc_node, "power-domains",
					 "#power-domain-cells", 0, &spec);
	if (ret)
		goto cleanup;
	ret = spec.args_count == 1 && spec.args[0] == SM8150_MMCX &&
		of_device_is_compatible(spec.np, "qcom,sm8150-rpmhpd") ? 0 : -EINVAL;
	of_node_put(spec.np);
	if (ret)
		goto cleanup;
	consumer = root_device_register("samurai-camera-perf");
	if (IS_ERR(consumer)) {
		ret = PTR_ERR(consumer);
		consumer = NULL;
		goto cleanup;
	}
	/* The root device only supplies lookup data to its own virtual consumer. */
	device_set_node(consumer, of_fwnode_handle(camcc_node));
	domain = dev_pm_domain_attach_by_id(consumer, 0);
	if (IS_ERR_OR_NULL(domain)) {
		ret = domain ? PTR_ERR(domain) : -ENODEV;
		domain = NULL;
		goto cleanup;
	}
	ret = pm_runtime_resume_and_get(domain);
	if (ret < 0)
		goto cleanup;
	runtime_held = true;
	ret = dev_pm_genpd_set_performance_state(domain, RPMH_REGULATOR_LEVEL_TURBO);
	if (ret)
		goto cleanup;
	requested_level = RPMH_REGULATOR_LEVEL_TURBO;
	active = true;
	pr_info("samurai camera perf: independent MMCX request=%u active\n",
		requested_level);
	return 0;
cleanup:
	samurai_camera_perf_cleanup();
	return ret;
}

static void __exit samurai_camera_perf_exit(void)
{
	samurai_camera_perf_cleanup();
	pr_info("samurai camera perf: independent consumer removed\n");
}

module_init(samurai_camera_perf_init);
module_exit(samurai_camera_perf_exit);
MODULE_DESCRIPTION("Temporary realme X2 Pro independent MMCX performance consumer");
MODULE_LICENSE("GPL");
