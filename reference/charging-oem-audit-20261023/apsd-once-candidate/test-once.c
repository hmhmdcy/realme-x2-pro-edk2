/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include "samurai-apsd-once.h"

static unsigned int groups;

static struct samurai_apsd_once ready(unsigned char result)
{
	struct samurai_apsd_once s = { 0 };

	assert(samurai_apsd_attach(&s, 100) == 0);
	assert(samurai_apsd_sample(&s, s.epoch, 101, 1, 0x11, result) ==
	       SAMURAI_APSD_REQUEST);
	return s;
}

static struct samurai_apsd_once waiting(void)
{
	struct samurai_apsd_once s = ready(1);

	assert(samurai_apsd_claim(&s, s.epoch, 102, 1000) == 0);
	assert(samurai_apsd_write_done(&s, s.epoch, 103, 0) == 0);
	return s;
}

static void first_done_and_exact_class(void)
{
	unsigned int result;
	struct samurai_apsd_once s;

	/* Every 7-bit result is checked against the declared exact-class rule. */
	for (result = 0; result < 128; result++) {
		s = (struct samurai_apsd_once) { 0 };
		assert(samurai_apsd_attach(&s, 0) == 0);
		assert(samurai_apsd_sample(&s, s.epoch, 1, 1, 0, result) == 0);
		assert(s.phase == SAMURAI_APSD_FIRST);
		assert(samurai_apsd_sample(&s, s.epoch, 2, 2, 1, result) ==
		       (result == 1 || result == 4 ? SAMURAI_APSD_REQUEST :
			SAMURAI_APSD_NO_RERUN));
		assert(!s.attempted && !s.new_result);
	}
	s = (struct samurai_apsd_once) { 0 };
	assert(samurai_apsd_attach(&s, 0) == 0);
	assert(samurai_apsd_sample(&s, s.epoch, 1, 1, 3, 1) ==
	       SAMURAI_APSD_NO_RERUN); /* QC status does not request rerun. */
	groups++;
}

static void same_result_is_new_only_after_clear(void)
{
	struct samurai_apsd_once s = waiting();
	unsigned int i;

	/* A changed result with DONE still high is also not a fresh completion. */
	for (i = 2; i < 25; i++) {
		assert(samurai_apsd_sample(&s, s.epoch, 104 + i, i, 0x11,
					 i & 1 ? 1 : 4) == SAMURAI_APSD_WAIT);
		assert(s.phase == SAMURAI_APSD_WAIT_CLEAR && !s.new_result);
	}
	assert(samurai_apsd_sample(&s, s.epoch, 200, 25, 0x10, 1) == 0);
	assert(s.phase == SAMURAI_APSD_WAIT_DONE);
	assert(samurai_apsd_sample(&s, s.epoch, 201, 26, 0x11, 1) ==
	       SAMURAI_APSD_NEW_DONE);
	assert(s.phase == SAMURAI_APSD_COMPLETE && s.new_result == 1);
	assert(samurai_apsd_sample(&s, s.epoch, 202, 27, 0x11, 1) == 0);
	assert(samurai_apsd_claim(&s, s.epoch, 203, 1000) == -EALREADY);
	groups++;
}

static void timeout_without_observed_clear(void)
{
	struct samurai_apsd_once s = waiting();

	assert(samurai_apsd_sample(&s, s.epoch, 999, 2, 1, 4) == 0);
	assert(samurai_apsd_clock(&s, s.epoch, 1000) == -ETIMEDOUT);
	assert(s.phase == SAMURAI_APSD_FAILED && s.attempted && !s.new_result);
	assert(samurai_apsd_claim(&s, s.epoch, 1001, 2000) == -ETIMEDOUT);
	assert(samurai_apsd_attach(&s, 1002) == -EBUSY);
	groups++;
}

static void clear_without_new_done_times_out(void)
{
	struct samurai_apsd_once s = waiting();

	assert(samurai_apsd_sample(&s, s.epoch, 200, 2, 0, 1) == 0);
	assert(samurai_apsd_sample(&s, s.epoch, 1000, 3, 1, 4) == -ETIMEDOUT);
	assert(s.phase == SAMURAI_APSD_FAILED && !s.new_result);
	groups++;
}

