/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef QCOM_PMIC_TYPEC_APSD_H
#define QCOM_PMIC_TYPEC_APSD_H
struct device;
struct regmap;
struct qcom_pmic_typec_apsd;
struct qcom_pmic_typec_apsd *
qcom_pmic_typec_apsd_prepare(struct device *dev, struct regmap *map);
/* Read-only guard. NULL is for other boards/the unchanged fixed-5V profile.
 * No native power_supply getter, TCPM callback or worker join is performed.
 */
int qcom_pmic_typec_apsd_verify(struct qcom_pmic_typec_apsd *handoff);
#endif
