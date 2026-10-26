// SPDX-License-Identifier: GPL-2.0-only
/* Real paired producer arbitration, not an iomem-tree permission predicate. */
#include <linux/acpi.h>
#include <linux/atomic.h>
#include <linux/completion.h>
#include <linux/device.h>
#include <linux/firmware/samurai-eud-handoff.h>
#include <linux/io.h>
#include <linux/ioport.h>
#include <linux/kref.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/platform_device.h>
#include <linux/slab.h>
#include <linux/string.h>
#include "samurai-eud-route.h"

#define EUD_START 0x088e0000ULL
#define EUD_BYTES 0x2000ULL
#define DWC_START 0x0a600000ULL
struct samurai_eud_route_provider;
struct samurai_eud_producer { struct device *device; };
struct samurai_eud_route_client {
	struct kref ref;
	struct samurai_eud_route_provider *provider;
	struct samurai_eud_route_client_ops ops;
	struct device *consumer;
	void *context;
};
struct samurai_eud_route_provider {
	struct kref ref;
	struct mutex lock;
	struct completion joined;
	struct device *device;
	struct device_node *hardware, *consumer;
	struct samurai_eud_handoff handoff;
	struct samurai_eud_route_client *client;
	struct samurai_eud_route_lease *active;
	void __iomem *base;
	u64 binding, generation;
	bool attached, published, blocked, retired, joining, join_satisfied;
	bool region_owned, pm_prepared, pm_joining;
	int evidence_error, join_error, pm_error;
};
static DEFINE_MUTEX(route_registry);
static struct samurai_eud_producer *producer;
static struct samurai_eud_route_provider *route_provider;
static bool producer_ever_granted;
static bool early_producer_seen;
static atomic_t route_exclusive = ATOMIC_INIT(0);
static atomic_t boot_evidence_retired = ATOMIC_INIT(0);
static u64 route_binding;

/* Only the exclusive provider owns this mapping. Keep it through a failed
 * removal/join, and release before admitting another physical producer. */
static void route_unmap(struct samurai_eud_route_provider *p)
{
	if (p->base) {
		iounmap(p->base);
		p->base = NULL;
	}
	if (p->region_owned) {
		release_mem_region(EUD_START, EUD_BYTES);
		p->region_owned = false;
	}
}

int __init samurai_eud_earlycon_claim(phys_addr_t physical)
{
	if (physical > ~0ULL - (EUD_BYTES - 1))
		return -EINVAL;
	if (physical >= EUD_START + EUD_BYTES || physical + EUD_BYTES <= EUD_START)
		return 0;
	if (physical != EUD_START)
		return -EINVAL;
	if (atomic_read(&route_exclusive))
		return -EBUSY;
	WRITE_ONCE(early_producer_seen, true);
	smp_mb();
	return atomic_read(&route_exclusive) ? -EBUSY : 0;
}

int samurai_eud_producer_claim(struct platform_device *pdev, struct samurai_eud_producer **token)
{
	struct samurai_eud_producer *value;
	struct resource *resource;
	int ret = 0;

	if (!pdev || !token)
		return -EINVAL;
	*token = NULL;
	resource = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	if (!resource || resource->end < resource->start)
		return -EINVAL;
	if (resource->end < EUD_START || resource->start >= EUD_START + EUD_BYTES)
		return 0;
	if (resource->start != EUD_START || resource_size(resource) < EUD_BYTES)
		return -EINVAL;
	value = kzalloc(sizeof(*value), GFP_KERNEL);
	if (!value)
		return -ENOMEM;
	mutex_lock(&route_registry);
	if (producer || atomic_read(&route_exclusive))
		ret = -EBUSY;
	else {
		/* This history survives failed probe, release, UDC and provider rebind. */
		producer_ever_granted = true;
		value->device = get_device(&pdev->dev);
		producer = value;
		*token = value;
	}
	mutex_unlock(&route_registry);
	if (ret)
		kfree(value);
	return ret;
}
EXPORT_SYMBOL_GPL(samurai_eud_producer_claim);

