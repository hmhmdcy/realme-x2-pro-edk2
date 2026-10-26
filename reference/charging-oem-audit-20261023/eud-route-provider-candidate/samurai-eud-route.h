/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SAMURAI_EUD_ROUTE_H
#define SAMURAI_EUD_ROUTE_H
#include <linux/errno.h>
#include <linux/init.h>
#include <linux/kconfig.h>
#include <linux/stddef.h>
#include <linux/types.h>
struct device;
struct platform_device;
struct samurai_eud_producer;
struct samurai_eud_route_client;
struct samurai_eud_route_lease {
	struct samurai_eud_route_client *client;
	u64 generation;
};
struct samurai_eud_route_client_ops {
	bool (*get_unless_zero)(void *context);
	void (*put)(void *context);
	int (*cancel_join)(void *context);
};
struct samurai_eud_route_status {
	u64 binding, generation;
	bool exclusive, revoked;
	int evidence_error, join_error;
};

/* Every paired EUD producer enters before its first MMIO/SCM access and
 * releases only after its final producer/devres teardown. Earlycon uses the
 * allocation-free early entry. No absent-provider result grants a route.
 */
#if IS_ENABLED(CONFIG_QCOM_SAMURAI_EUD_ROUTE)
int samurai_eud_producer_claim(struct platform_device *pdev, struct samurai_eud_producer **token);
void samurai_eud_producer_release(void *token);
int __init samurai_eud_earlycon_claim(phys_addr_t physical);
int samurai_eud_route_client_register(struct device *route, struct device *consumer,
	const struct samurai_eud_route_client_ops *ops, void *context,
	struct samurai_eud_route_client **client);
/* Caller joins all API users and ends its active lease before unregister. */
int samurai_eud_route_client_unregister(struct samurai_eud_route_client *client);
int samurai_eud_route_begin(struct samurai_eud_route_client *client, struct samurai_eud_route_lease *lease);
int samurai_eud_route_validate(const struct samurai_eud_route_lease *lease);
int samurai_eud_route_end(struct samurai_eud_route_lease *lease);
int samurai_eud_route_status(struct samurai_eud_route_client *client, struct samurai_eud_route_status *status);
#else
static inline int samurai_eud_producer_claim(struct platform_device *pdev, struct samurai_eud_producer **token)
{
	if (token)
		*token = NULL;
	return 0; /* Disabled arbiter preserves the original producer behavior. */
}
static inline void samurai_eud_producer_release(void *token) { }
static inline int samurai_eud_earlycon_claim(phys_addr_t physical) { return 0; }
static inline int samurai_eud_route_client_register(struct device *route, struct device *consumer,
	const struct samurai_eud_route_client_ops *ops, void *context, struct samurai_eud_route_client **client)
{
	if (client)
		*client = NULL;
	return -EOPNOTSUPP;
}
static inline int samurai_eud_route_client_unregister(struct samurai_eud_route_client *client) { return -EOPNOTSUPP; }
static inline int samurai_eud_route_begin(struct samurai_eud_route_client *client, struct samurai_eud_route_lease *lease) { return -EOPNOTSUPP; }
static inline int samurai_eud_route_validate(const struct samurai_eud_route_lease *lease) { return -EOPNOTSUPP; }
static inline int samurai_eud_route_end(struct samurai_eud_route_lease *lease) { return -EOPNOTSUPP; }
static inline int samurai_eud_route_status(struct samurai_eud_route_client *client, struct samurai_eud_route_status *status) { return -EOPNOTSUPP; }
#endif
#endif
