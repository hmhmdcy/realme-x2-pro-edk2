// SPDX-License-Identifier: GPL-2.0
/*
 * Copyright (c) 2023, Linaro Ltd. All rights reserved.
 */

#include <linux/err.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/property.h>
#include <linux/usb/pd.h>
#include <linux/regmap.h>
#include <linux/slab.h>
#include <linux/usb/tcpm.h>

#include <drm/bridge/aux-bridge.h>

#include "qcom_pmic_typec.h"
#include "qcom_pmic_typec_pdphy.h"
#include "qcom_pmic_typec_port.h"
#include "qcom_pmic_typec_5v.h"

static bool samurai_5v_only;
module_param(samurai_5v_only, bool, 0400);
MODULE_PARM_DESC(samurai_5v_only, "Opt in to the explicitly marked Samurai PD-disabled owner");
static struct platform_driver qcom_pmic_typec_driver;

struct pmic_typec_resources {
	const struct pmic_typec_pdphy_resources	*pdphy_res;
	const struct pmic_typec_port_resources	*port_res;
};

static int qcom_pmic_typec_init(struct tcpc_dev *tcpc)
{
	return 0;
}


/* Only the reviewed fixed 5V/500mA, fixed-device Samurai profile uses this
 * handoff. This is not a shutdown-to-5V implementation for a 9V contract.
 */
static bool qcom_pmic_typec_samurai_fixed_5v(struct pmic_typec *tcpm)
{
	struct fwnode_handle *f = tcpm->tcpc.fwnode;
	const char *role;
	u32 pdo, microwatt;

	if (!of_machine_is_compatible("realme,samurai") ||
	    !of_device_is_compatible(tcpm->dev->of_node, "qcom,pm8150b-typec"))
		return false;
	if (fwnode_property_read_string(f, "power-role", &role) || strcmp(role, "sink"))
		return false;
	if (fwnode_property_read_string(f, "data-role", &role) || strcmp(role, "device"))
		return false;
	if (fwnode_property_present(f, "source-pdos") ||
	    fwnode_property_count_u32(f, "sink-pdos") != 1 ||
	    fwnode_property_read_u32(f, "sink-pdos", &pdo) ||
	    pdo != PDO_FIXED(5000, 500, PDO_FIXED_USB_COMM) ||
	    fwnode_property_read_u32(f, "op-sink-microwatt", &microwatt) ||
	    microwatt != 2500000)
		return false;
	return true;
}

/* Only the fixed sink/device Samurai can enter this terminal handoff. */
static bool qcom_pmic_typec_samurai_sink(struct pmic_typec *tcpm)
{
	struct fwnode_handle *f = tcpm->tcpc.fwnode;
	const char *role;

	return of_machine_is_compatible("realme,samurai") &&
		of_device_is_compatible(tcpm->dev->of_node, "qcom,pm8150b-typec") &&
		!fwnode_property_read_string(f, "power-role", &role) &&
		!strcmp(role, "sink") &&
		!fwnode_property_read_string(f, "data-role", &role) &&
		!strcmp(role, "device") &&
		!fwnode_property_present(f, "source-pdos");
}

static int qcom_pmic_typec_stop_samurai_5v(struct pmic_typec *tcpm)
{
	int pd, cc;

	if (tcpm->samurai_joined)
		return tcpm->samurai_stop_error;
	tcpm->port_stop(tcpm);
	qcom_pmic_typec_pdphy_quiesce_5v(tcpm);
	tcpm_unregister_port(tcpm->tcpm_port);
	tcpm->tcpm_port = NULL;
	tcpm->samurai_joined = true;
	pd = qcom_pmic_typec_pdphy_finish_5v(tcpm);
	cc = qcom_pmic_typec_port_finish_5v(tcpm, !pd);
	tcpm->samurai_stop_error = pd ? pd : cc;
	if (tcpm->samurai_stop_error)
		dev_err(tcpm->dev, "fixed5V shutdown failed: PD %d CC %d\n", pd, cc);
	else
		dev_info(tcpm->dev, "fixed5V callbacks joined, PD quiet=%d, sink handoff restored\n",
	          tcpm->samurai_pd_quiet);
	return tcpm->samurai_stop_error;
}

/* Request/measure while every IRQ and TCPM worker is still available. */
static int qcom_pmic_typec_stop_samurai_contract(struct pmic_typec *tcpm)
{
	int ret;

	if (tcpm->samurai_joined)
		return tcpm->samurai_stop_error;
	ret = tcpm_prepare_sink_shutdown(tcpm->tcpm_port, 2000,
					 tcpm->read_vbus_uv, tcpm);
	if (ret) {
		dev_err(tcpm->dev,
			"5V shutdown preparation failed %d; contract/ADC not verified\n", ret);
		return ret;
	}
	return qcom_pmic_typec_stop_samurai_5v(tcpm);
}

