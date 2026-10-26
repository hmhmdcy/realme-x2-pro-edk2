// SPDX-License-Identifier: GPL-2.0-only
/* Samurai BC1.2 -> full TCPM exclusion. Detached-epoch rearm is not yet
 * implemented. This code never disables PD or restricts the sink PDOs.
 */
#include <linux/bitops.h>
#include <linux/delay.h>
#include <linux/device.h>
#include <linux/err.h>
#include <linux/ktime.h>
#include <linux/mutex.h>
#include <linux/regmap.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/usb/samurai-tcpm-apsd.h>
#include "qcom_pmic_typec_apsd.h"

#define USBIN_OPTIONS_1 0x1362
#define APSD_ENABLE BIT(3)
#define HVDCP_AUTH_AUTONOMOUS_ENABLE 0x64
#define USBIN_OPTIONS_2 0x1358
#define APSD_START_ON_CC BIT(7)
#define HANDOFF_STABLE_MS 20
#define HANDOFF_FRESH_MS 250

struct qcom_pmic_typec_apsd {
	struct device *dev;
	struct regmap *map;
	struct mutex lock;
	bool prepared;
	int error;
};

static const unsigned int off_regs[] = { 0x1310, 0x1509, 0x150a, 0x150b };
static const struct { unsigned int reg, mask; } isolation[] = {
	{ USBIN_OPTIONS_1, APSD_ENABLE | HVDCP_AUTH_AUTONOMOUS_ENABLE },
	{ USBIN_OPTIONS_2, APSD_START_ON_CC },
};

/* A real off is required for this first candidate's initial takeover.
 * Neither get_vbus(false), stale ONLINE nor absence of a contract proves
 * vSafe0V. The Type-C bit and all four physical presence bits must agree.
 * A connected/inherited 5V/9V/QC source is refused, not renegotiated here.
 */
static int apsd_read_off(struct qcom_pmic_typec_apsd *h, unsigned int *s)
{
	s64 start = ktime_to_ms(ktime_get_boottime()), elapsed;
	unsigned int i;
	int ret;

	for (i = 0; i < ARRAY_SIZE(off_regs); i++) {
		ret = regmap_read(h->map, off_regs[i], &s[i]);
		if (ret)
			return ret;
	}
	elapsed = ktime_to_ms(ktime_get_boottime()) - start;
	if (elapsed < 0 || elapsed > HANDOFF_FRESH_MS)
		return -EAGAIN;
	if ((s[0] & BIT(4)) || (s[1] & BIT(5)) ||
	    (s[3] & (BIT(5) | BIT(0))) ||
	    !(s[2] & BIT(6)) || (s[2] & BIT(5)))
		return -EAGAIN;
	return 0;
}

static int apsd_verify_locked(struct qcom_pmic_typec_apsd *h)
{
	unsigned int i, value;
	int ret;

	for (i = 0; i < ARRAY_SIZE(isolation); i++) {
		ret = regmap_read(h->map, isolation[i].reg, &value);
		if (ret)
			return ret;
		if (value & isolation[i].mask)
			return -EUCLEAN;
	}
	return 0;
}

static void apsd_release(void *data)
{
	struct qcom_pmic_typec_apsd *h = data;

	/* Called by real Type-C devres after remove/probe error unwinding.
	 * No worker uses h: only the original bound Type-C callbacks do.
	 * Keep isolation/fence on every failure and through removal.
	 */
	samurai_apsd_tcpm_release(h->dev);
}

struct qcom_pmic_typec_apsd *
qcom_pmic_typec_apsd_prepare(struct device *dev, struct regmap *map)
{
	struct qcom_pmic_typec_apsd *h;
	unsigned int first[ARRAY_SIZE(off_regs)], fresh[ARRAY_SIZE(off_regs)];
	unsigned int i, value;
	int ret;

	if (!dev || !map)
		return ERR_PTR(-EINVAL);
	h = devm_kzalloc(dev, sizeof(*h), GFP_KERNEL);
	if (!h)
		return ERR_PTR(-ENOMEM);
	h->dev = dev;
	h->map = map;
	mutex_init(&h->lock);
	/* Join before holding h->lock, and before any TCPM port exists.
	 * The owner may need input->lock to finish the original rerun.
	 */
	ret = samurai_apsd_tcpm_quiesce(dev, map);
	if (ret)
		return ERR_PTR(ret);
	ret = devm_add_action_or_reset(dev, apsd_release, h);
	if (ret)
		return ERR_PTR(ret);
	ret = apsd_read_off(h, first);
	if (ret)
		return ERR_PTR(ret);
	/* Engineering debounce only; not presented as an OEM timing value. */
	msleep(HANDOFF_STABLE_MS);
	ret = apsd_read_off(h, fresh);
	if (ret || memcmp(first, fresh, sizeof(first)))
		return ERR_PTR(ret ? ret : -EAGAIN);
	for (i = 0; i < ARRAY_SIZE(isolation); i++) {
		ret = apsd_read_off(h, fresh);
		if (ret || memcmp(first, fresh, sizeof(first))) {
			ret = ret ? ret : -ESTALE;
			goto failed;
		}
		/* OEM narrow masks only. No PMIC battery-charger, DP/DM voltage,
		 * CC role, sink FET, protection, OTP or NV writes.
		 */
		ret = regmap_update_bits(map, isolation[i].reg, isolation[i].mask, 0);
		if (ret)
			goto failed;
		ret = regmap_read(map, isolation[i].reg, &value);
		if (ret || (value & isolation[i].mask)) {
			ret = ret ? ret : -EUCLEAN;
			goto failed;
		}
		ret = apsd_read_off(h, fresh);
		if (ret || memcmp(first, fresh, sizeof(first))) {
			ret = ret ? ret : -ESTALE;
			goto failed;
		}
	}
	h->prepared = true;
	return h;
failed:
	h->error = ret;
	return ERR_PTR(ret);
}

int qcom_pmic_typec_apsd_verify(struct qcom_pmic_typec_apsd *h)
{
	int ret;

	if (!h)
		return 0;
	mutex_lock(&h->lock);
	ret = h->error ? h->error : h->prepared ? apsd_verify_locked(h) : -EAGAIN;
	/* Unknown read/error or externally changed isolation never repairs itself
	 * while a live TCPM connection may exist. RX-off never changes this state.
	 */
	if (ret)
		h->error = ret;
	mutex_unlock(&h->lock);
	return ret;
}
