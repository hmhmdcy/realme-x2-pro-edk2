# SPDX-License-Identifier: GPL-2.0
obj-m += qcom_pmic_tcpm_alt.o
qcom_pmic_tcpm_alt-y := \
	qcom_pmic_typec.o \
	qcom_pmic_typec_port.o \
	qcom_pmic_typec_pdphy.o \
	qcom_pmic_typec_pdphy_stub.o

ccflags-y += -DQCOM_PMIC_TYPEC_DRIVER_NAME=\"qcom-pmic-typec-alt\"