/* Removal cannot fail. Join every callback, without claiming a safe-voltage close. */
static void qcom_pmic_typec_abort_samurai(struct pmic_typec *tcpm, int error)
{
	if (!tcpm->samurai_joined) {
		tcpm->port_stop(tcpm);
		qcom_pmic_typec_pdphy_quiesce_5v(tcpm);
		tcpm_unregister_port(tcpm->tcpm_port);
		tcpm->tcpm_port = NULL;
		tcpm->samurai_joined = true;
		/* Remaining TCPM callbacks can queue a final CC debounce during join. */
		tcpm->port_stop(tcpm);
	}
	if (!tcpm->samurai_stop_error)
		tcpm->samurai_stop_error = error;
}

static int qcom_pmic_typec_probe(struct platform_device *pdev)
{
	struct pmic_typec *tcpm;
	struct device *dev = &pdev->dev;
	struct device_node *np = dev->of_node;
	const struct pmic_typec_resources *res;
	struct regmap *regmap;
	struct auxiliary_device *bridge_dev;
	u32 base;
	bool protocol_live = false;
	int ret, stop_error;

	res = of_device_get_match_data(dev);
	if (!res)
		return -ENODEV;

	tcpm = devm_kzalloc(dev, sizeof(*tcpm), GFP_KERNEL);
	if (!tcpm)
		return -ENOMEM;

	tcpm->dev = dev;
	tcpm->tcpc.init = qcom_pmic_typec_init;

	regmap = dev_get_regmap(dev->parent, NULL);
	if (!regmap) {
		dev_err(dev, "Failed to get regmap\n");
		return -ENODEV;
	}

	/* Both explicit opt-ins are required. Never fall through into TCPM
	 * when the special mode is requested but its binding is incomplete. */
	if (samurai_5v_only || of_property_read_bool(np, "realme,pd5v-only")) {
		u32 pd_base;
		if (!samurai_5v_only || !of_property_read_bool(np, "realme,pd5v-only") ||
		    !of_machine_is_compatible("realme,samurai") ||
		    !of_device_is_compatible(np, "qcom,pm8150b-typec"))
			return -EOPNOTSUPP;
		if (of_get_child_count(np))
			return -EBUSY;
		ret = of_property_read_u32_index(np, "reg", 0, &base);
		if (ret)
			return ret;
		ret = of_property_read_u32_index(np, "reg", 1, &pd_base);
		if (ret)
			return ret;
		if (base != 0x1500 || pd_base != 0x1700)
			return -EXDEV;
		tcpm->pd5v = samurai_pd5v_create(dev, regmap);
		if (IS_ERR(tcpm->pd5v))
			return PTR_ERR(tcpm->pd5v);
		platform_set_drvdata(pdev, tcpm);
		return 0;
	}

	ret = of_property_read_u32_index(np, "reg", 0, &base);
	if (ret)
		return ret;

	ret = qcom_pmic_typec_port_probe(pdev, tcpm,
					 res->port_res, regmap, base);
	if (ret)
		return ret;

	if (res->pdphy_res) {
		ret = of_property_read_u32_index(np, "reg", 1, &base);
		if (ret)
			return ret;

		ret = qcom_pmic_typec_pdphy_probe(pdev, tcpm,
						  res->pdphy_res, regmap, base);
		if (ret)
			return ret;
	} else {
		ret = qcom_pmic_typec_pdphy_stub_probe(pdev, tcpm);
		if (ret)
			return ret;
	}

	platform_set_drvdata(pdev, tcpm);

	tcpm->tcpc.fwnode = device_get_named_child_node(tcpm->dev, "connector");
	if (!tcpm->tcpc.fwnode)
		return -EINVAL;

	tcpm->samurai_fixed_5v = qcom_pmic_typec_samurai_fixed_5v(tcpm);
	tcpm->samurai_contract_shutdown = !tcpm->samurai_fixed_5v &&
		qcom_pmic_typec_samurai_sink(tcpm);
	if (tcpm->samurai_contract_shutdown && !tcpm->read_vbus_uv) {
		ret = -EOPNOTSUPP;
		goto fwnode_remove;
	}

	bridge_dev = devm_drm_dp_hpd_bridge_alloc(tcpm->dev, to_of_node(tcpm->tcpc.fwnode));
	if (IS_ERR(bridge_dev)) {
		ret = PTR_ERR(bridge_dev);
		goto fwnode_remove;
	}

	tcpm->tcpm_port = tcpm_register_port(tcpm->dev, &tcpm->tcpc);
	if (IS_ERR(tcpm->tcpm_port)) {
		ret = PTR_ERR(tcpm->tcpm_port);
		goto fwnode_remove;
	}

	ret = tcpm->port_start(tcpm, tcpm->tcpm_port);
	if (ret)
		goto port_unregister;

	ret = tcpm->pdphy_start(tcpm, tcpm->tcpm_port);
	if (ret)
		goto port_stop;
	protocol_live = true;

	ret = devm_drm_dp_hpd_bridge_add(tcpm->dev, bridge_dev);
	if (ret)
		goto pdphy_stop;

	return 0;

pdphy_stop:
	if (!tcpm->samurai_fixed_5v && !tcpm->samurai_contract_shutdown)
		tcpm->pdphy_stop(tcpm);
port_stop:
	if (!tcpm->samurai_fixed_5v && !tcpm->samurai_contract_shutdown)
		tcpm->port_stop(tcpm);
port_unregister:
	if (tcpm->samurai_contract_shutdown) {
		stop_error = protocol_live ? qcom_pmic_typec_stop_samurai_contract(tcpm) : ret;
		if (!tcpm->samurai_joined)
			qcom_pmic_typec_abort_samurai(tcpm, stop_error);
	} else if (tcpm->samurai_fixed_5v) {
		qcom_pmic_typec_stop_samurai_5v(tcpm);
	} else {
		tcpm_unregister_port(tcpm->tcpm_port);
	}
fwnode_remove:
	fwnode_handle_put(tcpm->tcpc.fwnode);

	return ret;
}

