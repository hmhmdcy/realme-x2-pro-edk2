static int qcom_pmic_typec_init(struct tcpc_dev *tcpc)
{
	return 0;
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
	int ret;

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

	ret = devm_drm_dp_hpd_bridge_add(tcpm->dev, bridge_dev);
	if (ret)
		goto pdphy_stop;

	return 0;

pdphy_stop:
	tcpm->pdphy_stop(tcpm);
port_stop:
	tcpm->port_stop(tcpm);
port_unregister:
	tcpm_unregister_port(tcpm->tcpm_port);
fwnode_remove:
	fwnode_handle_put(tcpm->tcpc.fwnode);

	return ret;
}

static void qcom_pmic_typec_remove(struct platform_device *pdev)
{
	struct pmic_typec *tcpm = platform_get_drvdata(pdev);

	if (tcpm->pd5v) {
		samurai_pd5v_destroy(tcpm->pd5v);
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
