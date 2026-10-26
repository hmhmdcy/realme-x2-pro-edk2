static void qcom_pmic_typec_port_stop(struct pmic_typec *tcpm)
{
	struct pmic_typec_port *pmic_typec_port = tcpm->pmic_typec_port;
	int i;

	if ((!tcpm->samurai_fixed_5v && !tcpm->samurai_contract_shutdown) ||
	    pmic_typec_port->irqs_started) {
		for (i = 0; i < pmic_typec_port->nr_irqs; i++)
			disable_irq(pmic_typec_port->irq_data[i].irq);
	}
	pmic_typec_port->irqs_started = false;

	disable_delayed_work_sync(&pmic_typec_port->cc_debounce_dwork);
	if (tcpm->samurai_joined)
		pmic_typec_port->tcpm_port = NULL;
}
int qcom_pmic_typec_port_finish_5v(struct pmic_typec *tcpm, bool restore_sink)
{
	struct pmic_typec_port *p = tcpm->pmic_typec_port;
	unsigned int mode = restore_sink ? EN_SNK_ONLY : TYPEC_DISABLE_CMD, val;
	int ret;

	if (!tcpm->samurai_joined || tcpm->tcpm_port || p->irqs_started)
		return -EBUSY;
	/* TCPM work can queue a last debounce after the first port_stop(). */
	disable_delayed_work_sync(&p->cc_debounce_dwork);
	p->tcpm_port = NULL;
	ret = regmap_write(p->regmap, p->base + TYPEC_MODE_CFG_REG, mode);
	if (ret)
		return ret;
	ret = regmap_read(p->regmap, p->base + TYPEC_MODE_CFG_REG, &val);
	return ret ? ret : val == mode ? 0 : -EIO;
}
static void qcom_pmic_typec_pdphy_reset_on(struct pmic_typec_pdphy *pmic_typec_pdphy)
{
	struct device *dev = pmic_typec_pdphy->dev;
	int ret;

	/* Terminate TX */
	ret = regmap_write(pmic_typec_pdphy->regmap,
			   pmic_typec_pdphy->base + USB_PDPHY_TX_CONTROL_REG, 0);
	if (ret)
		goto err;

	ret = regmap_write(pmic_typec_pdphy->regmap,
			   pmic_typec_pdphy->base + USB_PDPHY_FRAME_FILTER_REG, 0);
	if (ret)
		goto err;

	return;
err:
	dev_err(dev, "pd_reset_on error\n");
}
static void qcom_pmic_typec_pdphy_reset_off(struct pmic_typec_pdphy *pmic_typec_pdphy)
{
	struct device *dev = pmic_typec_pdphy->dev;
	int ret;

	ret = regmap_write(pmic_typec_pdphy->regmap,
			   pmic_typec_pdphy->base + USB_PDPHY_FRAME_FILTER_REG,
			   FRAME_FILTER_EN_SOP | FRAME_FILTER_EN_HARD_RESET);
	if (ret)
		dev_err(dev, "pd_reset_off error\n");
}
static int qcom_pmic_typec_pdphy_enable(struct pmic_typec_pdphy *pmic_typec_pdphy)
{
	struct device *dev = pmic_typec_pdphy->dev;
	int ret;

	/* PD 2.0, DR=TYPEC_DEVICE, PR=TYPEC_SINK */
	ret = regmap_update_bits(pmic_typec_pdphy->regmap,
				 pmic_typec_pdphy->base + USB_PDPHY_MSG_CONFIG_REG,
				 MSG_CONFIG_SPEC_REV_MASK, PD_REV20);
	if (ret)
		goto done;

	ret = regmap_write(pmic_typec_pdphy->regmap,
			   pmic_typec_pdphy->base + USB_PDPHY_EN_CONTROL_REG, 0);
	if (ret)
		goto done;

	ret = regmap_write(pmic_typec_pdphy->regmap,
			   pmic_typec_pdphy->base + USB_PDPHY_EN_CONTROL_REG,
			   CONTROL_ENABLE);
	if (ret)
		goto done;

	qcom_pmic_typec_pdphy_reset_off(pmic_typec_pdphy);
done:
	if (ret)
		dev_err(dev, "pdphy_enable fail %d\n", ret);

	return ret;
}
static int qcom_pmic_typec_pdphy_disable(struct pmic_typec_pdphy *pmic_typec_pdphy)
{
	int ret;

	qcom_pmic_typec_pdphy_reset_on(pmic_typec_pdphy);

	ret = regmap_write(pmic_typec_pdphy->regmap,
			   pmic_typec_pdphy->base + USB_PDPHY_EN_CONTROL_REG, 0);

	return ret;
}
static int pmic_typec_pdphy_reset(struct pmic_typec_pdphy *pmic_typec_pdphy)
{
	int ret;

	ret = qcom_pmic_typec_pdphy_disable(pmic_typec_pdphy);
	if (ret)
		goto done;

	usleep_range(400, 500);
	ret = qcom_pmic_typec_pdphy_enable(pmic_typec_pdphy);
done:
	return ret;
}
static int qcom_pmic_typec_pdphy_start(struct pmic_typec *tcpm,
				       struct tcpm_port *tcpm_port)
{
	struct pmic_typec_pdphy *pmic_typec_pdphy = tcpm->pmic_typec_pdphy;
	int i;
	int ret;

