// SPDX-License-Identifier: GPL-2.0
/*
 * Copyright (c) 2023, Linaro Ltd. All rights reserved.
 */

#ifndef __QCOM_PMIC_TYPEC_H__
#define __QCOM_PMIC_TYPEC_H__

struct pmic_typec {
	struct device		*dev;
	struct samurai_pd5v	*pd5v;
	struct qcom_pmic_typec_apsd *apsd_handoff;
	bool			samurai_fixed_5v;
	bool			samurai_contract_shutdown;
	int (*read_vbus_uv)(void *context, int *uv);
	bool			samurai_joined;
	bool			samurai_pd_quiet;
	int			samurai_stop_error;
	struct tcpm_port	*tcpm_port;
	struct tcpc_dev		tcpc;
	struct pmic_typec_pdphy	*pmic_typec_pdphy;
	struct pmic_typec_port	*pmic_typec_port;

	int (*pdphy_start)(struct pmic_typec *tcpm,
			   struct tcpm_port *tcpm_port);
	void (*pdphy_stop)(struct pmic_typec *tcpm);

	int (*port_start)(struct pmic_typec *tcpm,
			  struct tcpm_port *tcpm_port);
	void (*port_stop)(struct pmic_typec *tcpm);
};

#define tcpc_to_tcpm(_tcpc_) container_of(_tcpc_, struct pmic_typec, tcpc)

#endif
