/* Same-Image provider lifecycle. Registry metadata never spans client calls,
 * PHY mutex, PM operations or a join. Driver PM/remove entrypoints retain the
 * bound devres lifetime; public operations drain before the last devres action.
 */
static DEFINE_MUTEX(window_registry);
static LIST_HEAD(window_providers);
static u64 window_binding_sequence;

static struct qcom_snps_hsphy *window_find(struct phy *phy)
{
	struct qcom_snps_hsphy *h;

	lockdep_assert_held(&window_registry);
	list_for_each_entry(h, &window_providers, window_node)
		if (h->phy == phy)
			return h;
	return NULL;
}

static bool window_binding_matches(struct qcom_snps_hsphy *h,
		const struct qcom_snps_hsphy_window_binding *b)
{
	return h && h->window_published && !READ_ONCE(h->window_dead) &&
		h->window_client.context == b->context &&
		h->window_binding_id == b->provider_id &&
		h->window_client_id == b->client_id && b->client_id;
}

static struct qcom_snps_hsphy *window_operation_get(
		const struct qcom_snps_hsphy_window_binding *b, bool restore)
{
	struct qcom_snps_hsphy *h;

	if (!b || !b->phy || !b->provider_id || !b->client_id || !b->context)
		return ERR_PTR(-EINVAL);
	mutex_lock(&window_registry);
	h = window_find(b->phy); /* compare identity first; never dereference old phy */
	if (!window_binding_matches(h, b) || h->window_closing)
		h = ERR_PTR(-ESHUTDOWN);
	else if (!restore && h->window_blocked)
		h = ERR_PTR(-EBUSY);
	else if (!h->window_operations++)
		reinit_completion(&h->window_operations_done);
	mutex_unlock(&window_registry);
	return h;
}

static void window_operation_put(struct qcom_snps_hsphy *h)
{
	mutex_lock(&window_registry);
	if (!--h->window_operations)
		complete_all(&h->window_operations_done);
	mutex_unlock(&window_registry);
}

int qcom_snps_hsphy_window_client_register(struct phy *phy,
		const struct qcom_snps_hsphy_window_client *client,
		struct qcom_snps_hsphy_window_binding *binding)
{
	struct qcom_snps_hsphy *h;
	int ret = 0;

	if (!binding || !client || !client->context || !client->get_unless_zero ||
	    !client->put || !client->cancel_join || !client->complete)
		return -EINVAL;
	memset(binding, 0, sizeof(*binding));
	mutex_lock(&window_registry);
	h = window_find(phy);
	if (!h || !h->window_published || READ_ONCE(h->window_dead))
		ret = -ENODEV;
	else if (h->window_blocked || h->window_client.context)
		ret = -EBUSY;
	else if (h->window_client_id == U64_MAX)
		ret = -EOVERFLOW;
	else if (!client->get_unless_zero(client->context))
		ret = -ESHUTDOWN;
	else {
		h->window_client = *client; /* registration owns this real client ref */
		binding->phy = phy;
		binding->provider_id = h->window_binding_id;
		binding->client_id = ++h->window_client_id;
		binding->context = client->context;
	}
	mutex_unlock(&window_registry);
	return ret;
}

int qcom_snps_hsphy_window_client_unregister(
		struct qcom_snps_hsphy_window_binding *binding)
{
	struct qcom_snps_hsphy_window_client client = { };
	struct qcom_snps_hsphy *h;
	int ret = 0;

	if (!binding || !binding->phy)
		return -EINVAL;
	mutex_lock(&window_registry);
	h = window_find(binding->phy);
	if (!window_binding_matches(h, binding))
		ret = -ESHUTDOWN;
	else {
		/* Caller joined its worker first. Never wait for provider cancel:
		 * its callback may currently be waiting for owner_registry. */
		mutex_lock(&h->phy->mutex);
		if (qcom_snps_hsphy_window_busy(h) || h->window_operations)
			ret = -EBUSY;
		else {
			client = h->window_client;
			memset(&h->window_client, 0, sizeof(h->window_client));
		}
		mutex_unlock(&h->phy->mutex);
	}
	if (ret != -EBUSY)
		memset(binding, 0, sizeof(*binding));
	mutex_unlock(&window_registry);
	if (client.context)
		client.put(client.context); /* never under provider/PHY locks */
	return ret;
}

