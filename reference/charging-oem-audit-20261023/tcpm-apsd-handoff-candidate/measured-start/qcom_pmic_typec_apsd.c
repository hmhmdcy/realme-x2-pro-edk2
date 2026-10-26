// SPDX-License-Identifier: GPL-2.0-only
/* Offline revision: true-off OR measured connected 5V, then APSD/QC -> TCPM.
 * Detached-epoch APSD rearm remains outside this single-direction component.
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
/* Same engineering acceptance window as full-PD shutdown. ADC calibration
 * and physical accuracy still require board validation, not unit inference.
 */
#define HANDOFF_MIN_UV 4750000
#define HANDOFF_MAX_UV 5500000

struct qcom_pmic_typec_apsd {
	struct device *dev;
	struct regmap *map;
	struct mutex lock;
	struct qcom_pmic_typec_apsd_start_ops ops;
	void *context;
	bool prepared, quiet_attempted;
	int error, release_error;
};

static const unsigned int off_regs[] = { 0x1310, 0x1509, 0x150a, 0x150b };
static const unsigned int sink_regs[] = {
	0x1307, 0x1308, 0x1310, 0x1506, 0x1509, 0x150b, 0x150d, 0x150a, 0x1362,
};
static const struct { unsigned int reg, mask; } isolation[] = {
	{ USBIN_OPTIONS_1, APSD_ENABLE | HVDCP_AUTH_AUTONOMOUS_ENABLE },
	{ USBIN_OPTIONS_2, APSD_START_ON_CC },
};
struct apsd_start_sample {
	bool connected;
	unsigned int off[ARRAY_SIZE(off_regs)], sink[ARRAY_SIZE(sink_regs)];
	int vbus_uv;
};

/* Preserve the original real-off path: no ADC or powered PD read needed. */
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
		return -ENOLINK;
	return 0;
}

static int apsd_read_sink(struct qcom_pmic_typec_apsd *h, unsigned int *s)
{
	unsigned int i, cc;
	int ret;

	for (i = 0; i < ARRAY_SIZE(sink_regs); i++) {
		ret = regmap_read(h->map, sink_regs[i], &s[i]);
		if (ret)
			return ret;
	}
	cc = s[3] & 0x7f;
	/* Exact existing native sink-role predicates, plus actual comparator
	 * status. ONLINE/APSD completion/current allowance are not consulted.
	 */
	if (!(s[2] & 0x10) || (s[2] & 0x2f) || !(s[4] & 0x20) ||
	    (s[5] & 0x21) != 0x21 || (s[5] & 0xd0) || !(s[5] & 8) ||
	    (s[6] & 1) || (cc != 8 && cc != 4 && cc != 2) ||
	    !(s[7] & 0x20) || (s[7] & 0x40))
		return -EAGAIN;
	/* Completed/active proprietary detection, or enabled autonomous QC,
	 * is not permission to adopt the source as plain 5V. Never lower it.
	 */
	if ((s[0] & 2) || (s[1] & 0x60) || (s[8] & 0x64))
		return -EBUSY;
	return 0;
}

static bool apsd_same_sink(const unsigned int *a, const unsigned int *b)
{
	/* Physical presence, Rp, role, legacy and comparator status must remain
	 * identical. APSD DONE/non-QC result may progress while we take over.
	 */
	return !memcmp(a + 2, b + 2, 6 * sizeof(*a));
}

static int apsd_read_start(struct qcom_pmic_typec_apsd *h,
			 struct apsd_start_sample *sample, bool require_quiet)
{
	unsigned int before[ARRAY_SIZE(sink_regs)];
	s64 start, elapsed;
	int ret;

	memset(sample, 0, sizeof(*sample));
	ret = apsd_read_off(h, sample->off);
	if (!ret)
		return 0;
	if (ret != -ENOLINK)
		return ret;
	start = ktime_to_ms(ktime_get_boottime());
	ret = apsd_read_sink(h, before);
	if (ret)
		return ret;
	if (!h->context || !h->ops.read_vbus_uv || !h->ops.quiet_begin ||
	    !h->ops.quiet_verify || !h->ops.quiet_release)
		return -EOPNOTSUPP;
	ret = h->ops.read_vbus_uv(h->context, &sample->vbus_uv);
	if (ret)
		return ret;
	if (sample->vbus_uv < HANDOFF_MIN_UV || sample->vbus_uv > HANDOFF_MAX_UV)
		return -ERANGE;
	if (require_quiet) {
		ret = h->ops.quiet_verify(h->context);
		if (ret)
			return ret;
	}
	ret = apsd_read_sink(h, sample->sink);
	if (ret)
		return ret;
	elapsed = ktime_to_ms(ktime_get_boottime()) - start;
	if (elapsed < 0 || elapsed > HANDOFF_FRESH_MS)
		return -EAGAIN;
	if (!apsd_same_sink(before, sample->sink))
		return -ESTALE;
	sample->connected = true;
	return 0;
}

