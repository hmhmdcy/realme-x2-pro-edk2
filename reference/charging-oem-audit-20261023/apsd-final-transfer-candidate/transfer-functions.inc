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
