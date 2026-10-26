/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_USB_SAMURAI_TCPM_APSD_H
#define _LINUX_USB_SAMURAI_TCPM_APSD_H
#include <linux/errno.h>
#include <linux/kconfig.h>
struct device;
struct regmap;

/* Internal bound-driver lifecycle, not a permission token. Call BEFORE
 * tcpm_register_port()/PHY startup, with no TCPM, input or notifier lock held.
 * Publishes an irreversible fence for this boot before joining the actual
 * APSD owner. Future owner/backend bindings inherit the same fence.
 * release drops the supplier device reference; it never reopens APSD.
 * A future detached-epoch rearm implementation must replace that restriction.
 */
#if IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_OWNER)
int samurai_apsd_tcpm_quiesce(struct device *typec, struct regmap *map);
void samurai_apsd_tcpm_release(struct device *typec);
#else
static inline int samurai_apsd_tcpm_quiesce(struct device *typec,
					struct regmap *map)
{
	return -EOPNOTSUPP;
}
static inline void samurai_apsd_tcpm_release(struct device *typec) {}
#endif
#endif
