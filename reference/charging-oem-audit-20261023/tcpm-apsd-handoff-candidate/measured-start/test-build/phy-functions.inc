static int qcom_pmic_typec_pdphy_handoff_quiet(struct pmic_typec_pdphy *p)
{
	static const unsigned int controls[] = {
		USB_PDPHY_BIST_MODE_REG, USB_PDPHY_TX_CONTROL_REG,
		USB_PDPHY_FRAME_FILTER_REG, USB_PDPHY_EN_CONTROL_REG,
	};
	unsigned long flags;
	unsigned int i, value;
	int ret = 0;

	if (!p->handoff_powered || p->supply_held || p->tcpm_port || p->irqs_started)
		return -EBUSY;
	spin_lock_irqsave(&p->lock, flags);
	for (i = 0; i < ARRAY_SIZE(controls); i++) {
		ret = regmap_read(p->regmap, p->base + controls[i], &value);
		if (ret)
			break;
		if (value) {
			ret = -EBUSY;
			break;
		}
	}
	spin_unlock_irqrestore(&p->lock, flags);
	return ret;
}

int qcom_pmic_typec_pdphy_apsd_verify(void *context)
{
	struct pmic_typec *tcpm = context;

	if (!tcpm || !tcpm->pmic_typec_pdphy || tcpm->tcpm_port)
		return -EBUSY;
	return qcom_pmic_typec_pdphy_handoff_quiet(tcpm->pmic_typec_pdphy);
}

int qcom_pmic_typec_pdphy_apsd_release(void *context)
{
	struct pmic_typec *tcpm = context;
	struct pmic_typec_pdphy *p;
	int ret;

	if (!tcpm || !tcpm->pmic_typec_pdphy)
		return -EINVAL;
	p = tcpm->pmic_typec_pdphy;
	if (!p->handoff_powered)
		return 0; /* never acquired, already released, or consumed by start */
	if (p->supply_held || p->tcpm_port || p->irqs_started)
		return -EBUSY;
	ret = regulator_disable(p->vdd_pdphy);
	if (!ret)
		p->handoff_powered = false;
	return ret;
}

int qcom_pmic_typec_pdphy_apsd_begin(void *context)
{
	struct pmic_typec *tcpm = context;
	struct pmic_typec_pdphy *p;
	int ret, release;

	if (!tcpm || !tcpm->pmic_typec_pdphy || tcpm->tcpm_port)
		return -EBUSY;
	p = tcpm->pmic_typec_pdphy;
	if (p->handoff_powered || p->supply_held || p->tcpm_port || p->irqs_started)
		return -EBUSY;
	ret = regulator_enable(p->vdd_pdphy);
	if (ret)
		return ret;
	p->handoff_powered = true;
	ret = qcom_pmic_typec_pdphy_handoff_quiet(p);
	if (ret) {
		release = qcom_pmic_typec_pdphy_apsd_release(tcpm);
		if (release)
			dev_err(p->dev, "unverified pre-start PD supply release failed %d\n", release);
	}
	return ret;
}

static void qcom_pmic_typec_pdphy_apsd_cleanup(void *context)
{
	struct pmic_typec *tcpm = context;
	int ret = qcom_pmic_typec_pdphy_apsd_release(tcpm);

	if (ret)
		dev_err(tcpm->dev, "pre-start PD PHY devres release failed %d\n", ret);
}

static int qcom_pmic_typec_pdphy_start(struct pmic_typec *tcpm,
				       struct tcpm_port *tcpm_port)
{
	struct pmic_typec_pdphy *pmic_typec_pdphy = tcpm->pmic_typec_pdphy;
	int i;
	int ret;

	ret = qcom_pmic_typec_apsd_verify(tcpm->apsd_handoff);
	if (ret)
		return ret;
	if (pmic_typec_pdphy->handoff_powered) {
		/* Recheck actual zero controls; transfer the SAME held reference.
		 * The outer tcpm_port was just registered, but this PHY has not
		 * published its own port or enabled IRQs/protocol callbacks yet.
		 */
		ret = qcom_pmic_typec_pdphy_handoff_quiet(pmic_typec_pdphy);
		if (ret)
			return ret;
		pmic_typec_pdphy->supply_held = true;
		pmic_typec_pdphy->handoff_powered = false;
	} else {
		ret = regulator_enable(pmic_typec_pdphy->vdd_pdphy);
		if (ret)
			return ret;
		pmic_typec_pdphy->supply_held = true;
	}
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
