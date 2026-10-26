#define PD5V_STABLE_MS 500ULL
#define PD5V_FRESH_MS 250ULL
/* Exact PM8150B byte registers; no CC, QC, APSD, VBUS or USB2 control writes. */
static const unsigned int pd5v_status_regs[] = {
	0x1307, 0x1308, 0x1310, 0x1506, 0x1509, 0x150b, 0x150d,
	0x150a, 0x1544, 0x1362,
};
/* OEM close: BIST -> TX -> EN; current qcom reset adds filter=0 before EN.
 * All four are full-byte zero writes already used by those exact drivers. */
static const unsigned int pd5v_control_regs[] = { 0x174e, 0x1744, 0x174c, 0x1746 };
static const unsigned int pd5v_known_masks[] = { 0x8f, 0x7f, 0x21, 0x01 };

struct pd5v_sample { unsigned int status[10], control[4]; };
struct samurai_pd5v {
	struct device *dev;
	struct regmap *regmap;
	struct regulator *vdd;
	struct mutex lock;
	struct kref ref;
	struct samurai_pd5v_client client;
	struct samurai_pd5v_lease *active_lease;
	unsigned long long generation;
	bool powered, power_attempted, blocked, removed, initialized, attempted, leased;
	int power_errno;
	int error, write_errno, readback_errno, post_errno;
	unsigned int stage, writes;
	struct pd5v_sample first, before, after;
	unsigned long long first_ms, pre_ms, post_ms;
};

/* Exactly one board-specific real binding. Registry lock only protects a
 * temporary kref lookup/publication; no I/O or client join under this lock.
 * In particular, runtime acquire never needs device_lock(), since generic
 * PM calls prepare with that device lock already held. */
static DEFINE_MUTEX(pd5v_registry_lock);
static struct samurai_pd5v *pd5v_bound;


static unsigned long long pd5v_now_ms(void)
{
	return ktime_to_ms(ktime_get_boottime());
}

static int pd5v_read(struct samurai_pd5v *p, struct pd5v_sample *s)
{
	unsigned int i;
	int ret;
	for (i = 0; i < ARRAY_SIZE(pd5v_status_regs); i++) {
		ret = regmap_read(p->regmap, pd5v_status_regs[i], &s->status[i]);
		if (ret)
			return ret;
	}
	/* Type-C/USBIN status is readable independently, as in OEM policy.
	 * Do not touch the PD analogue block before our own power reference. */
	if (!p->powered)
		return 0;
	for (i = 0; i < ARRAY_SIZE(pd5v_control_regs); i++) {
		ret = regmap_read(p->regmap, pd5v_control_regs[i], &s->control[i]);
		if (ret)
			return ret;
		if (s->control[i] & ~pd5v_known_masks[i])
			return -EOPNOTSUPP;
	}
	return 0;
}

static int pd5v_policy(const struct pd5v_sample *s)
{
	/* No inference from peripheral DT, PHY enable=0, or absent TCPM.
	 * Require inherited CC already sink-only (no TRY/SRC/DISABLE), and
	 * HVDCP AUTH/AUTONOMOUS/ENABLE all disabled; do not change either. */
	return s->status[8] == 0x02 && !(s->status[9] & 0x64) &&
		(s->status[9] & 0x08);
}

static int pd5v_off(const struct pd5v_sample *s)
{
	/* Existing seven-field off test PLUS the actual Type-C vSafe0V bit.
	 * Neither cached get_vbus() nor ACOK=0 alone is accepted as 0 V. */
	return !(s->status[2] & 0x10) && !(s->status[5] & 0x21) &&
		!(s->status[4] & 0x20) && (s->status[7] & 0x40) &&
		!(s->status[7] & 0x20);
}

static int pd5v_same_status(const struct pd5v_sample *a, const struct pd5v_sample *b)
{
	unsigned int i;
	for (i = 0; i < ARRAY_SIZE(a->status); i++)
		if (a->status[i] != b->status[i])
			return 0;
	return 1;
}

static int pd5v_disabled(const struct pd5v_sample *s)
{
	return !s->control[0] && !s->control[1] &&
		!s->control[2] && !s->control[3];
}