static bool apsd_same_start(const struct apsd_start_sample *a,
			    const struct apsd_start_sample *b)
{
	if (a->connected != b->connected)
		return false;
	return a->connected ? apsd_same_sink(a->sink, b->sink) :
		!memcmp(a->off, b->off, sizeof(a->off));
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

static int apsd_drop_quiet(struct qcom_pmic_typec_apsd *h)
{
	int ret;

	if (!h->quiet_attempted)
		return 0;
	ret = h->ops.quiet_release(h->context);
	h->release_error = ret;
	if (!ret)
		h->quiet_attempted = false;
	return ret;
}

static void apsd_release(void *data)
{
	struct qcom_pmic_typec_apsd *h = data;
	int ret = apsd_drop_quiet(h);

	/* A started PHY already consumed this same supply reference. Its
	 * original joined stop/finish sequence owns it, not this devres action.
	 */
	if (ret)
		dev_err(h->dev, "pre-start PD PHY release failed: %d\n", ret);
	samurai_apsd_tcpm_release(h->dev);
}

struct qcom_pmic_typec_apsd *qcom_pmic_typec_apsd_prepare(
	struct device *dev, struct regmap *map,
	const struct qcom_pmic_typec_apsd_start_ops *ops, void *context)
{
	struct qcom_pmic_typec_apsd *h;
	struct apsd_start_sample first, fresh;
	unsigned int i, value;
	int ret;

	if (!dev || !map)
		return ERR_PTR(-EINVAL);
	h = devm_kzalloc(dev, sizeof(*h), GFP_KERNEL);
	if (!h)
		return ERR_PTR(-ENOMEM);
	h->dev = dev;
	h->map = map;
	if (ops)
		h->ops = *ops;
	h->context = context;
	mutex_init(&h->lock);
	/* No helper, input, port or notifier lock held; no TCPM port yet. */
	ret = samurai_apsd_tcpm_quiesce(dev, map);
	if (ret)
		return ERR_PTR(ret);
	ret = devm_add_action_or_reset(dev, apsd_release, h);
	if (ret)
		return ERR_PTR(ret);
	ret = apsd_read_start(h, &first, false);
	if (ret)
		goto failed;
	msleep(HANDOFF_STABLE_MS);
	ret = apsd_read_start(h, &fresh, false);
	if (ret || !apsd_same_start(&first, &fresh)) {
		ret = ret ? ret : -EAGAIN;
		goto failed;
	}
	if (first.connected) {
		/* The callback itself acquires the real regulator reference and
		 * reads existing controls, without reset/enabling PD or old-value
		 * replay. It cannot run before these measured 5V/sink prechecks.
		 */
		h->quiet_attempted = true;
		ret = h->ops.quiet_begin(context);
		if (ret)
			goto failed;
	}
	for (i = 0; i < ARRAY_SIZE(isolation); i++) {
		ret = apsd_read_start(h, &fresh, first.connected);
		if (ret || !apsd_same_start(&first, &fresh)) {
			ret = ret ? ret : -ESTALE;
			goto failed;
		}
		ret = regmap_update_bits(map, isolation[i].reg, isolation[i].mask, 0);
		if (ret)
			goto failed;
		ret = regmap_read(map, isolation[i].reg, &value);
		if (ret || (value & isolation[i].mask)) {
			ret = ret ? ret : -EUCLEAN;
			goto failed;
		}
		ret = apsd_read_start(h, &fresh, first.connected);
		if (ret || !apsd_same_start(&first, &fresh)) {
			ret = ret ? ret : -ESTALE;
			goto failed;
		}
	}
	h->prepared = true;
	return h;
failed:
	h->error = ret;
	/* Preserve the original ADC/source/control errno, and independently
	 * retain release_error/real powered state if regulator_disable fails.
	 */
	apsd_drop_quiet(h);
	return ERR_PTR(ret);
}

int qcom_pmic_typec_apsd_verify(struct qcom_pmic_typec_apsd *h)
{
	int ret;

	if (!h)
		return 0;
	mutex_lock(&h->lock);
	ret = h->error ? h->error : h->prepared ? apsd_verify_locked(h) : -EAGAIN;
	if (ret)
		h->error = ret;
	mutex_unlock(&h->lock);
	return ret;
}
