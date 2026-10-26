// SPDX-License-Identifier: GPL-2.0
/*
 * Copyright (c) 2023, Linaro Ltd. All rights reserved.
 */

#ifndef __QCOM_PMIC_TYPEC_H__
#define __QCOM_PMIC_TYPEC_H__

struct pmic_typec {
	struct device		*dev;
	struct samurai_pd5v	*pd5v;
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
#define TYPEC_SNK_STATUS_REG				0x06
#define DETECTED_SNK_TYPE_MASK				GENMASK(6, 0)
#define SNK_DAM_MASK					GENMASK(6, 4)
#define SNK_DAM_500MA					BIT(6)
#define SNK_DAM_1500MA					BIT(5)
#define SNK_DAM_3000MA					BIT(4)
#define SNK_RP_STD					BIT(3)
#define SNK_RP_1P5					BIT(2)
#define SNK_RP_3P0					BIT(1)
#define SNK_RP_SHORT					BIT(0)

#define TYPEC_SRC_STATUS_REG				0x08
#define DETECTED_SRC_TYPE_MASK				GENMASK(4, 0)
#define SRC_HIGH_BATT					BIT(5)
#define SRC_DEBUG_ACCESS				BIT(4)
#define SRC_RD_OPEN					BIT(3)
#define SRC_RD_RA_VCONN					BIT(2)
#define SRC_RA_OPEN					BIT(1)
#define AUDIO_ACCESS_RA_RA				BIT(0)

#define TYPEC_STATE_MACHINE_STATUS_REG			0x09
#define TYPEC_ATTACH_DETACH_STATE			BIT(5)

#define TYPEC_SM_STATUS_REG				0x0A
#define TYPEC_SM_VBUS_VSAFE5V				BIT(5)
#define TYPEC_SM_VBUS_VSAFE0V				BIT(6)
#define TYPEC_SM_USBIN_LT_LV				BIT(7)

#define TYPEC_MISC_STATUS_REG				0x0B
#define TYPEC_WATER_DETECTION_STATUS			BIT(7)
#define SNK_SRC_MODE					BIT(6)
#define TYPEC_VBUS_DETECT				BIT(5)
#define TYPEC_VBUS_ERROR_STATUS				BIT(4)
#define TYPEC_DEBOUNCE_DONE				BIT(3)
#define CC_ORIENTATION					BIT(1)
#define CC_ATTACHED					BIT(0)

#define LEGACY_CABLE_STATUS_REG				0x0D
#define TYPEC_LEGACY_CABLE_STATUS			BIT(1)
#define TYPEC_NONCOMP_LEGACY_CABLE_STATUS		BIT(0)

#define TYPEC_U_USB_STATUS_REG				0x0F
#define U_USB_GROUND_NOVBUS				BIT(6)
#define U_USB_GROUND					BIT(4)
#define U_USB_FMB1					BIT(3)
#define U_USB_FLOAT1					BIT(2)
#define U_USB_FMB2					BIT(1)
#define U_USB_FLOAT2					BIT(0)

#define TYPEC_MODE_CFG_REG				0x44
#define TYPEC_TRY_MODE_MASK				GENMASK(4, 3)
#define EN_TRY_SNK					BIT(4)
#define EN_TRY_SRC					BIT(3)
#define TYPEC_POWER_ROLE_CMD_MASK			GENMASK(2, 0)
#define EN_SRC_ONLY					BIT(2)
#define EN_SNK_ONLY					BIT(1)
#define TYPEC_DISABLE_CMD				BIT(0)

#define TYPEC_VCONN_CONTROL_REG				0x46
#define VCONN_EN_ORIENTATION				BIT(2)
#define VCONN_EN_VALUE					BIT(1)
#define VCONN_EN_SRC					BIT(0)

#define TYPEC_CCOUT_CONTROL_REG				0x48
#define TYPEC_CCOUT_BUFFER_EN				BIT(2)
#define TYPEC_CCOUT_VALUE				BIT(1)
#define TYPEC_CCOUT_SRC					BIT(0)

#define DEBUG_ACCESS_SRC_CFG_REG			0x4C
#define EN_UNORIENTED_DEBUG_ACCESS_SRC			BIT(0)

#define TYPE_C_CRUDE_SENSOR_CFG_REG			0x4e
#define EN_SRC_CRUDE_SENSOR				BIT(1)
#define EN_SNK_CRUDE_SENSOR				BIT(0)

#define TYPEC_EXIT_STATE_CFG_REG			0x50
#define BYPASS_VSAFE0V_DURING_ROLE_SWAP			BIT(3)
#define SEL_SRC_UPPER_REF				BIT(2)
#define USE_TPD_FOR_EXITING_ATTACHSRC			BIT(1)
#define EXIT_SNK_BASED_ON_CC				BIT(0)

#define TYPEC_CURRSRC_CFG_REG				0x52
#define TYPEC_SRC_RP_SEL_330UA				BIT(1)
#define TYPEC_SRC_RP_SEL_180UA				BIT(0)
#define TYPEC_SRC_RP_SEL_80UA				0
#define TYPEC_SRC_RP_SEL_MASK				GENMASK(1, 0)

#define TYPEC_INTERRUPT_EN_CFG_1_REG			0x5E
#define TYPEC_LEGACY_CABLE_INT_EN			BIT(7)
#define TYPEC_NONCOMPLIANT_LEGACY_CABLE_INT_EN		BIT(6)
#define TYPEC_TRYSOURCE_DETECT_INT_EN			BIT(5)
#define TYPEC_TRYSINK_DETECT_INT_EN			BIT(4)
#define TYPEC_CCOUT_DETACH_INT_EN			BIT(3)
#define TYPEC_CCOUT_ATTACH_INT_EN			BIT(2)
#define TYPEC_VBUS_DEASSERT_INT_EN			BIT(1)
#define TYPEC_VBUS_ASSERT_INT_EN			BIT(0)

#define TYPEC_INTERRUPT_EN_CFG_2_REG			0x60
#define TYPEC_SRC_BATT_HPWR_INT_EN			BIT(6)
#define MICRO_USB_STATE_CHANGE_INT_EN			BIT(5)
#define TYPEC_STATE_MACHINE_CHANGE_INT_EN		BIT(4)
#define TYPEC_DEBUG_ACCESS_DETECT_INT_EN		BIT(3)
#define TYPEC_WATER_DETECTION_INT_EN			BIT(2)
#define TYPEC_VBUS_ERROR_INT_EN				BIT(1)
#define TYPEC_DEBOUNCE_DONE_INT_EN			BIT(0)

#define TYPEC_DEBOUNCE_OPTION_REG			0x62
#define REDUCE_TCCDEBOUNCE_TO_2MS			BIT(2)

#define TYPE_C_SBU_CFG_REG				0x6A
#define SEL_SBU1_ISRC_VAL				0x04
#define SEL_SBU2_ISRC_VAL				0x01

#define TYPEC_U_USB_CFG_REG				0x70
#define EN_MICRO_USB_FACTORY_MODE			BIT(1)
#define EN_MICRO_USB_MODE				BIT(0)

#define TYPEC_PMI632_U_USB_WATER_PROTECTION_CFG_REG	0x72

#define TYPEC_U_USB_WATER_PROTECTION_CFG_REG		0x73
#define EN_MICRO_USB_WATER_PROTECTION			BIT(4)
#define MICRO_USB_DETECTION_ON_TIME_CFG_MASK		GENMASK(3, 2)
#define MICRO_USB_DETECTION_PERIOD_CFG_MASK		GENMASK(1, 0)

#define TYPEC_PMI632_MICRO_USB_MODE_REG			0x73
#define MICRO_USB_MODE_ONLY				BIT(0)

/* Interrupt numbers */
#define PMIC_TYPEC_OR_RID_IRQ				0x0
#define PMIC_TYPEC_VPD_IRQ				0x1
#define PMIC_TYPEC_CC_STATE_IRQ				0x2
#define PMIC_TYPEC_VCONN_OC_IRQ				0x3
#define PMIC_TYPEC_VBUS_IRQ				0x4
#define PMIC_TYPEC_ATTACH_DETACH_IRQ			0x5
#define PMIC_TYPEC_LEGACY_CABLE_IRQ			0x6
#define PMIC_TYPEC_TRY_SNK_SRC_IRQ			0x7

struct pmic_typec_port_irq_data {
	int				virq;
	int				irq;
	struct pmic_typec_port		*pmic_typec_port;
};

struct pmic_typec_port {
	struct device			*dev;
	struct tcpm_port		*tcpm_port;
	struct regmap			*regmap;
	u32				base;
	unsigned int			nr_irqs;
	struct pmic_typec_port_irq_data	*irq_data;

