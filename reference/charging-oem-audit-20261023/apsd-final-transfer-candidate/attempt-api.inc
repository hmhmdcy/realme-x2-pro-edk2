/* The attempt is embedded in the joined owner worker. validate must verify
 * that exact address and its actual supplier leases, not trust these fields.
 * Called with input->lock held: no owner registry, input lock, join, resume,
 * lease acquisition/release or restoration. Supplier validation may sleep;
 * supplier revocation publishes before joining this worker outside its lock.
 */
struct samurai_apsd_attempt {
	void *context;
	u64 epoch;
	struct samurai_apsd_bus_sample expected;
	int (*validate)(const struct samurai_apsd_attempt *attempt,
			const struct samurai_apsd_bus_sample *fresh);
};

struct samurai_apsd_transfer_result {
	struct samurai_apsd_bus_sample before, after;
	bool transfer_attempted, post_valid;
	int write_error, post_error;
};