void samurai_eud_producer_release(void *token)
{
	struct samurai_eud_producer *value = token;

	if (!value)
		return;
	mutex_lock(&route_registry);
	if (WARN_ON(producer != value)) {
		mutex_unlock(&route_registry);
		return;
	}
	producer = NULL;
	mutex_unlock(&route_registry);
	put_device(value->device);
	kfree(value);
}
EXPORT_SYMBOL_GPL(samurai_eud_producer_release);

static void route_provider_free(struct kref *ref)
{
	struct samurai_eud_route_provider *p = container_of(ref, struct samurai_eud_route_provider, ref);

	WARN_ON(p->published);
	WARN_ON(p->base || p->region_owned);
	of_node_put(p->hardware);
	of_node_put(p->consumer);
	put_device(p->device);
	mutex_destroy(&p->lock);
	kfree(p);
}

static void route_client_free(struct kref *ref)
{
	struct samurai_eud_route_client *c = container_of(ref, struct samurai_eud_route_client, ref);

	c->ops.put(c->context);
	put_device(c->consumer);
	kref_put(&c->provider->ref, route_provider_free);
	kfree(c);
}

/* Registry -> provider is the only nested order. Context puts/join are outside. */
static void route_unpublish_if_joined(struct samurai_eud_route_provider *p)
{
	bool drop = false;

	mutex_lock(&route_registry);
	mutex_lock(&p->lock);
	if (p->published && !p->attached && p->retired && !p->joining && p->join_satisfied && !p->active) {
		WARN_ON(route_provider != p);
		route_provider = NULL;
		p->published = false;
		route_unmap(p);
		atomic_set(&route_exclusive, 0);
		drop = true;
	}
	mutex_unlock(&p->lock);
	mutex_unlock(&route_registry);
	if (drop)
		kref_put(&p->ref, route_provider_free);
}

int samurai_eud_route_client_register(struct device *route, struct device *consumer,
		const struct samurai_eud_route_client_ops *ops, void *context,
		struct samurai_eud_route_client **client)
{
	struct samurai_eud_route_client *c;
	struct samurai_eud_route_provider *p;
	int ret = -ENODEV;

	if (!client)
		return -EINVAL;
	*client = NULL;
	if (!route || !consumer || !context || !ops || !ops->get_unless_zero || !ops->put || !ops->cancel_join)
		return -EINVAL;
	c = kzalloc(sizeof(*c), GFP_KERNEL);
	if (!c)
		return -ENOMEM;
	if (!ops->get_unless_zero(context)) {
		kfree(c);
		return -ESHUTDOWN;
	}
	kref_init(&c->ref);
	c->ops = *ops;
	c->context = context;
	mutex_lock(&route_registry);
	p = route_provider;
	if (p && p->device == route) {
		mutex_lock(&p->lock);
		if (p->blocked || p->retired || !p->attached)
			ret = -ESHUTDOWN;
		else if (p->pm_prepared)
			ret = -EAGAIN;
		else if (consumer->of_node != p->consumer || !device_is_registered(consumer))
			ret = -EXDEV;
		else if (p->client)
			ret = -EBUSY;
		else {
			kref_get(&p->ref);
			c->provider = p;
			c->consumer = get_device(consumer);
			p->client = c;
			*client = c;
			ret = 0;
		}
		mutex_unlock(&p->lock);
	}
	mutex_unlock(&route_registry);
	if (ret) {
		ops->put(context);
		kfree(c);
	}
	return ret;
}

int samurai_eud_route_client_unregister(struct samurai_eud_route_client *c)
{
	struct samurai_eud_route_provider *p;

	if (!c)
		return -EINVAL;
	p = c->provider;
	mutex_lock(&p->lock);
	if (p->client != c || p->active) {
		mutex_unlock(&p->lock);
		return -EBUSY;
	}
	p->client = NULL;
	/* A later unregister explicitly acknowledges the caller's joined users.
	 * Unregister inside a failing callback is not that later acknowledgement. */
	if (p->retired && !p->joining)
		p->join_satisfied = true;
	mutex_unlock(&p->lock);
	route_unpublish_if_joined(p);
	kref_put(&c->ref, route_client_free);
	return 0;
}

