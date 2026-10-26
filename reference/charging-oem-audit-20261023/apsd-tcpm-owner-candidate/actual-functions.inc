void tcpm_pd_receive(struct tcpm_port *port, const struct pd_message *msg,
		     enum tcpm_transmit_type rx_sop_type)
{
	struct pd_rx_event *event;

	event = kzalloc_obj(*event, GFP_ATOMIC);
	if (!event)
		return;

	kthread_init_work(&event->work, tcpm_pd_rx_handler);
	event->port = port;
	event->rx_sop_type = rx_sop_type;
	memcpy(&event->msg, msg, sizeof(*msg));
	kthread_queue_work(port->wq, &event->work);
}

void tcpm_pd_hard_reset(struct tcpm_port *port)
{
	spin_lock(&port->pd_event_lock);
	port->pd_events = TCPM_RESET_EVENT;
	spin_unlock(&port->pd_event_lock);
	kthread_queue_work(port->wq, &port->event_work);
}

void tcpm_cc_change(struct tcpm_port *port)
{
	spin_lock(&port->pd_event_lock);
	port->pd_events |= TCPM_CC_EVENT;
	spin_unlock(&port->pd_event_lock);
	kthread_queue_work(port->wq, &port->event_work);
}

static void qcom_pmic_typec_pdphy_sig_reset_work(struct work_struct *work)
{
	struct pmic_typec_pdphy *pmic_typec_pdphy = container_of(work, struct pmic_typec_pdphy,
						     reset_work);
	unsigned long flags;

	spin_lock_irqsave(&pmic_typec_pdphy->lock, flags);

	qcom_pmic_typec_pdphy_reset_on(pmic_typec_pdphy);
	qcom_pmic_typec_pdphy_reset_off(pmic_typec_pdphy);

	spin_unlock_irqrestore(&pmic_typec_pdphy->lock, flags);

	tcpm_pd_hard_reset(pmic_typec_pdphy->tcpm_port);
}

static irqreturn_t qcom_pmic_typec_pdphy_isr(int irq, void *dev_id)
{
	struct pmic_typec_pdphy_irq_data *irq_data = dev_id;
	struct pmic_typec_pdphy *pmic_typec_pdphy = irq_data->pmic_typec_pdphy;
	struct device *dev = pmic_typec_pdphy->dev;

	switch (irq_data->virq) {
	case PMIC_PDPHY_SIG_TX_IRQ:
		dev_err(dev, "isr: tx_sig\n");
		break;
	case PMIC_PDPHY_SIG_RX_IRQ:
		schedule_work(&pmic_typec_pdphy->reset_work);
		break;
	case PMIC_PDPHY_MSG_TX_IRQ:
		tcpm_pd_transmit_complete(pmic_typec_pdphy->tcpm_port,
					  TCPC_TX_SUCCESS);
		break;
	case PMIC_PDPHY_MSG_RX_IRQ:
		qcom_pmic_typec_pdphy_pd_receive(pmic_typec_pdphy);
		break;
	case PMIC_PDPHY_MSG_TX_FAIL_IRQ:
		tcpm_pd_transmit_complete(pmic_typec_pdphy->tcpm_port,
					  TCPC_TX_FAILED);
		break;
	case PMIC_PDPHY_MSG_TX_DISCARD_IRQ:
		tcpm_pd_transmit_complete(pmic_typec_pdphy->tcpm_port,
					  TCPC_TX_DISCARDED);
		break;
	}

	return IRQ_HANDLED;
}

static int qcom_pmic_typec_pdphy_set_pd_rx(struct tcpc_dev *tcpc, bool on)
{
	struct pmic_typec *tcpm = tcpc_to_tcpm(tcpc);
	struct pmic_typec_pdphy *pmic_typec_pdphy = tcpm->pmic_typec_pdphy;
	unsigned long flags;
	int ret;

	spin_lock_irqsave(&pmic_typec_pdphy->lock, flags);

	ret = regmap_write(pmic_typec_pdphy->regmap,
			   pmic_typec_pdphy->base + USB_PDPHY_RX_ACKNOWLEDGE_REG, !on);

	spin_unlock_irqrestore(&pmic_typec_pdphy->lock, flags);

	dev_dbg(pmic_typec_pdphy->dev, "set_pd_rx: %s\n", str_on_off(on));

	return ret;
}

static int qcom_pmic_typec_pdphy_set_roles(struct tcpc_dev *tcpc, bool attached,
					   enum typec_role power_role,
					   enum typec_data_role data_role)
{
	struct pmic_typec *tcpm = tcpc_to_tcpm(tcpc);
	struct pmic_typec_pdphy *pmic_typec_pdphy = tcpm->pmic_typec_pdphy;
	struct device *dev = pmic_typec_pdphy->dev;
	unsigned long flags;
	int ret;

	spin_lock_irqsave(&pmic_typec_pdphy->lock, flags);

	ret = regmap_update_bits(pmic_typec_pdphy->regmap,
				 pmic_typec_pdphy->base + USB_PDPHY_MSG_CONFIG_REG,
				 MSG_CONFIG_PORT_DATA_ROLE |
				 MSG_CONFIG_PORT_POWER_ROLE,
				 (data_role == TYPEC_HOST ? MSG_CONFIG_PORT_DATA_ROLE : 0) |
				 (power_role == TYPEC_SOURCE ? MSG_CONFIG_PORT_POWER_ROLE : 0));

	spin_unlock_irqrestore(&pmic_typec_pdphy->lock, flags);

	dev_dbg(dev, "pdphy_set_roles: data_role_host=%d power_role_src=%d\n",
		data_role, power_role);

	return ret;
}

static int qcom_pmic_typec_port_vbus_detect(struct pmic_typec_port *pmic_typec_port)
{
	struct device *dev = pmic_typec_port->dev;
	unsigned int misc;
	int ret;

	ret = regmap_read(pmic_typec_port->regmap,
			  pmic_typec_port->base + TYPEC_MISC_STATUS_REG,
			  &misc);
	if (ret)
		misc = 0;

	dev_dbg(dev, "get_vbus: 0x%08x detect %d\n", misc, !!(misc & TYPEC_VBUS_DETECT));

	return !!(misc & TYPEC_VBUS_DETECT);
}

static int qcom_pmic_typec_port_get_vbus(struct tcpc_dev *tcpc)
{
	struct pmic_typec *tcpm = tcpc_to_tcpm(tcpc);
	struct pmic_typec_port *pmic_typec_port = tcpm->pmic_typec_port;
	int ret;

	mutex_lock(&pmic_typec_port->vbus_lock);
	ret = pmic_typec_port->vbus_enabled || qcom_pmic_typec_port_vbus_detect(pmic_typec_port);
	mutex_unlock(&pmic_typec_port->vbus_lock);

	return ret;
}