static void write_error_is_not_a_completed_attempt(void)
{
	struct samurai_apsd_once s = ready(4);

	assert(samurai_apsd_claim(&s, s.epoch, 102, 1000) == 0);
	assert(samurai_apsd_claim(&s, s.epoch, 102, 1000) == -EALREADY);
	assert(samurai_apsd_write_done(&s, s.epoch, 103, -EIO) == -EIO);
	assert(s.phase == SAMURAI_APSD_FAILED && s.attempted && !s.new_result);
	assert(samurai_apsd_sample(&s, s.epoch, 104, 2, 1, 4) == -EIO);
	assert(samurai_apsd_cancel(&s, s.epoch) == -EIO); /* preserve first fault */
	groups++;
}

static void uncertain_or_late_write_is_not_retried(void)
{
	struct samurai_apsd_once s = ready(1);

	assert(samurai_apsd_claim(&s, s.epoch, 102, 200) == 0);
	assert(samurai_apsd_clock(&s, s.epoch, 200) == -ETIMEDOUT);
	assert(samurai_apsd_write_done(&s, s.epoch, 201, 0) == -ETIMEDOUT);
	assert(samurai_apsd_claim(&s, s.epoch, 202, 1000) == -ETIMEDOUT);
	assert(s.attempted && s.phase == SAMURAI_APSD_FAILED);
	groups++;
}

static void physical_detach_only_rearms(void)
{
	struct samurai_apsd_once s = waiting();
	unsigned long long old = s.epoch;

	assert(samurai_apsd_cancel(&s, old) == -ECANCELED);
	assert(samurai_apsd_attach(&s, 200) == -EBUSY);
	samurai_apsd_detach(&s);
	assert(samurai_apsd_write_done(&s, old, 201, 0) == -ESTALE);
	assert(samurai_apsd_attach(&s, 202) == 0 && s.epoch == old + 1);
	assert(!s.attempted && !s.error && !s.first_result && !s.new_result);
	assert(samurai_apsd_sample(&s, old, 203, 100, 1, 4) == -ESTALE);
	assert(s.phase == SAMURAI_APSD_FIRST && !s.last_read_serial);
	assert(samurai_apsd_sample(&s, s.epoch, 203, 1, 1, 4) ==
	       SAMURAI_APSD_REQUEST);
	groups++;
}

static void cancellation_at_every_active_phase(void)
{
	enum samurai_apsd_phase phases[] = { SAMURAI_APSD_FIRST,
		SAMURAI_APSD_READY, SAMURAI_APSD_WRITING, SAMURAI_APSD_WAIT_CLEAR,
		SAMURAI_APSD_WAIT_DONE, SAMURAI_APSD_COMPLETE, SAMURAI_APSD_BYPASSED };
	unsigned int i;

	for (i = 0; i < sizeof(phases) / sizeof(phases[0]); i++) {
		struct samurai_apsd_once s = { .epoch = 1, .phase = phases[i] };

		assert(samurai_apsd_cancel(&s, 1) == -ECANCELED);
		assert(s.phase == SAMURAI_APSD_CANCELLED);
		assert(samurai_apsd_sample(&s, 1, 1, 1, 1, 4) == -ECANCELED);
		assert(samurai_apsd_write_done(&s, 1, 1, 0) == -ECANCELED);
		assert(samurai_apsd_fail(&s, 1, -EIO) == -ECANCELED);
	}
	groups++;
}

static void read_failures_and_clock_regression(void)
{
	struct samurai_apsd_once s = waiting();

	assert(samurai_apsd_fail(&s, s.epoch, -EREMOTEIO) == -EREMOTEIO);
	assert(samurai_apsd_sample(&s, s.epoch, 104, 2, 0, 0) == -EREMOTEIO);
	s = waiting();
	assert(samurai_apsd_sample(&s, s.epoch, 102, 2, 0, 0) == -ERANGE);
	assert(s.phase == SAMURAI_APSD_FAILED && s.attempted);
	groups++;
}

