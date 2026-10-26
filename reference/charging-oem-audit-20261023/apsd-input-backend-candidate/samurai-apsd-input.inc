/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after the unchanged R7 status reader. Input->lock protects only
 * this transport; it does not grant a PD, route, HALT or PHY lease.
 */
static int samurai_usb_apsd_read(void *ctx,
		struct samurai_apsd_bus_sample *sample)
{
	struct samurai_usb_input *input = ctx;
	struct samurai_usb_status before, after;
	struct samurai_apsd_bus_sample value = { 0 };
	bool plugin, vbus, attached, state_attached;
	int ret;

	if (!sample)
		return -EINVAL;
	mutex_lock(&input->lock);
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
	mutex_unlock(&input->lock);
	return ret;
}

static int samurai_usb_apsd_rerun(void *ctx, u64 epoch)
{
	struct samurai_usb_input *input = ctx;
	int ret;

	if (!epoch)
		return -EINVAL;
	mutex_lock(&input->lock);
	if (epoch <= input->apsd_attempt_epoch) {
		ret = epoch == input->apsd_attempt_epoch ? -EALREADY : -ESTALE;
		goto out;
	}
	/* A failed/blocked call consumes this epoch too. No resume-time retry. */
	input->apsd_attempt_epoch = epoch;
	if (input->paused || input->apsd_joining) {
		ret = -ESHUTDOWN;
		goto out;
	}
	/* Force the original OEM masked command transfer. Ordinary update_bits
	 * can skip an already-set bit and falsely look like a newly sent command.
	 * This callback alone grants no authorization to enter it; the owner must
	 * hold its independent leases and consume the protocol attempt first.
	 */
	ret = regmap_write_bits(input->map, 0x1341, BIT(0), BIT(0));
out:
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
