/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _QCOM_PM8008_IMX319_LAB_H
#define _QCOM_PM8008_IMX319_LAB_H

#include <linux/bitops.h>
#include <linux/mutex.h>
#include <linux/types.h>

struct device;
struct regmap;

#define PM8008_IMX319_LAB_MAGIC 0x80081931U
#define PM8008_IMX319_LAB_MASK (BIT(0) | BIT(3))

/* Owned by the P MFD epoch, never reinitialized by the regulator child. */
struct pm8008_imx319_lab_state {
	u32 magic;
	struct device *parent;
	struct regmap *primary;
	struct regmap *secondary;
	unsigned long mask;
	struct mutex lock;
	int (*assert_p_reset)(void *cookie);
	void *reset_cookie;
	bool reset_held;
	bool reset_attempted;
	int reset_error;
	bool fault;
	bool claimed;
	bool ready;
	bool removing;
	bool global_initialized;
	bool global_original;
	bool global_attempted;
	unsigned long attempted_mask;
	unsigned long enabled_mask;
};

/* MFD copies this pointer wrapper, never the state or its mutex. */
struct pm8008_imx319_lab_data {
	struct pm8008_imx319_lab_state *state;
};
#endif
