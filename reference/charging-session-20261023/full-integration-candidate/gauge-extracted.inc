static int sm_gauge_sample(struct sm_charger *c, struct sm_sample *s)
{
	struct i2c_client *g = c->gauge;
	unsigned char packet[36];
	int temp, pack, flags, current_word, ret;

	i2c_lock_bus(g->adapter, I2C_LOCK_SEGMENT);
	temp = sm_gauge_word_locked(g, 0x06, false, 0);
	pack = sm_gauge_word_locked(g, 0x08, false, 0);
	flags = sm_gauge_word_locked(g, 0x0a, false, 0);
	/* OEM FFA5 maps its misleading get_average_current name to 0x0c.
	 * Acquire the actual signed instantaneous net current in the same bus
	 * segment; do not substitute mainline current_now's 0x14 average.
	 */
	current_word = sm_gauge_word_locked(g, 0x0c, false, 0);
	if (temp < 0 || pack < 0 || flags < 0 || current_word < 0) {
		ret = temp < 0 ? temp : pack < 0 ? pack : flags < 0 ? flags : current_word;
		goto out;
	}
	ret = sm_gauge_mac_locked(g, 0x0071, packet);
	if (ret) goto out;
	s->temp_decic = temp - 2731;
	s->pack_uv = pack * 1000;
	s->gauge_flags = flags;
	ret = sm_oem_gauge_current_ua(current_word, &s->gauge_current_ua);
	if (ret) goto out;
	s->cell1_uv = sm_le16(packet + 2) * 1000;
	s->cell2_uv = sm_le16(packet + 4) * 1000;
out:
	i2c_unlock_bus(g->adapter, I2C_LOCK_SEGMENT);
	return ret;
}