static int route_evidence_locked(struct samurai_eud_route_provider *p)
{
	struct samurai_eud_handoff fresh;
	int ret;

	ret = samurai_eud_handoff_copy(&fresh);
	if (!ret && memcmp(&fresh, &p->handoff, sizeof(fresh)))
		ret = -ESTALE;
	/* The handoff is necessary, but cannot establish post-sleep hardware
	 * state. Read only the same CSR used by the paired firmware/mainline
	 * driver; never touch FIFO/interrupt clear or write a route register. */
	if (!ret && (!p->base || !p->region_owned || !atomic_read(&route_exclusive)))
		ret = -ENODEV;
	if (!ret && (readl(p->base + 0x1014) != 0 || readl(p->base + 0x1014) != 0))
		ret = -EIO;
	if (ret) {
		p->blocked = true;
		p->evidence_error = ret;
		if (p->generation != ~0ULL)
			p->generation++;
		atomic_set(&boot_evidence_retired, 1);
	}
	return ret;
}

int samurai_eud_route_begin(struct samurai_eud_route_client *c, struct samurai_eud_route_lease *lease)
{
	struct samurai_eud_route_provider *p;
	int ret;

	if (!c || !lease)
		return -EINVAL;
	p = c->provider;
	mutex_lock(&p->lock);
	if (p->blocked || p->retired || !p->attached || !p->published)
		ret = -ESHUTDOWN;
	else if (p->pm_prepared)
		ret = -EAGAIN;
	else if (p->client != c || p->active || lease->client)
		ret = -EBUSY;
	else {
		ret = route_evidence_locked(p);
		if (!ret) {
			lease->client = c;
			lease->generation = p->generation;
			p->active = lease;
		}
	}
	mutex_unlock(&p->lock);
	return ret;
}

int samurai_eud_route_validate(const struct samurai_eud_route_lease *lease)
{
	struct samurai_eud_route_client *c;
	struct samurai_eud_route_provider *p;
	int ret;

	if (!lease || !lease->client)
		return -EINVAL;
	c = lease->client;
	p = c->provider;
	mutex_lock(&p->lock);
	if (p->blocked || p->retired || p->pm_prepared || !p->attached || !p->published ||
	    p->client != c || p->active != lease || lease->generation != p->generation)
		ret = -ESTALE;
	else
		ret = route_evidence_locked(p);
	mutex_unlock(&p->lock);
	return ret;
}

int samurai_eud_route_end(struct samurai_eud_route_lease *lease)
{
	struct samurai_eud_route_provider *p;

	if (!lease || !lease->client)
		return -EINVAL;
	p = lease->client->provider;
	mutex_lock(&p->lock);
	if (p->active != lease || p->client != lease->client) {
		mutex_unlock(&p->lock);
		return -ESTALE;
	}
	p->active = NULL;
	lease->client = NULL;
	lease->generation = 0;
	mutex_unlock(&p->lock);
	return 0;
}

int samurai_eud_route_status(struct samurai_eud_route_client *c, struct samurai_eud_route_status *status)
{
	struct samurai_eud_route_provider *p;

	if (!c || !status)
		return -EINVAL;
	p = c->provider;
	mutex_lock(&p->lock);
	*status = (struct samurai_eud_route_status) {
		.binding = p->binding, .generation = p->generation,
		.exclusive = p->published,
		.revoked = p->blocked || p->retired || !p->attached,
		.paused = p->pm_prepared,
		.evidence_error = p->evidence_error, .join_error = p->join_error,
		.pm_error = p->pm_error,
	};
	mutex_unlock(&p->lock);
	return 0;
}

static int route_retire(struct samurai_eud_route_provider *p)
{
	struct samurai_eud_route_client *c;
	int ret = 0;

	kref_get(&p->ref);
	mutex_lock(&p->lock);
	if (p->retired) {
		mutex_unlock(&p->lock);
		wait_for_completion(&p->joined);
		ret = p->join_error;
		kref_put(&p->ref, route_provider_free);
		return ret;
	}
	p->retired = p->blocked = p->joining = true;
	if (p->generation != ~0ULL)
		p->generation++;
	c = p->client;
	if (c)
		kref_get(&c->ref);
	mutex_unlock(&p->lock);
	if (c)
		ret = c->ops.cancel_join(c->context);
	mutex_lock(&p->lock);
	if (!ret && p->active)
		ret = -EBUSY;
	p->join_error = ret;
	p->join_satisfied = !ret;
	p->joining = false;
	mutex_unlock(&p->lock);
	if (c)
		kref_put(&c->ref, route_client_free);
	complete_all(&p->joined);
	kref_put(&p->ref, route_provider_free);
	return ret;
}

