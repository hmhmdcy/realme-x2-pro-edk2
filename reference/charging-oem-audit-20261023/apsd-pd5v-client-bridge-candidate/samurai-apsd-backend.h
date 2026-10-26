/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_USB_SAMURAI_APSD_BACKEND_H
#define _LINUX_USB_SAMURAI_APSD_BACKEND_H

#include <linux/device.h>
#include <linux/errno.h>
#include <linux/kconfig.h>
#include <linux/types.h>

/* Transport only. No callback grants PD, sink, route or component lifetime.
 * raw order: apsd/result/plugin/cc/attached/misc/legacy, at the R7 addresses
 * 1307/1308/1310/1506/1509/150b/150d respectively.
 * A successful read is TWO new equal physical reads under input->lock.
 * serial is nonzero, strictly increasing for this registered instance;
 * present is 0/1 only for proved all-off/all-on; mixed states return EAGAIN.
 */
struct samurai_apsd_bus_sample {
	u64 serial;
	u8 raw[7];
	bool present;
};

struct samurai_apsd_bus_ops {
	int (*read_sample)(void *ctx, struct samurai_apsd_bus_sample *sample);
	/* Exactly ONE physical 1341 bit0 masked transfer, even if already set.
	 * Consume this epoch before transfer; error/unknown consumes it too.
	 * Do not retry, synthesize DONE, or change any source/current policy.
	 * Return actual transfer errno. Epoch must be nonzero and nonreused.
	 */
	int (*rerun_once)(void *ctx, u64 epoch);
};

/* Sleepable process context, outside input->lock/PM/IRQ/component locks.
 * unregister withdraws the provider and synchronously cancels/joins all
 * owner callbacks BEFORE source devres/MMIO/regmap teardown. A device ref
 * or module ref alone is NOT this bound lifetime guarantee.
 * One provider only. Missing owner configuration never enables anything.
 */
#if IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_OWNER)
int samurai_apsd_bus_register(struct device *dev,
		const struct samurai_apsd_bus_ops *ops, void *ctx);
void samurai_apsd_bus_unregister(struct device *dev, void *ctx);
#else
static inline int samurai_apsd_bus_register(struct device *dev,
		const struct samurai_apsd_bus_ops *ops, void *ctx)
{
	return -EOPNOTSUPP;
}
static inline void samurai_apsd_bus_unregister(struct device *dev, void *ctx)
{
}
#endif
#endif