static int pd5v_disable_off(struct samurai_pd5v *p)
{
	struct pd5v_sample sample;
	unsigned long long started, now;
	unsigned int i, value;
	int ret;
	if (p->attempted || p->power_attempted)
		return p->error ? p->error : -EALREADY;
	started = pd5v_now_ms();
	ret = pd5v_read(p, &p->first);
	if (ret)
		return ret;
	if (!pd5v_policy(&p->first) || !pd5v_off(&p->first))
		return -EAGAIN;
	p->first_ms = pd5v_now_ms();
	if (p->first_ms < started || p->first_ms - started > PD5V_FRESH_MS)
		return -EAGAIN;
	/* Engineering stability interval, not an OEM timing requirement. */
	msleep(PD5V_STABLE_MS);
	started = pd5v_now_ms();
	ret = pd5v_read(p, &sample);
	if (ret)
		return ret;
	now = pd5v_now_ms();
	if (now < started || now - started > PD5V_FRESH_MS ||
	    started < p->first_ms || started - p->first_ms < PD5V_STABLE_MS ||
	    !pd5v_same_status(&p->first, &sample) || !pd5v_off(&sample))
		return -EAGAIN;
	/* Taking a supply reference may actually power a formerly-off shared
	 * rail. It is part of takeover, so it too requires a real fresh off
	 * window; probe never powers the PD block on a live connection. */
	p->power_attempted = true;
	p->power_errno = regulator_enable(p->vdd);
	if (p->power_errno) {
		p->error = p->power_errno;
		return p->error;
	}
	p->powered = true;
	for (i = 0; i < ARRAY_SIZE(pd5v_control_regs); i++) {
		started = pd5v_now_ms();
		ret = pd5v_read(p, &p->before);
		if (ret)
			goto failed;
		p->pre_ms = pd5v_now_ms();
		if (p->pre_ms < started || p->pre_ms - started > PD5V_FRESH_MS ||
		    !pd5v_same_status(&p->first, &p->before) || !pd5v_off(&p->before)) {
			ret = -EAGAIN;
			goto failed;
		}
		p->stage = i + 1;
		p->attempted = true;
		/* Preserve a precise write/readback/post error; an errno does not
		 * prove a transfer had no effect. No fall-through to permission. */
		p->writes++;
		p->write_errno = regmap_write(p->regmap, pd5v_control_regs[i], 0);
		p->readback_errno = regmap_read(p->regmap, pd5v_control_regs[i], &value);
		if (!p->readback_errno && value)
			p->readback_errno = -EIO;
		p->post_errno = pd5v_read(p, &p->after);
		p->post_ms = pd5v_now_ms();
		if (!p->post_errno && (p->post_ms < p->pre_ms ||
		    !pd5v_same_status(&p->first, &p->after) || !pd5v_off(&p->after)))
			p->post_errno = -EAGAIN;
		ret = p->write_errno ? p->write_errno : p->readback_errno ?
			p->readback_errno : p->post_errno;
		if (ret)
			goto failed;
	}
	if (!pd5v_disabled(&p->after)) {
		ret = -EIO;
		goto failed;
	}
	p->initialized = true;
	p->generation++;
	return 0;
failed:
	/* Before any write, a changed off observation can be tried afresh by
	 * an explicit caller. After a write, this binding stays failed. */
	if (p->attempted || p->power_attempted)
		p->error = ret;
	return ret;
}

static int pd5v_verify(struct samurai_pd5v *p)
{
	struct pd5v_sample s;
	unsigned long long started = pd5v_now_ms(), now;
	int ret;
	if (!p->powered)
		return -ENODEV;
	ret = pd5v_read(p, &s);
	if (ret)
		return ret;
	now = pd5v_now_ms();
	if (now < started || now - started > PD5V_FRESH_MS)
		return -EAGAIN;
	if (!pd5v_policy(&s) || !pd5v_disabled(&s))
		return -EIO;
	/* Attached source/accessory or inconsistent VBUS/CC is never a sink
	 * permission. Detached is allowed for the pre-attach lease; the session
	 * still needs its own real physical epoch, sink sample and route gate. */
	if (s.status[5] & 0xd0)
		return -EBUSY;
	return 0;
}

static int samurai_pd5v_acquire(struct samurai_pd5v *p,
		const struct samurai_pd5v_client *client,
		struct samurai_pd5v_lease *lease)
{
	int ret;
	if (!p || !client || !client->cancel_join || !lease || lease->owner)
		return -EINVAL;
	/* Before any I/O/write: a module already GOING cannot acquire. */
	if (!try_module_get(THIS_MODULE))
		return -ENODEV;
	mutex_lock(&p->lock);
	if (p->removed || p->blocked || p->leased || p->error) {
		ret = p->error ? p->error : -EBUSY;
		goto out;
	}
	ret = p->initialized ? pd5v_verify(p) : pd5v_disable_off(p);
	if (ret) {
		if (p->initialized) {
			p->generation++;
			p->error = ret;
		}
		goto out;
	}
	kref_get(&p->ref);
	p->client = *client;
	p->leased = true;
	p->active_lease = lease;
	p->generation++;
	lease->owner = p;
	lease->generation = p->generation;
out:
	mutex_unlock(&p->lock);
	if (ret)
		module_put(THIS_MODULE);
	return ret;
}

int samurai_pd5v_validate(const struct samurai_pd5v_lease *lease)
{
	struct samurai_pd5v *p;
	int ret;
	if (!lease || !lease->owner)
		return -EINVAL;
	p = lease->owner;
	mutex_lock(&p->lock);
	if (!p->leased || p->active_lease != lease || p->removed || p->blocked || p->error ||
	    lease->generation != p->generation) {
		ret = -ESTALE;
		goto out;
	}
	ret = pd5v_verify(p);
	/* A failed read is unknown; never reuse the old success token. The
	 * caller must unwind on any error. No join is called under this lock. */
	if (ret) {
		p->generation++;
		p->error = ret;
	}
out:
	mutex_unlock(&p->lock);
	return ret;
}

