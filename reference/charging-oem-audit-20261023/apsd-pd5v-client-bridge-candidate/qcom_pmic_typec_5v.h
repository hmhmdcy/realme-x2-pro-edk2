/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef QCOM_PMIC_TYPEC_5V_H
#define QCOM_PMIC_TYPEC_5V_H
#include <linux/types.h>

struct device;
struct regmap;
struct samurai_pd5v;

/* Internal, same-Image interface. No UAPI or EXPORT_SYMBOL. */
struct samurai_pd5v_client {
	void *context;
	/* Mandatory real lifetime operations, not a permission predicate.
	 * get_unless_zero is nonblocking, nonreentrant and holds context AND
	 * callback code/data alive until put. Called under the PD5V mutex.
	 * put may destroy the context and is always called outside that mutex. */
	bool (*get_unless_zero)(void *context);
	void (*put)(void *context);
	/* Must stop and join the client's work, including release of its lease.
	 * Called without the PD5V mutex or a TCPM/IRQ lock held, with its own
	 * extra context reference. It may release its lease synchronously. */
	void (*cancel_join)(void *context);
};
struct samurai_pd5v_lease {
	struct samurai_pd5v *owner;
	unsigned long long generation;
};

struct samurai_pd5v *samurai_pd5v_create(struct device *dev,
					struct regmap *regmap);
void samurai_pd5v_destroy(struct samurai_pd5v *owner);
int samurai_pd5v_quiesce(struct samurai_pd5v *owner);
void samurai_pd5v_complete(struct samurai_pd5v *owner);

/* First acquisition must observe a real, stable detach/vSafe0V. It performs
 * the single disabling transaction. No automatic poll, retry or role write.
 * Later acquisition only verifies the retained disabled state; it cannot
 * recreate an inherited-contract epoch or repair a failed transaction. */
int samurai_pd5v_validate(const struct samurai_pd5v_lease *lease);
void samurai_pd5v_release(struct samurai_pd5v_lease *lease);

/* Resolves only a currently bound, opted-in instance of the real qcom
 * platform driver. Caller supplies the actual Type-C device, not a label.
 * A successful lease proves PD disabled, not DP/DM route or APSD permission. */
/* Metadata only: not a lease or PD permission. Exact source/Type-C parent
 * and regmap identity are checked. No physical I/O or supply operation.
 * binding_id never reuses a removed instance's identity. */
struct samurai_pd5v_status {
 unsigned long long binding_id;
 bool initialized, blocked;
 int error;
};
int qcom_pmic_typec_5v_status(struct device *typec, struct device *source,
 struct samurai_pd5v_status *status);
int qcom_pmic_typec_5v_acquire(struct device *typec,
		const struct samurai_pd5v_client *client,
		struct samurai_pd5v_lease *lease);
#endif
