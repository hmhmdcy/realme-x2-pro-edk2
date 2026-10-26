/* Integration reference for the root's merged qcom_pmic_typec_probe().
 * Place after real pdphy_probe + the Samurai profile decision, and BEFORE
 * tcpm_register_port(). This fragment itself was not compiled as a probe.
 * tcpm->read_vbus_uv must already be bound to the proved PM8150B ADC5
 * channel-8 IIO reader returning processed uV, shared with shutdown.
 */
{
	struct qcom_pmic_typec_apsd_start_ops start_ops = {
		.read_vbus_uv = tcpm->read_vbus_uv,
		.quiet_begin = qcom_pmic_typec_pdphy_apsd_begin,
		.quiet_verify = qcom_pmic_typec_pdphy_apsd_verify,
		.quiet_release = qcom_pmic_typec_pdphy_apsd_release,
	};

	tcpm->apsd_handoff = qcom_pmic_typec_apsd_prepare(dev, regmap,
						       &start_ops, tcpm);
	if (IS_ERR(tcpm->apsd_handoff)) {
		ret = PTR_ERR(tcpm->apsd_handoff);
		goto fwnode_remove;
	}
}
