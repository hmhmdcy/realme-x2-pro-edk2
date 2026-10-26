#define USB2_PHY_USB_PHY_UTMI_CTRL0		(0x3c)
#define SLEEPM					BIT(0)
#define OPMODE_MASK				GENMASK(4, 3)
#define OPMODE_NORMAL				(0x00)
#define OPMODE_NONDRIVING			BIT(3)
#define TERMSEL					BIT(5)
#define USB2_PHY_USB_PHY_UTMI_CTRL1		(0x40)
#define XCVRSEL					BIT(0)
#define USB2_PHY_USB_PHY_UTMI_CTRL5		(0x50)
#define POR					BIT(1)
#define USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON0	(0x54)
#define SIDDQ					BIT(2)
#define RETENABLEN				BIT(3)
#define FSEL_MASK				GENMASK(6, 4)
#define FSEL_DEFAULT				(0x3 << 4)
#define USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON1	(0x58)
#define VBUSVLDEXTSEL0				BIT(4)
#define PLLBTUNE				BIT(5)
#define USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON2	(0x5c)
#define VREGBYPASS				BIT(0)
#define USB2_PHY_USB_PHY_HS_PHY_CTRL1		(0x60)
#define VBUSVLDEXT0				BIT(0)
#define USB2_PHY_USB_PHY_HS_PHY_CTRL2		(0x64)
#define USB2_AUTO_RESUME			BIT(0)
#define USB2_SUSPEND_N				BIT(2)
#define USB2_SUSPEND_N_SEL			BIT(3)
#define USB2_PHY_USB_PHY_HS_PHY_OVERRIDE_X0		(0x6c)
#define USB2_PHY_USB_PHY_HS_PHY_OVERRIDE_X1		(0x70)
#define USB2_PHY_USB_PHY_HS_PHY_OVERRIDE_X2		(0x74)
#define USB2_PHY_USB_PHY_HS_PHY_OVERRIDE_X3		(0x78)
#define PARAM_OVRD_MASK				0xFF
#define USB2_PHY_USB_PHY_CFG0			(0x94)
#define UTMI_PHY_DATAPATH_CTRL_OVERRIDE_EN	BIT(0)
#define UTMI_PHY_CMN_CTRL_OVERRIDE_EN		BIT(1)
#define USB2_PHY_USB_PHY_REFCLK_CTRL		(0xa0)
#define REFCLK_SEL_MASK				GENMASK(1, 0)
#define REFCLK_SEL_DEFAULT			(0x2 << 0)
#define HS_DISCONNECT_MASK			GENMASK(2, 0)
#define SQUELCH_DETECTOR_MASK			GENMASK(7, 5)
#define HS_AMPLITUDE_MASK			GENMASK(3, 0)
#define PREEMPHASIS_DURATION_MASK		BIT(5)
#define PREEMPHASIS_AMPLITUDE_MASK		GENMASK(7, 6)
#define HS_RISE_FALL_MASK			GENMASK(1, 0)
#define HS_CROSSOVER_VOLTAGE_MASK		GENMASK(3, 2)
#define HS_OUTPUT_IMPEDANCE_MASK		GENMASK(5, 4)
#define LS_FS_OUTPUT_IMPEDANCE_MASK		GENMASK(3, 0)
#define NUM_HSPHY_TUNING_PARAMS	(9)
#define SNPS_HS_NUM_VREGS 3
/* SPDX-License-Identifier: GPL-2.0 */
#ifndef QCOM_SNPS_FEMTO_V2_WINDOW_H
#define QCOM_SNPS_FEMTO_V2_WINDOW_H
struct phy;

/* Internal same-Image interface; no exported module symbol or UAPI. The
 * provider registration holds the real client lifetime; public operations
 * are fenced/drained before devres. Caller still owns a successful active DWC
 * HALT window through end and joins before its own UDC/core lifetime ends. */
enum qcom_snps_hsphy_window_reason {
 QCOM_HSPHY_WINDOW_RUNTIME = 1, QCOM_HSPHY_WINDOW_SYSTEM = 2,
 QCOM_HSPHY_WINDOW_REMOVE = 4, QCOM_HSPHY_WINDOW_SHUTDOWN = 8,
};
struct qcom_snps_hsphy_window_binding {
 struct phy *phy;
 u64 provider_id, client_id;
 void *context;
};
struct qcom_snps_hsphy_window_client {
 void *context;
 /* Registration and each queued lifecycle callback hold real client refs.
  * get is nonblocking under registry; put may free, always outside locks. */
 bool (*get_unless_zero)(void *context);
 void (*put)(void *context);
 /* No provider registry/PHY lock is held; must publish abort and join.
  * Existing end is permitted until this callback returns. Return actual
  * restore error; forced withdrawal never calls that successful restoration. */
 int (*cancel_join)(void *context,
   const struct qcom_snps_hsphy_window_binding *binding,
   enum qcom_snps_hsphy_window_reason reason);
 /* Metadata notification only; no route/APSD permission or new epoch. */
 void (*complete)(void *context,
   const struct qcom_snps_hsphy_window_binding *binding);
};
int qcom_snps_hsphy_window_client_register(struct phy *phy,
 const struct qcom_snps_hsphy_window_client *client,
 struct qcom_snps_hsphy_window_binding *binding);
int qcom_snps_hsphy_window_client_unregister(struct qcom_snps_hsphy_window_binding *binding);

enum qcom_snps_hsphy_window_state {
	QCOM_HSPHY_WINDOW_IDLE,
	QCOM_HSPHY_WINDOW_CLAIMED,
	QCOM_HSPHY_WINDOW_HIGH_Z,
	QCOM_HSPHY_WINDOW_FAILED,
};
struct qcom_snps_hsphy_window_result {
	u64 cookie;
 u64 provider_id, client_id;
 bool provider_revoked;
 int lifecycle_error;
	enum qcom_snps_hsphy_window_state state;
	u32 saved[3]; /* masked old CTRL2, UTMI_CTRL0, CFG0, in entry order */
	u8 attempted, verified, restored_mask;
	bool high_z, restored;
	int enter_error, restore_error;
};
int qcom_snps_hsphy_window_begin(const struct qcom_snps_hsphy_window_binding *binding,
		struct qcom_snps_hsphy_window_result *result);
int qcom_snps_hsphy_window_end(const struct qcom_snps_hsphy_window_binding *binding, u64 cookie,
		struct qcom_snps_hsphy_window_result *result);
#endif
struct qcom_snps_hsphy {
	struct device *dev;

	struct phy *phy;
	void __iomem *base;

	int num_clks;
	struct clk_bulk_data *clks;
	struct reset_control *phy_reset;
	struct regulator_bulk_data vregs[SNPS_HS_NUM_VREGS];

	bool phy_initialized;
	struct qcom_snps_hsphy_window_result window;
	u64 window_generation;
	bool window_pm_ref;
 struct list_head window_node;
 struct completion window_operations_done, window_revoke_done, window_callbacks_done;
 struct mutex window_pm_stop_lock;
 bool window_pm_disabled;
 unsigned int window_operations, window_callbacks, window_blocked;
 bool window_published, window_dead, window_revoking, window_closing;
 u64 window_binding_id, window_client_id;
 int window_join_error;
 struct qcom_snps_hsphy_window_client window_client;
	enum phy_mode mode;
	struct phy_override_seq update_seq_cfg[NUM_HSPHY_TUNING_PARAMS];
};