static int route_boot_profile(void)
{
	char *copy, *args, *name, *value;
	int ret = 0;

	if (!acpi_disabled || !of_chosen || of_property_present(of_chosen, "stdout-path") ||
	    of_property_present(of_chosen, "linux,stdout-path"))
		return -EOPNOTSUPP;
	copy = kstrdup(saved_command_line, GFP_KERNEL);
	if (!copy)
		return -ENOMEM;
	args = copy;
	while (*args) {
		args = next_arg(args, &name, &value);
		if (!strcmp(name, "--"))
			break;
		if (!strcmp(name, "earlycon") || !strcmp(name, "earlyprintk") ||
		    (!strcmp(name, "console") && value &&
		     (!strncmp(value, "uart", 4) || !strncmp(value, "eud", 3) || !strncmp(value, "ttyEUD", 6)))) {
			ret = -EOPNOTSUPP;
			break;
		}
	}
	kfree(copy);
	return ret;
}

static int route_probe(struct platform_device *pdev)
{
	struct samurai_eud_route_provider *p;
	struct resource hardware, consumer;
	int ret;

	if (!of_machine_is_compatible("realme,samurai"))
		return -ENODEV;
	ret = route_boot_profile();
	if (ret)
		return ret;
	p = kzalloc(sizeof(*p), GFP_KERNEL);
	if (!p)
		return -ENOMEM;
	kref_init(&p->ref);
	mutex_init(&p->lock);
	init_completion(&p->joined);
	p->device = get_device(&pdev->dev);
	p->hardware = of_parse_phandle(pdev->dev.of_node, "realme,eud-hardware", 0);
	p->consumer = of_parse_phandle(pdev->dev.of_node, "realme,usb-controller", 0);
	if (!p->hardware || !p->consumer || of_device_is_available(p->hardware) ||
	    (!of_device_is_compatible(p->hardware, "qcom,sm8150-eud-com") && !of_device_is_compatible(p->hardware, "qcom,eud")) ||
	    !of_device_is_compatible(p->consumer, "snps,dwc3") ||
	    of_address_to_resource(p->hardware, 0, &hardware) || of_address_to_resource(p->consumer, 0, &consumer) ||
	    hardware.start != EUD_START || resource_size(&hardware) < EUD_BYTES || consumer.start != DWC_START) {
		ret = -EINVAL;
		goto failed;
	}
	mutex_lock(&route_registry);
	if (route_provider || producer || producer_ever_granted || atomic_read(&boot_evidence_retired)) {
		ret = -EBUSY;
		goto unlock;
	}
	atomic_set(&route_exclusive, 1);
	smp_mb();
	if (READ_ONCE(early_producer_seen)) {
		ret = -EBUSY;
		goto release_exclusive;
	}
	ret = samurai_eud_handoff_copy(&p->handoff);
	if (ret)
		goto release_exclusive;
	if (!request_mem_region(EUD_START, EUD_BYTES, "samurai-eud-off-route")) {
		ret = -EBUSY;
		goto release_exclusive;
	}
	p->region_owned = true;
	p->base = ioremap(EUD_START, EUD_BYTES);
	if (!p->base) {
		ret = -ENOMEM;
		goto release_exclusive;
	}
	ret = route_evidence_locked(p);
	if (ret)
		goto release_exclusive;
	if (route_binding == ~0ULL) {
		ret = -EOVERFLOW;
		goto release_exclusive;
	}
	p->binding = ++route_binding;
	p->generation = 1;
	p->attached = p->published = true;
	kref_get(&p->ref); /* Independent publication survives failed remove/join. */
	route_provider = p;
	platform_set_drvdata(pdev, p);
	mutex_unlock(&route_registry);
	return 0;
release_exclusive:
	route_unmap(p);
	atomic_set(&route_exclusive, 0);
unlock:
	mutex_unlock(&route_registry);
failed:
	kref_put(&p->ref, route_provider_free);
	return ret;
}

