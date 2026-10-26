/* SPDX-License-Identifier: GPL-2.0 */
#ifndef QCOM_SNPS_FEMTO_V2_WINDOW_H
#define QCOM_SNPS_FEMTO_V2_WINDOW_H
#include <linux/types.h>
struct phy;

/* Internal same-Image interface; no exported module symbol or UAPI. The
 * caller owns the bound PHY lifetime and a successful active DWC HALT window
 * through end; it must cancel/join its work before UDC/PHY removal. */
enum qcom_snps_hsphy_window_state {
	QCOM_HSPHY_WINDOW_IDLE,
	QCOM_HSPHY_WINDOW_CLAIMED,
	QCOM_HSPHY_WINDOW_HIGH_Z,
	QCOM_HSPHY_WINDOW_FAILED,
};
struct qcom_snps_hsphy_window_result {
	u64 cookie;
	enum qcom_snps_hsphy_window_state state;
	u32 saved[3]; /* masked old CTRL2, UTMI_CTRL0, CFG0, in entry order */
	u8 attempted, verified, restored_mask;
	bool high_z, restored;
	int enter_error, restore_error;
};
int qcom_snps_hsphy_window_begin(struct phy *phy,
		struct qcom_snps_hsphy_window_result *result);
int qcom_snps_hsphy_window_end(struct phy *phy, u64 cookie,
		struct qcom_snps_hsphy_window_result *result);
#endif
