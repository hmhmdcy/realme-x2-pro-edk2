/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef QCOM_PMIC_TYPEC_APSD_H
#define QCOM_PMIC_TYPEC_APSD_H
struct device;
struct regmap;
struct qcom_pmic_typec_apsd;

/* Original bound Type-C driver invokes prepare before tcpm_register_port.
 * read_vbus_uv must perform a NEW real PM8150B ADC5 USB_IN_V_16 conversion
 * (channel 8, processed value already uV), never a cached TCPM/psy voltage.
 * quiet_begin holds the real pre-start PD PHY supply and reads four controls;
 * quiet_verify rechecks that held reference and actual zero controls;
 * quiet_release drops only a still-untransferred pre-start supply reference.
 * All callbacks are sleepable, synchronous and owned by this device's actual
 * probe/devres lifetime. The ops are copied, not retained by caller address.
 */
struct qcom_pmic_typec_apsd_start_ops {
	int (*read_vbus_uv)(void *context, int *uv);
	int (*quiet_begin)(void *context);
	int (*quiet_verify)(void *context);
	int (*quiet_release)(void *context);
};

struct qcom_pmic_typec_apsd *qcom_pmic_typec_apsd_prepare(
	struct device *dev, struct regmap *map,
	const struct qcom_pmic_typec_apsd_start_ops *ops, void *context);
int qcom_pmic_typec_apsd_verify(struct qcom_pmic_typec_apsd *handoff);
#endif