static void route_remove(struct platform_device *pdev)
{
	struct samurai_eud_route_provider *p = platform_get_drvdata(pdev);
	int ret = route_retire(p);

	mutex_lock(&p->lock);
	p->attached = false;
	mutex_unlock(&p->lock);
	platform_set_drvdata(pdev, NULL);
	route_unpublish_if_joined(p);
	if (ret)
		dev_warn(&pdev->dev, "EUD route retained after failed client join: %d\n", ret);
	kref_put(&p->ref, route_provider_free);
}

static void route_shutdown(struct platform_device *pdev)
{
	struct samurai_eud_route_provider *p = platform_get_drvdata(pdev);
	int ret = route_retire(p);

	if (ret)
		dev_warn(&pdev->dev, "EUD route shutdown join failed: %d\n", ret);
}

static int route_prepare(struct device *device)
{
	struct samurai_eud_route_provider *p = dev_get_drvdata(device);
	struct samurai_eud_route_client *c = NULL;
	int ret = 0;
	bool retire = false, already = false;

	kref_get(&p->ref);
	mutex_lock(&p->lock);
	if (p->pm_prepared) {
		ret = p->pm_error;
		already = true;
		goto unlock;
	}
	if (p->retired || p->blocked ||
	    (p->client && (!p->client->ops.pause_join || !p->client->ops.resume))) {
		retire = true;
		goto unlock;
	}
	if (p->generation == ~0ULL) {
		ret = -EOVERFLOW;
		retire = true;
		goto unlock;
	}
	p->pm_prepared = p->pm_joining = true;
	p->generation++; /* Revoke every pre-sleep lease before joining work. */
	c = p->client;
	if (c)
		kref_get(&c->ref);
unlock:
	mutex_unlock(&p->lock);
	if (already)
		goto out;
	if (retire) {
		atomic_set(&boot_evidence_retired, 1);
		ret = route_retire(p) ?: ret;
		goto out;
	}
	if (!c)
		goto joined;
	ret = c->ops.pause_join(c->context);
joined:
	mutex_lock(&p->lock);
	if (!ret && p->active)
		ret = -EBUSY;
	p->pm_joining = false;
	p->pm_error = ret;
	if (ret) {
		p->blocked = true;
		atomic_set(&boot_evidence_retired, 1);
	}
	mutex_unlock(&p->lock);
	if (c)
		kref_put(&c->ref, route_client_free);
out:
	kref_put(&p->ref, route_provider_free);
	return ret;
}

static void route_complete(struct device *device)
{
	struct samurai_eud_route_provider *p = dev_get_drvdata(device);
	struct samurai_eud_route_client *c = NULL;
	int ret = 0;

	kref_get(&p->ref);
	mutex_lock(&p->lock);
	if (!p->pm_prepared || p->pm_joining)
		goto unlock;
	if (p->blocked || p->retired || !p->attached || !p->published)
		goto expired;
	ret = p->active ? -EBUSY : route_evidence_locked(p);
	if (ret) {
		p->blocked = true;
		p->pm_error = ret;
		atomic_set(&boot_evidence_retired, 1);
		goto expired;
	}
	c = p->client;
	if (c)
		kref_get(&c->ref);
expired:
	p->pm_prepared = false;
unlock:
	mutex_unlock(&p->lock);
	if (c) {
		c->ops.resume(c->context);
		kref_put(&c->ref, route_client_free);
	}
	if (ret)
		dev_warn(device, "EUD route remains blocked after sleep: %d\n", ret);
	kref_put(&p->ref, route_provider_free);
}

static const struct dev_pm_ops route_pm = {
	.prepare = pm_sleep_ptr(route_prepare),
	.complete = pm_sleep_ptr(route_complete),
};
static const struct of_device_id route_match[] = {
	{ .compatible = "realme,rmx1931-eud-off-route" }, { }
};
static struct platform_driver route_driver = {
	.probe = route_probe, .remove = route_remove, .shutdown = route_shutdown,
	.driver = { .name = "samurai-eud-off-route", .of_match_table = route_match,
		.pm = pm_sleep_ptr(&route_pm), .suppress_bind_attrs = true },
};
static int __init route_init(void) { return platform_driver_register(&route_driver); }
subsys_initcall(route_init);
MODULE_LICENSE("GPL");
