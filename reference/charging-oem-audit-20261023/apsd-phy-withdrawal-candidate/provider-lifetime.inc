/* Registry protects publication only. Provider lock protects bound storage;
 * no client callback runs under either it or the generic PHY mutex. */
struct qcom_hsphy_window_provider;
struct qcom_snps_hsphy_window_client {
	struct kref ref;
	struct qcom_hsphy_window_provider *provider;
	struct qcom_snps_hsphy_window_client_ops ops;
	void *context;
};
struct qcom_hsphy_window_provider {
	struct list_head node;
	struct kref ref;
	struct mutex lock;
	struct completion withdrawn;
	struct phy *key; /* compare only under registry; never dereference */
	struct qcom_snps_hsphy *bound;
	struct qcom_snps_hsphy_window_client *client;
	struct qcom_snps_hsphy_window_result receipt;
	bool withdrawing, dead;
	int withdraw_error;
};
static LIST_HEAD(qcom_hsphy_window_providers);
static DEFINE_MUTEX(qcom_hsphy_window_registry);

static void qcom_hsphy_window_provider_free(struct kref *ref)
{
	struct qcom_hsphy_window_provider *p = container_of(ref,
		struct qcom_hsphy_window_provider, ref);
	mutex_destroy(&p->lock);
	kfree(p);
}

static void qcom_hsphy_window_client_free(struct kref *ref)
{
	struct qcom_snps_hsphy_window_client *c = container_of(ref,
		struct qcom_snps_hsphy_window_client, ref);
	/* Context release can destroy the owner; always outside component locks. */
	c->ops.put(c->context);
	kref_put(&c->provider->ref, qcom_hsphy_window_provider_free);
	kfree(c);
}

int qcom_snps_hsphy_window_client_register(struct phy *phy,
		const struct qcom_snps_hsphy_window_client_ops *ops, void *context,
		struct qcom_snps_hsphy_window_client **client)
{
	struct qcom_snps_hsphy_window_client *c;
	struct qcom_hsphy_window_provider *p;
	int ret = -ENODEV;

	if (!client)
		return -EINVAL;
	*client = NULL;
	if (!phy || !ops || !ops->get_unless_zero || !ops->put || !ops->cancel_join)
		return -EINVAL;
	c = kzalloc(sizeof(*c), GFP_KERNEL);
	if (!c)
		return -ENOMEM;
	/* Pins callback code/data until final client or withdrawal callback put. */
	if (!ops->get_unless_zero(context)) {
		kfree(c);
		return -ESHUTDOWN;
	}
	kref_init(&c->ref);
	c->ops = *ops;
	c->context = context;
	mutex_lock(&qcom_hsphy_window_registry);
	list_for_each_entry(p, &qcom_hsphy_window_providers, node) {
		if (p->key != phy)
			continue;
		mutex_lock(&p->lock);
		if (p->withdrawing || p->dead)
			ret = -ESHUTDOWN;
		else if (p->client)
			ret = -EBUSY;
		else {
			kref_get(&p->ref);
			c->provider = p;
			p->client = c;
			*client = c;
			ret = 0;
		}
		mutex_unlock(&p->lock);
		break;
	}
	mutex_unlock(&qcom_hsphy_window_registry);
	if (ret) {
		ops->put(context);
		kfree(c);
	}
	return ret;
}

int qcom_snps_hsphy_window_client_unregister(struct qcom_snps_hsphy_window_client *c)
{
	struct qcom_hsphy_window_provider *p;
	bool busy = false;

	if (!c)
		return -EINVAL;
	p = c->provider;
	mutex_lock(&p->lock);
	if (p->bound) {
		mutex_lock(&p->bound->phy->mutex);
		busy = qcom_snps_hsphy_window_busy(p->bound);
		mutex_unlock(&p->bound->phy->mutex);
	}
	if (!busy)
		p->client = NULL;
	mutex_unlock(&p->lock);
	if (busy)
		return -EBUSY; /* preserve context/handle until restored or revoked */
	kref_put(&c->ref, qcom_hsphy_window_client_free);
	return 0;
}

int qcom_snps_hsphy_window_begin(struct qcom_snps_hsphy_window_client *c,
		struct qcom_snps_hsphy_window_result *result)
{
	struct qcom_hsphy_window_provider *p;
	int ret;

	if (!c || !result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	p = c->provider;
	mutex_lock(&p->lock);
	if (p->withdrawing || !p->bound)
		ret = -ESHUTDOWN;
	else
		ret = qcom_snps_hsphy_window_bound_begin(p->bound->phy, result);
	mutex_unlock(&p->lock);
	return ret;
}

int qcom_snps_hsphy_window_end(struct qcom_snps_hsphy_window_client *c, u64 cookie,
		struct qcom_snps_hsphy_window_result *result)
{
	struct qcom_hsphy_window_provider *p;
	int ret;