static void pd5v_free(struct kref *ref)
{
	struct samurai_pd5v *p = container_of(ref, struct samurai_pd5v, ref);
	if (p->powered)
		regulator_disable(p->vdd);
	regulator_put(p->vdd);
	put_device(p->dev);
	kfree(p);
}

void samurai_pd5v_release(struct samurai_pd5v_lease *lease)
{
	struct samurai_pd5v *p;
	if (!lease || !lease->owner)
		return;
	p = lease->owner;
	mutex_lock(&p->lock);
	if (!p->leased || p->active_lease != lease) {
		lease->owner = NULL;
		mutex_unlock(&p->lock);
		return;
	}
	p->leased = false;
	p->active_lease = NULL;
	memset(&p->client, 0, sizeof(p->client));
	lease->owner = NULL;
	mutex_unlock(&p->lock);
	kref_put(&p->ref, pd5v_free);
	module_put(THIS_MODULE);
}

int qcom_pmic_typec_5v_acquire(struct device *typec,
		const struct samurai_pd5v_client *client,
		struct samurai_pd5v_lease *lease)
{
	struct samurai_pd5v *p = NULL;
	int ret;
	mutex_lock(&pd5v_registry_lock);
	if (pd5v_bound && pd5v_bound->dev == typec && try_module_get(THIS_MODULE)) {
		p = pd5v_bound;
		kref_get(&p->ref);
	}
	mutex_unlock(&pd5v_registry_lock);
	if (!p)
		return -ENODEV;
	ret = samurai_pd5v_acquire(p, client, lease);
	kref_put(&p->ref, pd5v_free);
	module_put(THIS_MODULE);
	return ret;
}

int samurai_pd5v_quiesce(struct samurai_pd5v *p)
{
	struct samurai_pd5v_client client = { };
	int ret;
	mutex_lock(&p->lock);
	p->blocked = true;
	p->generation++;
	if (p->leased)
		client = p->client;
	mutex_unlock(&p->lock);
	if (client.cancel_join)
		client.cancel_join(client.context);
	mutex_lock(&p->lock);
	ret = p->leased ? -EBUSY : 0;
	if (ret)
		p->error = ret;
	mutex_unlock(&p->lock);
	if (ret)
		dev_err(p->dev, "PD5V client failed to join: %d; permission revoked\n", ret);
	return ret;
}

void samurai_pd5v_complete(struct samurai_pd5v *p)
{
	int ret = 0;
	mutex_lock(&p->lock);
	if (p->initialized && !p->error)
		ret = pd5v_verify(p);
	if (ret)
		p->error = ret;
	/* Waiting for first off stays waiting. No init or retry on resume. */
	if (!p->removed && !p->error)
		p->blocked = false;
	mutex_unlock(&p->lock);
}

struct samurai_pd5v *samurai_pd5v_create(struct device *dev, struct regmap *regmap)
{
	struct samurai_pd5v *p;
	struct device_node *supply, *usb2, *shared;
	int ret;
	/* Same physical L2 as the actual native USB2 vdda33. Hold only a
	 * consumer reference: no voltage, load, power-cycle or USB2 reset. */
	supply = of_parse_phandle(dev->of_node, "vdd-pdphy-supply", 0);
	usb2 = of_find_node_by_path("/soc@0/phy@88e2000");
	shared = usb2 ? of_parse_phandle(usb2, "vdda33-supply", 0) : NULL;
	ret = !supply || !shared || supply != shared ? -EXDEV : 0;
	of_node_put(shared);
	of_node_put(usb2);
	of_node_put(supply);
	if (ret)
		return ERR_PTR(ret);
	p = kzalloc(sizeof(*p), GFP_KERNEL);
	if (!p)
		return ERR_PTR(-ENOMEM);
	p->vdd = regulator_get(dev, "vdd-pdphy");
	if (IS_ERR(p->vdd)) {
		ret = PTR_ERR(p->vdd);
		kfree(p);
		return ERR_PTR(ret);
	}
	p->regmap = regmap;
	p->dev = get_device(dev);
	p->generation = 1;
	mutex_init(&p->lock);
	kref_init(&p->ref);
	mutex_lock(&pd5v_registry_lock);
	if (pd5v_bound) {
		mutex_unlock(&pd5v_registry_lock);
		kref_put(&p->ref, pd5v_free);
		return ERR_PTR(-EBUSY);
	}
	pd5v_bound = p;
	mutex_unlock(&pd5v_registry_lock);
	return p;
}

void samurai_pd5v_destroy(struct samurai_pd5v *p)
{
	int ret;
	mutex_lock(&pd5v_registry_lock);
	if (pd5v_bound == p)
		pd5v_bound = NULL;
	mutex_unlock(&pd5v_registry_lock);
	mutex_lock(&p->lock);
	p->removed = true;
	mutex_unlock(&p->lock);
	ret = samurai_pd5v_quiesce(p);
	/* Trusted in-Image client's cancel_join must release. If violated,
	 * keep its object/power references, report failure, and grant nothing. */
	if (ret)
		dev_err(p->dev, "PD5V client failed to join: %d; permission revoked\n", ret);
	kref_put(&p->ref, pd5v_free);
}
