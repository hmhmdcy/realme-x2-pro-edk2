/* SPDX-License-Identifier: GPL-2.0 */
#ifndef QCOM_SNPS_FEMTO_V2_WINDOW_H
#define QCOM_SNPS_FEMTO_V2_WINDOW_H
#include <linux/types.h>
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