int qcom_snps_hsphy_window_begin(
		const struct qcom_snps_hsphy_window_binding *binding,
		struct qcom_snps_hsphy_window_result *result)
{
	struct qcom_snps_hsphy *h;
	int ret;

	if (!result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	h = window_operation_get(binding, false);
	if (IS_ERR(h))
		return PTR_ERR(h);
	ret = qcom_snps_hsphy_window_begin_active(h->phy, result);
	result->provider_id = binding->provider_id;
	result->client_id = binding->client_id;
	window_operation_put(h);
	return ret;
}

int qcom_snps_hsphy_window_end(
		const struct qcom_snps_hsphy_window_binding *binding, u64 cookie,
		struct qcom_snps_hsphy_window_result *result)
{
	struct qcom_snps_hsphy *h;
	int ret;

	if (!result || !cookie)
		return -EINVAL;
	h = window_operation_get(binding, true);
	if (IS_ERR(h)) {
		/* An old receipt may keep its actual enter/restore errno. Revocation
		 * is independent and is never a successful restoration or retry. */
		result->provider_revoked = PTR_ERR(h) == -ESHUTDOWN;
		result->lifecycle_error = PTR_ERR(h);
		result->restored = result->high_z = false;
		return PTR_ERR(h);
	}
	ret = qcom_snps_hsphy_window_end_active(h->phy, cookie, result);
	result->provider_id = binding->provider_id;
	result->client_id = binding->client_id;
	window_operation_put(h);
	return ret;
}

static void window_provider_init(struct qcom_snps_hsphy *h)
{
	mutex_init(&h->window_pm_stop_lock);
	INIT_LIST_HEAD(&h->window_node);
	init_completion(&h->window_operations_done);
	complete_all(&h->window_operations_done);
	init_completion(&h->window_revoke_done);
	complete_all(&h->window_revoke_done);
	init_completion(&h->window_callbacks_done);
	complete_all(&h->window_callbacks_done);
}

/* devm_pm_runtime_enable's original cleanup is older than generic PHY devres.
 * Stop runtime callbacks before those resources, with no registry/PHY lock
 * held. The later managed action still performs dont_use_autosuspend and
 * never adds a second disable depth. No callback calls this helper. */
static void window_provider_disable_pm(struct qcom_snps_hsphy *h)
{
	mutex_lock(&window_registry);
	h->window_blocked |= QCOM_HSPHY_WINDOW_REMOVE;
	mutex_unlock(&window_registry);
	mutex_lock(&h->window_pm_stop_lock);
	if (!h->window_pm_disabled) {
		pm_runtime_disable(h->dev);
		h->window_pm_disabled = true;
	}
	mutex_unlock(&h->window_pm_stop_lock);
}

static void window_provider_pm_cleanup(void *data)
{
	struct qcom_snps_hsphy *h = data;

	pm_runtime_dont_use_autosuspend(h->dev);
	window_provider_disable_pm(h);
}

static int window_provider_publish(struct qcom_snps_hsphy *h)
{
	int ret = 0;

	mutex_lock(&window_registry);
	if (window_binding_sequence == U64_MAX)
		ret = -EOVERFLOW;
	else {
		h->window_binding_id = ++window_binding_sequence;
		h->window_published = true;
		list_add_tail(&h->window_node, &window_providers);
	}
	mutex_unlock(&window_registry);
	return ret;
}

static int window_provider_quiesce(struct qcom_snps_hsphy *h,
		enum qcom_snps_hsphy_window_reason reason, bool terminal)
{
	struct qcom_snps_hsphy_window_client callback = { }, release = { };
	struct qcom_snps_hsphy_window_binding binding = { };
	bool extra = false, put_pm = false;
	int ret = 0;

