/* Appended to existing OS/I2C fake boundaries, not a duplicate capture algorithm. */
static void dump_cache(const char *directory, const char *name)
{
	char data[PAGE_SIZE], path[1024];
	unsigned before = io_count;
	ssize_t n = mac_evidence_show(&dev, NULL, data);
	assert(n > 0 && n < PAGE_SIZE && io_count == before);
	assert(snprintf(path, sizeof(path), "%s/%s", directory, name) < (int)sizeof(path));
	FILE *file = fopen(path, "wb"); assert(file);
	assert(fwrite(data, 1, n, file) == (size_t)n); assert(!fclose(file));
}

int main(int argc, char **argv)
{
	assert(argc == 3);
	FILE *file = fopen(argv[1], "rb"); assert(file);
	for (unsigned int i = 0; i < 8; i++) {
		unsigned char cmd[2]; assert(fread(cmd, 1, 2, file) == 2);
		commands[i] = sm_le16(cmd); assert(fread(packets[i], 1, 36, file) == 36);
	}
	assert(fgetc(file) == EOF); assert(!fclose(file));
	assert(commands[0] == 1 && commands[7] == 0x56 && packets[7][35] == 7);
	assert(sm_mac_validate_sized(packets[7], 36, 0x56, 4) == -EMSGSIZE);
	assert(!sm_mac_validate_sized(packets[7], 36, 0x56, 3));
	cases++;

	reset(); assert(!observed_2719_diagnostic);
	assert(mac_evidence_capture_store(&dev, NULL, "capture\n", 8) == -EMSGSIZE);
	assert(p.evidence.diagnostic_profile == 0 && p.evidence.profile_identity_verified);
	assert(p.evidence.frames[7].expected_size == 4 && p.evidence.error == -EMSGSIZE && word_count == 1 && !p.evidence.battery_after_valid);
	dump_cache(argv[2], "standard-failed.txt"); unchanged_health(); cases++;
	unsigned before = io_count;
	observed_2719_diagnostic = true; /* Adversarial fake load-param change must not relabel old evidence. */
	assert(mac_evidence_capture_store(&dev, NULL, "capture\n", 8) == -EALREADY && io_count == before);
	dump_cache(argv[2], "same-attempt-not-relabelled.txt");
	assert(p.evidence.diagnostic_profile == 0); cases++;

	reset(); observed_2719_diagnostic = true;
	dump_cache(argv[2], "observed-before-attempt.txt"); assert(!io_count);
	word_after = 0x55aa; /* ONLY a fake boundary value; no physical trailing0A was captured. */
	assert(mac_evidence_capture_store(&dev, NULL, "capture\n", 8) == 8);
	assert(p.evidence.diagnostic_profile == 1 && p.evidence.profile_identity_verified && p.evidence.frames[7].expected_size == 3);
	assert(p.evidence.frames[5].expected_size == 4 && p.evidence.frames[6].expected_size == 4);
	assert(!memcmp(p.evidence.frames[7].raw, packets[7], 36));
	assert(p.evidence.stage == SM_EVIDENCE_COMPLETE && p.evidence.battery_after == 0x55aa && word_count == 2);
	dump_cache(argv[2], "observed-synthetic-after.txt"); unchanged_health(); cases++;

	reset(); observed_2719_diagnostic = true; packets[0][2] ^= 1; checksum(packets[0]);
	assert(mac_evidence_capture_store(&dev, NULL, "capture\n", 8) == -ENODEV && selected_count == 1 && word_count == 0);
	assert(!p.evidence.profile_identity_verified && p.evidence.frames[7].expected_size == 4);
	dump_cache(argv[2], "wrong-id.txt"); packets[0][2] ^= 1; checksum(packets[0]); cases++;
	reset(); observed_2719_diagnostic = true; packets[0][34] ^= 1;
	assert(mac_evidence_capture_store(&dev, NULL, "capture\n", 8) == -EBADMSG && selected_count == 1 && word_count == 0);
	assert(!p.evidence.profile_identity_verified); dump_cache(argv[2], "invalid-id-frame.txt"); packets[0][34] ^= 1; cases++;

	reset(); struct sm_mac_receipt receipt;
	i2c_lock_bus(&adapter, I2C_LOCK_SEGMENT);
	assert(sm_gauge_mac_observe_profile_locked(&gauge, 0x56, 1, 0, &receipt) == -ENODEV && !io_count && !receipt.select_attempted);
	assert(sm_gauge_mac_observe_profile_locked(&gauge, 0x56, 2, 0x2719, &receipt) == -EINVAL && !io_count);
	assert(sm_gauge_mac_observe_profile_locked(&gauge, 0x55, 1, 0x2719, &receipt) == -EINVAL && !io_count);
	unsigned char raw[36]; assert(sm_gauge_mac_locked(&gauge, 0x56, raw) == -EINVAL && !io_count);
	i2c_unlock_bus(&adapter, I2C_LOCK_SEGMENT); cases++;

	for (int mode = 3; mode <= 5; mode++) {
		reset(); observed_2719_diagnostic = true; fail_cmd = 0x56; failure = mode;
		int expected = mode == 3 ? -EIO : mode == 4 ? -EAGAIN : -EBADMSG;
		assert(mac_evidence_capture_store(&dev, NULL, "capture\n", 8) == expected && !p.evidence.battery_after_valid);
		assert(p.evidence.frames[7].expected_size == 3 && p.evidence.frames[7].full_read == (mode != 3));
		char name[32]; snprintf(name, sizeof(name), "failure-%d.txt", mode); dump_cache(argv[2], name); unchanged_health(); cases++;
	}
	reset(); observed_2719_diagnostic = true; packets[7][35] = 8; checksum(packets[7]);
	assert(mac_evidence_capture_store(&dev, NULL, "capture\n", 8) == -EMSGSIZE && !p.evidence.battery_after_valid);
	dump_cache(argv[2], "wrong-length8.txt"); packets[7][35] = 7; checksum(packets[7]); cases++;
	assert(!pthread_mutex_destroy(&p.lock.native));
	printf("{\"passed\":true,\"new_actual_function_groups\":%u,\"all8_MAC_frames_from_saved_real_batch\":true,"
	       "\"profile_success_after0A_value_is_synthetic\":true,\"new_device_query\":false}\n", cases);
	return 0;
}