static void repeated_serial_cannot_supply_new_done(void)
{
	struct samurai_apsd_once s = waiting();

	assert(samurai_apsd_sample(&s, s.epoch, 104, 1, 0, 1) == -ESTALE);
	assert(s.phase == SAMURAI_APSD_WAIT_CLEAR);
	assert(samurai_apsd_sample(&s, s.epoch, 104, 2, 0, 1) == 0);
	assert(samurai_apsd_sample(&s, s.epoch, 105, 2, 1, 4) == -ESTALE);
	assert(s.phase == SAMURAI_APSD_WAIT_DONE);
	assert(samurai_apsd_sample(&s, s.epoch, 105, 3, 1, 4) ==
	       SAMURAI_APSD_NEW_DONE);
	groups++;
}

static void source_change_while_acquiring_windows(void)
{
	struct samurai_apsd_once s = ready(1);

	assert(samurai_apsd_sample(&s, s.epoch, 102, 2, 1, 4) == -EAGAIN);
	assert(!s.attempted && s.phase == SAMURAI_APSD_FAILED);
	assert(samurai_apsd_claim(&s, s.epoch, 103, 1000) == -EAGAIN);
	groups++;
}

static void invalid_deadline_has_no_bus_attempt(void)
{
	struct samurai_apsd_once s = ready(1);

	assert(samurai_apsd_claim(&s, s.epoch, 102, 102) == -EINVAL);
	assert(!s.attempted && s.phase == SAMURAI_APSD_READY);
	assert(samurai_apsd_claim(&s, s.epoch, 102, 103) == 0);
	assert(samurai_apsd_write_done(&s, s.epoch, 103, 0) == -ETIMEDOUT);
	groups++;
}

static void epoch_wrap_and_unsolicited_ack(void)
{
	struct samurai_apsd_once s = { .epoch = ~0ULL };

	assert(samurai_apsd_attach(&s, 0) == -EOVERFLOW);
	assert(s.phase == SAMURAI_APSD_DETACHED && s.epoch == ~0ULL);
	s = ready(1);
	assert(samurai_apsd_write_done(&s, s.epoch, 102, 0) == -EALREADY);
	assert(samurai_apsd_write_done(&s, 0, 103, 0) == -ESTALE);
	assert(!s.attempted && s.phase == SAMURAI_APSD_READY);
	groups++;
}

static void independent_late_bus_diagnostics(void)
{
	struct samurai_apsd_once s = ready(1);
	unsigned long long old = s.epoch;

	assert(samurai_apsd_claim(&s, old, 102, 200) == 0);
	assert(samurai_apsd_write_done(&s, old, 200, -EREMOTEIO) == -ETIMEDOUT);
	assert(s.error == -ETIMEDOUT && s.write_error == -EREMOTEIO);
	assert(s.write_ack && s.write_ack_ms == 200 && s.attempted);
	assert(samurai_apsd_write_done(&s, old, 201, 0) == -EALREADY);
	assert(s.write_error == -EREMOTEIO && s.write_ack_ms == 200);
	samurai_apsd_detach(&s);
	assert(samurai_apsd_attach(&s, 202) == 0);
	assert(samurai_apsd_write_done(&s, old, 203, -EIO) == -ESTALE);
	assert(!s.write_ack && !s.write_error && !s.write_ack_ms);
	s = ready(4);
	assert(samurai_apsd_claim(&s, s.epoch, 102, 1000) == 0);
	assert(samurai_apsd_cancel(&s, s.epoch) == -ECANCELED);
	assert(samurai_apsd_write_done(&s, s.epoch, 104, -EIO) == -ECANCELED);
	assert(s.error == -ECANCELED && s.write_error == -EIO && s.write_ack);
	groups++;
}

int main(void)
{
	first_done_and_exact_class();
	same_result_is_new_only_after_clear();
	timeout_without_observed_clear();
	clear_without_new_done_times_out();
	write_error_is_not_a_completed_attempt();
	uncertain_or_late_write_is_not_retried();
	physical_detach_only_rearms();
	cancellation_at_every_active_phase();
	read_failures_and_clock_regression();
	repeated_serial_cannot_supply_new_done();
	source_change_while_acquiring_windows();
	invalid_deadline_has_no_bus_attempt();
	epoch_wrap_and_unsolicited_ack();
	independent_late_bus_diagnostics();
	printf("%u protocol groups passed\n", groups);
	return 0;
}
