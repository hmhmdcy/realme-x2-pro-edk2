/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after the unchanged R7 status reader. Input->lock protects only
 * this transport; it does not grant a PD, route, HALT or PHY lease.
 */
static int samurai_usb_apsd_sample_locked(struct samurai_usb_input *input,
		struct samurai_apsd_bus_sample *sample)
{
	struct samurai_usb_status before, after;
	struct samurai_apsd_bus_sample value = { 0 };
	bool plugin, vbus, attached, state_attached;
	int ret;

	if (!sample)
		return -EINVAL;
	if (input->paused || input->apsd_joining) {
		ret = -ESHUTDOWN;
		goto out;
	}
	if (input->apsd_sample_serial == ~0ULL) {
		ret = -EOVERFLOW;
		goto out;
	}
	ret = samurai_usb_read_status(input, &before);
	if (!ret)
		ret = samurai_usb_read_status(input, &after);
	if (ret)
		goto out;
	if (!samurai_usb_status_equal(&before, &after)) {
		ret = -EAGAIN;
		goto out;
	}
	plugin = !!(after.plugin & 0x10);
	vbus = !!(after.misc & 0x20);
	attached = !!(after.misc & 0x01);
	state_attached = !!(after.attached & 0x20);
	if ((plugin || vbus || attached || state_attached) &&
	    !(plugin && vbus && attached && state_attached)) {
		ret = -EAGAIN;
		goto out;
	}
	/* Wire presence only. Even present=true is not proof of sink/PD state. */
	value.present = plugin;
	value.raw[0] = after.apsd;
	value.raw[1] = after.result;
	value.raw[2] = after.plugin;
	value.raw[3] = after.cc;
	value.raw[4] = after.attached;
	value.raw[5] = after.misc;
	value.raw[6] = after.legacy;
	value.serial = ++input->apsd_sample_serial;
	*sample = value;
out:
	return ret;
}

static int samurai_usb_apsd_read(void *ctx, struct samurai_apsd_bus_sample *sample)
{
 struct samurai_usb_input *input = ctx;
 int ret;
 mutex_lock(&input->lock);
 ret = samurai_usb_apsd_sample_locked(input, sample);
 mutex_unlock(&input->lock);
 return ret;
}

/* Input lock is held. Source samples are not an authorization capability. */
static int samurai_usb_apsd_rerun(void *ctx,
		const struct samurai_apsd_attempt *attempt,
		struct samurai_apsd_transfer_result *result)
{
	struct samurai_usb_input *input = ctx;
	struct samurai_apsd_transfer_result value = { };
	struct samurai_usb_status wire;
	struct samurai_usb_budget budget;
	int ret;

	if (!attempt || !attempt->context || !attempt->validate ||
	    !attempt->epoch || !attempt->expected.serial || !result)
		return -EINVAL;
	mutex_lock(&input->lock);
	if (attempt->epoch <= input->apsd_attempt_epoch) {
		ret = attempt->epoch == input->apsd_attempt_epoch ? -EALREADY : -ESTALE;
		goto out;
	}
	/* Consume before any fallible validation or possible transfer. */
	input->apsd_attempt_epoch = attempt->epoch;
	ret = samurai_usb_apsd_sample_locked(input, &value.before);
	if (ret)
		goto out;
	if (!value.before.present || value.before.serial <= attempt->expected.serial ||
	    !attempt->expected.present ||
	    memcmp(value.before.raw, attempt->expected.raw, sizeof(value.before.raw))) {
		ret = -ESTALE;
		goto out;
	}
	memcpy(&wire, value.before.raw, sizeof(wire));
	ret = samurai_usb_decode(&wire, &budget);
	if (ret || !budget.online || !(wire.apsd & 1) || (wire.apsd & 2) ||
	    (wire.result != 1 && wire.result != 4)) {
		ret = ret ? ret : -ENODATA;
		goto out;
	}
	/* Last potentially blocking check before the single forced transfer.
	 * A later cancellation is an in-flight operation: original worker join
	 * must finish before any supplier can release its bound resources.
	 * Neither this nor regmap makes source detach atomic with the write.
	 */
	ret = attempt->validate(attempt, &value.before);
	if (ret)
		goto out;
	value.transfer_attempted = true;
	value.write_error = regmap_write_bits(input->map, 0x1341, BIT(0), BIT(0));
	value.post_error = samurai_usb_apsd_sample_locked(input, &value.after);
	if (!value.post_error) {
		memcpy(&wire, value.after.raw, sizeof(wire));
		value.post_error = samurai_usb_decode(&wire, &budget);
		/* APSD status/result may legitimately change after the command.
		 * The five role/presence fields must still equal the pre-write read.
		 */
		if (!value.post_error && (!value.after.present || !budget.online ||
		    (wire.apsd & 2) || (wire.result & 0x60) ||
		    memcmp(value.after.raw + 2, value.before.raw + 2, 5)))
			value.post_error = -ESTALE;
	}
	value.post_valid = !value.post_error;
	/* Preserve both independent outcomes, including a late bus errno. */
	ret = value.write_error ? value.write_error : value.post_error;
out:
	*result = value;
	mutex_unlock(&input->lock);
	return ret;
}


static const struct samurai_apsd_bus_ops samurai_usb_apsd_ops = {
	.read_sample = samurai_usb_apsd_read,
	.rerun_once = samurai_usb_apsd_rerun,
};

static void samurai_usb_apsd_start(struct samurai_usb_input *input)
{
	int ret;

	if (!apsd_backend)
		return;
	mutex_lock(&input->lock);
	/* Probe/resume/stop are serialized by this provider's bound lifecycle. */
	if (input->apsd_registered) {
		mutex_unlock(&input->lock);
		return;
	}
	input->apsd_joining = false;
	mutex_unlock(&input->lock);
	ret = samurai_apsd_bus_register(input->dev, &samurai_usb_apsd_ops, input);
	mutex_lock(&input->lock);
	input->apsd_registered = !ret;
	input->apsd_joining = !!ret;
	mutex_unlock(&input->lock);
	/* Optional transport failure must not remove the normal budget observer. */
	if (ret)
		dev_warn(input->dev, "optional APSD transport unavailable: %d\n", ret);
}

static void samurai_usb_apsd_withdraw(struct samurai_usb_input *input)
{
	bool registered;

	mutex_lock(&input->lock);
	input->apsd_joining = true;
	registered = input->apsd_registered;
	input->apsd_registered = false;
	mutex_unlock(&input->lock);
	/* Never join while holding the lock the original callbacks need. */
	if (registered)
		samurai_apsd_bus_unregister(input->dev, input);
}