	struct power_supply		*usb_psy;
	struct iio_channel		*vbus_adc;
	struct regulator		*vdd_vbus;
	bool				vbus_enabled;
	bool				sink_only;
	bool				irqs_started;
	struct mutex			vbus_lock;		/* VBUS state serialization */

	int				cc;
	bool				debouncing_cc;
	struct delayed_work		cc_debounce_dwork;

	spinlock_t			lock;	/* Register atomicity */
};

/* PD PHY register offsets and bit fields */
#define USB_PDPHY_MSG_CONFIG_REG	0x40
#define MSG_CONFIG_PORT_DATA_ROLE	BIT(3)
#define MSG_CONFIG_PORT_POWER_ROLE	BIT(2)
#define MSG_CONFIG_SPEC_REV_MASK	(BIT(1) | BIT(0))

#define USB_PDPHY_EN_CONTROL_REG	0x46
#define CONTROL_ENABLE			BIT(0)

#define USB_PDPHY_RX_STATUS_REG		0x4A
#define RX_FRAME_TYPE			(BIT(0) | BIT(1) | BIT(2))

#define USB_PDPHY_FRAME_FILTER_REG	0x4C
#define FRAME_FILTER_EN_HARD_RESET	BIT(5)
#define FRAME_FILTER_EN_SOP		BIT(0)

#define USB_PDPHY_TX_SIZE_REG		0x42
#define TX_SIZE_MASK			0xF

#define USB_PDPHY_TX_CONTROL_REG	0x44
#define TX_CONTROL_RETRY_COUNT(n)	(((n) & 0x3) << 5)
#define TX_CONTROL_FRAME_TYPE(n)        (((n) & 0x7) << 2)
#define TX_CONTROL_FRAME_TYPE_CABLE_RESET	(0x1 << 2)
#define TX_CONTROL_SEND_SIGNAL		BIT(1)
#define TX_CONTROL_SEND_MSG		BIT(0)

#define USB_PDPHY_RX_SIZE_REG		0x48

#define USB_PDPHY_RX_ACKNOWLEDGE_REG	0x4B
#define RX_BUFFER_TOKEN			BIT(0)

#define USB_PDPHY_BIST_MODE_REG		0x4E
#define BIST_MODE_MASK			0xF
#define BIST_ENABLE			BIT(7)
#define PD_MSG_BIST			0x3
#define PD_BIST_TEST_DATA_MODE		0x8

#define USB_PDPHY_TX_BUFFER_HDR_REG	0x60
#define USB_PDPHY_TX_BUFFER_DATA_REG	0x62

#define USB_PDPHY_RX_BUFFER_REG		0x80

/* VDD regulator */
#define VDD_PDPHY_VOL_MIN		2800000	/* uV */
#define VDD_PDPHY_VOL_MAX		3300000	/* uV */
#define VDD_PDPHY_HPM_LOAD		3000	/* uA */

/* Message Spec Rev field */
#define PD_MSG_HDR_REV(hdr)		(((hdr) >> 6) & 3)

/* timers */
#define RECEIVER_RESPONSE_TIME		15	/* tReceiverResponse */
#define HARD_RESET_COMPLETE_TIME	5	/* tHardResetComplete */

/* Interrupt numbers */
#define PMIC_PDPHY_SIG_TX_IRQ		0x0
#define PMIC_PDPHY_SIG_RX_IRQ		0x1
#define PMIC_PDPHY_MSG_TX_IRQ		0x2
#define PMIC_PDPHY_MSG_RX_IRQ		0x3
#define PMIC_PDPHY_MSG_TX_FAIL_IRQ	0x4
#define PMIC_PDPHY_MSG_TX_DISCARD_IRQ	0x5
#define PMIC_PDPHY_MSG_RX_DISCARD_IRQ	0x6
#define PMIC_PDPHY_FR_SWAP_IRQ		0x7


struct pmic_typec_pdphy_irq_data {
	int				virq;
	int				irq;
	struct pmic_typec_pdphy		*pmic_typec_pdphy;
};

struct pmic_typec_pdphy {
	struct device			*dev;
	struct tcpm_port		*tcpm_port;
	struct regmap			*regmap;
	u32				base;

	unsigned int			nr_irqs;
	struct pmic_typec_pdphy_irq_data	*irq_data;

	struct work_struct		reset_work;
	struct work_struct		receive_work;
	struct regulator		*vdd_pdphy;
	bool			supply_held;
	bool			irqs_started;
	spinlock_t			lock;		/* Register atomicity */
};