	/* Only driver-bound PM/remove/shutdown/devres entrypoints call this.
	 * Waiters are protected by the actual device-core lifecycle, not by a
	 * get_device reference from a detection consumer. */
again:
	mutex_lock(&window_registry);
	if (h->window_revoking) {
		mutex_unlock(&window_registry);
		wait_for_completion(&h->window_revoke_done);
		goto again;
	}
	if (READ_ONCE(h->window_dead) || !h->window_published) {
		mutex_unlock(&window_registry);
		return 0;
	}
	h->window_revoking = true;
	h->window_blocked |= reason; /* new begin is refused before callback */
	reinit_completion(&h->window_revoke_done);
	callback = h->window_client;
	binding.phy = h->phy;
	binding.provider_id = h->window_binding_id;
	binding.client_id = h->window_client_id;
	binding.context = callback.context;
	if (callback.context) {
		extra = callback.get_unless_zero(callback.context);
		if (!extra)
			ret = -ESHUTDOWN;
	}
	mutex_unlock(&window_registry);
	/* Finish an already-dispatched complete callback before cancellation,
	 * so it cannot queue new owner work after cancel_join has returned. */
	wait_for_completion(&h->window_callbacks_done);
	if (extra)
		ret = callback.cancel_join(callback.context, &binding, reason);
	/* Existing end may restore during this join while MMIO still exists.
	 * No public operation can outlive this drain into devres destruction. */
	mutex_lock(&window_registry);
	h->window_closing = true; /* end is now also refused before final drain */
	mutex_unlock(&window_registry);
	wait_for_completion(&h->window_operations_done);
	mutex_lock(&h->phy->mutex);
	if (!ret && qcom_snps_hsphy_window_busy(h))
		ret = -EBUSY;
	if (terminal) {
		/* Generic init/exit/mode/runtime callbacks hold this same PHY
		 * mutex; terminal is visible before any of them can touch MMIO. */
		WRITE_ONCE(h->window_dead, true);
		h->window.provider_revoked = true;
		h->window.lifecycle_error = ret ? ret : -ESHUTDOWN;
		h->window.high_z = h->window.restored = false;
		if (qcom_snps_hsphy_window_busy(h))
			h->window.state = QCOM_HSPHY_WINDOW_FAILED;
		put_pm = h->window_pm_ref;
		h->window_pm_ref = false;
	}
	mutex_unlock(&h->phy->mutex);
	mutex_lock(&window_registry);
	h->window_join_error = ret;
	if (terminal) {
		h->window_published = false;
		list_del_init(&h->window_node);
		release = h->window_client;
		memset(&h->window_client, 0, sizeof(h->window_client));
	}
	mutex_unlock(&window_registry);
	if (put_pm)
		pm_runtime_put_noidle(h->dev); /* before devres, never another MMIO */
	if (release.context)
		release.put(release.context);
	if (extra)
		callback.put(callback.context);
	mutex_lock(&window_registry);
	if (!terminal)
		h->window_closing = false;
	h->window_revoking = false;
	complete_all(&h->window_revoke_done);
	mutex_unlock(&window_registry);
	return ret;
}

static void window_provider_complete(struct qcom_snps_hsphy *h,
		unsigned int reason)
{
	struct qcom_snps_hsphy_window_client callback = { };
	struct qcom_snps_hsphy_window_binding binding = { };

	mutex_lock(&window_registry);
	if (h->window_published && !READ_ONCE(h->window_dead) && !h->window_revoking &&
	    !h->window_join_error) {
		h->window_blocked &= ~reason;
		if (!h->window_blocked && h->window_client.context &&
		    h->window_client.get_unless_zero(h->window_client.context)) {
			callback = h->window_client;
			if (!h->window_callbacks++)
				reinit_completion(&h->window_callbacks_done);
			binding = (struct qcom_snps_hsphy_window_binding) {
				.phy = h->phy, .provider_id = h->window_binding_id,
				.client_id = h->window_client_id, .context = callback.context,
			};
		}
	}
	mutex_unlock(&window_registry);
	if (callback.context) {
		callback.complete(callback.context, &binding);
		callback.put(callback.context);
		mutex_lock(&window_registry);
		if (!--h->window_callbacks)
			complete_all(&h->window_callbacks_done);
		mutex_unlock(&window_registry);
	}
}