	ret = regulator_enable(pmic_typec_pdphy->vdd_pdphy);
	if (ret)
		return ret;

	pmic_typec_pdphy->supply_held = true;
	pmic_typec_pdphy->tcpm_port = tcpm_port;

	ret = pmic_typec_pdphy_reset(pmic_typec_pdphy);
	if (ret)
		goto err_disable_vdd_pdhy;

	for (i = 0; i < pmic_typec_pdphy->nr_irqs; i++)
		enable_irq(pmic_typec_pdphy->irq_data[i].irq);
	pmic_typec_pdphy->irqs_started = true;

	return 0;

err_disable_vdd_pdhy:
	/* This profile joins TCPM before disabling its still-owned PD supply. */
	if (tcpm->samurai_fixed_5v || tcpm->samurai_contract_shutdown)
		return ret;
	regulator_disable(pmic_typec_pdphy->vdd_pdphy);
	pmic_typec_pdphy->supply_held = false;

	return ret;
}
void qcom_pmic_typec_pdphy_quiesce_5v(struct pmic_typec *tcpm)
{
	struct pmic_typec_pdphy *p = tcpm->pmic_typec_pdphy;
	int i;

	if (p->irqs_started) {
		for (i = 0; i < p->nr_irqs; i++)
			disable_irq(p->irq_data[i].irq);
		p->irqs_started = false;
	}
	/* receive_work is unused/uninitialised in this source; RX runs in the IRQ. */
	cancel_work_sync(&p->reset_work);
}
int qcom_pmic_typec_pdphy_finish_5v(struct pmic_typec *tcpm)
{
	static const unsigned int controls[] = {
		USB_PDPHY_BIST_MODE_REG, USB_PDPHY_TX_CONTROL_REG,
		USB_PDPHY_FRAME_FILTER_REG, USB_PDPHY_EN_CONTROL_REG,
	};
	struct pmic_typec_pdphy *p = tcpm->pmic_typec_pdphy;
	unsigned int val;
	int i, ret, first = 0;

	if (!tcpm->samurai_joined || tcpm->tcpm_port || p->irqs_started)
		return -EBUSY;
	p->tcpm_port = NULL;
	if (!p->supply_held)
		return 0; /* Startup never acquired the supply; no disabled proof claimed. */
	for (i = 0; i < ARRAY_SIZE(controls); i++) {
		ret = regmap_write(p->regmap, p->base + controls[i], 0);
		if (ret) {
			if (!first)
	   first = ret;
			continue;
		}
		ret = regmap_read(p->regmap, p->base + controls[i], &val);
		if (!ret && val)
			ret = -EIO;
		if (ret && !first)
			first = ret;
	}
	if (first)
		return first; /* Retain power on unknown control state, without retries. */
	tcpm->samurai_pd_quiet = true;
	ret = regulator_disable(p->vdd_pdphy);
	if (!ret)
		p->supply_held = false;
	return ret;
}
static void qcom_pmic_typec_pdphy_stop(struct pmic_typec *tcpm)
{
	struct pmic_typec_pdphy *pmic_typec_pdphy = tcpm->pmic_typec_pdphy;
	int i;

	for (i = 0; i < pmic_typec_pdphy->nr_irqs; i++)
		disable_irq(pmic_typec_pdphy->irq_data[i].irq);

	cancel_work_sync(&pmic_typec_pdphy->reset_work);

	qcom_pmic_typec_pdphy_reset_on(pmic_typec_pdphy);

	regulator_disable(pmic_typec_pdphy->vdd_pdphy);
}
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