	if (!c || !result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	p = c->provider;
	mutex_lock(&p->lock);
	/* The withdrawal callback may restore while storage is still bound.
	 * Once tombstoned, no stale handle may touch PHY/PM/devres again. */
	if (!p->bound) {
		*result = p->receipt;
		ret = -ESHUTDOWN;
	} else {
		ret = qcom_snps_hsphy_window_bound_end(p->bound->phy, cookie, result);
	}
	mutex_unlock(&p->lock);
	return ret;
}

int qcom_snps_hsphy_window_status(struct qcom_snps_hsphy_window_client *c,
		struct qcom_snps_hsphy_window_result *result)
{
	struct qcom_hsphy_window_provider *p;

	if (!c || !result)
		return -EINVAL;
	p = c->provider;
	mutex_lock(&p->lock);
	if (p->bound) {
		mutex_lock(&p->bound->phy->mutex);
		*result = p->bound->window;
		mutex_unlock(&p->bound->phy->mutex);
		result->revoked = p->withdrawing;
	} else {
		*result = p->receipt;
	}
	mutex_unlock(&p->lock);
	return 0;
}

static int qcom_hsphy_window_withdraw(struct qcom_hsphy_window_provider *p)
{
	struct qcom_snps_hsphy_window_client *c;
	struct qcom_snps_hsphy *hsphy;
	bool put_pm = false;
	int error = 0;

	/* Each concurrent withdrawal keeps its completion/receipt storage alive,
	 * even if devres drops the publication reference before a waiter wakes. */
	kref_get(&p->ref);
	mutex_lock(&qcom_hsphy_window_registry);
	mutex_lock(&p->lock);
	if (p->withdrawing) {
		mutex_unlock(&p->lock);
		mutex_unlock(&qcom_hsphy_window_registry);
		wait_for_completion(&p->withdrawn);
		error = p->withdraw_error;
		kref_put(&p->ref, qcom_hsphy_window_provider_free);
		return error;
	}
	p->withdrawing = true;
	list_del_init(&p->node);
	hsphy = p->bound;
	mutex_lock(&hsphy->phy->mutex);
	hsphy->window_withdrawing = true;
	mutex_unlock(&hsphy->phy->mutex);
	c = p->client;
	if (c)
		kref_get(&c->ref);
	mutex_unlock(&p->lock);
	mutex_unlock(&qcom_hsphy_window_registry);
	if (c)
		error = c->ops.cancel_join(c->context);
	mutex_lock(&p->lock);
	mutex_lock(&hsphy->phy->mutex);
	p->receipt = hsphy->window;
	if (qcom_snps_hsphy_window_busy(hsphy)) {
		if (!error)
			error = p->receipt.restore_error ? p->receipt.restore_error : -ESHUTDOWN;
		p->receipt.high_z = false;
		p->receipt.restored = false;
		/* Forced removal cannot retain permission to retry on freed MMIO.
		 * No second restore attempt or reconnect is invented here. */
		put_pm = hsphy->window_pm_ref;
		hsphy->window_pm_ref = false;
	}
	p->receipt.revoked = true;
	p->receipt.withdraw_error = error;
	p->withdraw_error = error;
	p->bound = NULL;
	p->dead = true;
	mutex_unlock(&hsphy->phy->mutex);
	mutex_unlock(&p->lock);
	if (put_pm)
		pm_runtime_put_noidle(hsphy->dev);
	if (c)
		kref_put(&c->ref, qcom_hsphy_window_client_free);
	complete_all(&p->withdrawn);
	kref_put(&p->ref, qcom_hsphy_window_provider_free);
	return error;
}

static void qcom_hsphy_window_release(void *data)
{
	struct qcom_hsphy_window_provider *p = data;

	qcom_hsphy_window_withdraw(p);
	kref_put(&p->ref, qcom_hsphy_window_provider_free);
}

static int qcom_hsphy_window_publish(struct qcom_snps_hsphy *hsphy)
{
	struct qcom_hsphy_window_provider *p;

	p = kzalloc(sizeof(*p), GFP_KERNEL);
	if (!p)
		return -ENOMEM;
	kref_init(&p->ref);
	mutex_init(&p->lock);
	init_completion(&p->withdrawn);
	INIT_LIST_HEAD(&p->node);
	p->key = hsphy->phy;
	p->bound = hsphy;
	hsphy->window_provider = p;
	mutex_lock(&qcom_hsphy_window_registry);
	list_add_tail(&p->node, &qcom_hsphy_window_providers);
	mutex_unlock(&qcom_hsphy_window_registry);
	/* Installed after generic PHY/provider/PM devres: withdrawal runs first
	 * on probe rollback as well as ordinary unbind. */
	return devm_add_action_or_reset(hsphy->dev, qcom_hsphy_window_release, p);
}

static void qcom_snps_hsphy_remove(struct platform_device *pdev)
{
	struct qcom_snps_hsphy *hsphy = dev_get_drvdata(&pdev->dev);
	int ret = qcom_hsphy_window_withdraw(hsphy->window_provider);

	if (ret)
		dev_warn(&pdev->dev, "PHY window revoked without successful cleanup: %d\n", ret);
}

static void qcom_snps_hsphy_shutdown(struct platform_device *pdev)
{
	qcom_snps_hsphy_remove(pdev);
}