static void qcom_pmic_typec_remove(struct platform_device *pdev)
{
	struct pmic_typec *tcpm = platform_get_drvdata(pdev);
	int ret;

	if (tcpm->pd5v) {
		samurai_pd5v_destroy(tcpm->pd5v);
		return;
	}

	if (tcpm->samurai_contract_shutdown) {
		ret = qcom_pmic_typec_stop_samurai_contract(tcpm);
		if (!ret || tcpm->samurai_joined) {
			fwnode_handle_put(tcpm->tcpc.fwnode);
			tcpm->tcpc.fwnode = NULL;
			return;
		}
		/*
		 * platform remove is void: devres WILL be released. Never leave
		 * live IRQ/work callbacks pointing at that freed state. This is
		 * forced teardown, NOT verified 5V handoff; high-PD adoption is
		 * blocked until the removal policy is resolved externally.
		 */
		dev_err(tcpm->dev, "forced remove without verified 5V; joining callbacks\n");
		qcom_pmic_typec_abort_samurai(tcpm, ret);
		/* No SNK_ONLY restore and no successful-5V close claimed. */
		fwnode_handle_put(tcpm->tcpc.fwnode);
		tcpm->tcpc.fwnode = NULL;
		return;
	}

	if (tcpm->samurai_fixed_5v) {
		qcom_pmic_typec_stop_samurai_5v(tcpm);
		fwnode_handle_put(tcpm->tcpc.fwnode);
		tcpm->tcpc.fwnode = NULL;
		return;
	}
	tcpm->pdphy_stop(tcpm);
	tcpm->port_stop(tcpm);
	tcpm_unregister_port(tcpm->tcpm_port);
	fwnode_handle_put(tcpm->tcpc.fwnode);
}

static int qcom_pmic_typec_prepare(struct device *dev)
{
	struct pmic_typec *tcpm = dev_get_drvdata(dev);
	return tcpm->pd5v ? samurai_pd5v_quiesce(tcpm->pd5v) : 0;
}

static void qcom_pmic_typec_complete(struct device *dev)
{
	struct pmic_typec *tcpm = dev_get_drvdata(dev);
	if (tcpm->pd5v)
		samurai_pd5v_complete(tcpm->pd5v);
}

static void qcom_pmic_typec_shutdown(struct platform_device *pdev)
{
	struct pmic_typec *tcpm = platform_get_drvdata(pdev);
	if (tcpm->pd5v)
		samurai_pd5v_quiesce(tcpm->pd5v);
	else if (tcpm->samurai_contract_shutdown) {
		qcom_pmic_typec_stop_samurai_contract(tcpm);
		if (tcpm->samurai_joined) {
			fwnode_handle_put(tcpm->tcpc.fwnode);
			tcpm->tcpc.fwnode = NULL;
		}
	} else if (tcpm->samurai_fixed_5v) {
		qcom_pmic_typec_stop_samurai_5v(tcpm);
		fwnode_handle_put(tcpm->tcpc.fwnode);
		tcpm->tcpc.fwnode = NULL;
	}
}

static const struct dev_pm_ops qcom_pmic_typec_pm_ops = {
	.prepare = qcom_pmic_typec_prepare,
	.complete = qcom_pmic_typec_complete,
};

static const struct pmic_typec_resources pm8150b_typec_res = {
	.pdphy_res = &pm8150b_pdphy_res,
	.port_res = &pm8150b_port_res,
};

static const struct pmic_typec_resources pmi632_typec_res = {
	/* PD PHY not present */
	.port_res = &pm8150b_port_res,
};

static const struct of_device_id qcom_pmic_typec_table[] = {
	{ .compatible = "qcom,pm8150b-typec", .data = &pm8150b_typec_res },
	{ .compatible = "qcom,pmi632-typec", .data = &pmi632_typec_res },
	{ }
};
MODULE_DEVICE_TABLE(of, qcom_pmic_typec_table);

static struct platform_driver qcom_pmic_typec_driver = {
	.driver = {
		.name = "qcom,pmic-typec",
		.of_match_table = qcom_pmic_typec_table,
		.pm = &qcom_pmic_typec_pm_ops,
	},
	.probe = qcom_pmic_typec_probe,
	.remove = qcom_pmic_typec_remove,
	.shutdown = qcom_pmic_typec_shutdown,
};

module_platform_driver(qcom_pmic_typec_driver);

MODULE_DESCRIPTION("QCOM PMIC USB Type-C Port Manager Driver");
MODULE_LICENSE("GPL");
