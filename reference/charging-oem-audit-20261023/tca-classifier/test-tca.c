/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "tca-reference.h"

static unsigned int frame_cases, classification_cases;
static void packet(unsigned char *p, unsigned int command, unsigned int value,
		   unsigned int payload)
{
	unsigned int sum = 0;
	memset(p, 0, 36);
	p[0] = command; p[1] = command >> 8;
	for (unsigned int i = 0; i < payload; i++) p[i + 2] = value >> (i * 8);
	p[35] = payload + 4;
	for (unsigned int i = 0; i < payload + 2; i++) sum += p[i];
	p[34] = 255 - (sum & 255);
}
static void frames(void)
{
	unsigned char p[36];
	unsigned int value;
	const unsigned int commands[] = { 0x50, 0x52, 0x56, 0x55 };
	for (unsigned int i = 0; i < 4; i++) {
		unsigned int cmd = commands[i], n = sm_tca_payload_bytes(cmd);
		unsigned int expected = n == 4 ? 0x12345678 : 0x5678;
		packet(p, cmd, expected, n);
		assert(!sm_tca_decode(p, 36, cmd, &value) && value == expected); frame_cases++;
		assert(sm_tca_decode(p, 35, cmd, &value) == -EMSGSIZE); frame_cases++;
		p[35]--;
		assert(sm_tca_decode(p, 36, cmd, &value) == -EMSGSIZE); frame_cases++;
		p[35]++;
		p[0] ^= 1;
		assert(sm_tca_decode(p, 36, cmd, &value) == -EAGAIN); frame_cases++;
		p[0] ^= 1;
		p[34] ^= 1;
		assert(sm_tca_decode(p, 36, cmd, &value) == -EBADMSG); frame_cases++;
	}
	/* Three-byte GaugingStatus and guessed short PFAlert are rejected even
	 * when their logical checksum is internally correct. */
	packet(p, 0x56, 0x123456, 3);
	assert(sm_tca_decode(p, 36, 0x56, &value) == -EMSGSIZE); frame_cases++;
	packet(p, 0x52, 0x1234, 2);
	assert(sm_tca_decode(p, 36, 0x52, &value) == -EMSGSIZE); frame_cases++;
	assert(sm_tca_decode(p, 36, 0x22, &value) == -EINVAL); frame_cases++;
}
static struct sm_tca_evidence normal(void)
{
	return (struct sm_tca_evidence){
		.compatibility_verified = 1, .complete_fresh = 1, .coherent = 1,
		.source_allowed = 1, .policy_good_except_tca = 1, .independent_full = 1,
		.battery_before = 0x4020, .battery_after = 0x4020,
		.gauging = 0x100a, .operation = 0x306, .manufacturing = 0x18,
	};
}
static void check(struct sm_tca_evidence e, enum sm_tca_class want)
{
	enum sm_tca_class got = sm_tca_classify(&e);
	assert(got == want);
	assert(sm_tca_may_end_cycle(got) == (want == SM_TCA_NORMAL_TERMINATION));
	classification_cases++;
}
static void classification(void)
{
	struct sm_tca_evidence e = normal();
	check(e, SM_TCA_NORMAL_TERMINATION);
	e.compatibility_verified = 0; check(e, SM_TCA_UNVERIFIED);
	e = normal(); e.complete_fresh = 0; check(e, SM_TCA_UNVERIFIED);
	e = normal(); e.coherent = 0; check(e, SM_TCA_INCOHERENT);
	e = normal(); e.battery_before ^= 0x4000; check(e, SM_TCA_INCOHERENT);
	e = normal(); e.existing_hard_latch = 1; check(e, SM_TCA_EXISTING_FAULT);
	e = normal(); e.existing_timeout = 1; check(e, SM_TCA_EXISTING_FAULT);
	e = normal(); e.existing_timeout = 1; e.compatibility_verified = 0;
	check(e, SM_TCA_EXISTING_FAULT);
	for (unsigned int bit = 0; bit < 32; bit++) {
		e = normal(); e.safety_alert = 1U << bit; check(e, SM_TCA_ALERT_OR_FAULT);
		e = normal(); e.safety_status = 1U << bit; check(e, SM_TCA_ALERT_OR_FAULT);
		e = normal(); e.pf_alert = 1U << bit; check(e, SM_TCA_ALERT_OR_FAULT);
		e = normal(); e.pf_status = 1U << bit; check(e, SM_TCA_ALERT_OR_FAULT);
	}
	e = normal(); e.battery_before |= 0x8000; e.battery_after |= 0x8000;
	check(e, SM_TCA_ALERT_OR_FAULT);
	e = normal(); e.gauging &= ~0x08; check(e, SM_TCA_UNEXPLAINED);
	e = normal(); e.gauging |= 0x40; check(e, SM_TCA_UNEXPLAINED);
	e = normal(); e.battery_before |= 0x40; e.battery_after |= 0x40;
	check(e, SM_TCA_UNEXPLAINED);
	e = normal(); e.gauging |= 0x01000000; check(e, SM_TCA_BAD_OPERATION);
	e = normal(); e.gauging |= 0x100; check(e, SM_TCA_BAD_OPERATION);
	e = normal(); e.operation |= 0x4000; check(e, SM_TCA_BAD_OPERATION);
	e = normal(); e.operation &= ~0x04; check(e, SM_TCA_NORMAL_TERMINATION);
	e = normal(); e.independent_full = 0; check(e, SM_TCA_TC_REQUEST_HOLD);
	e = normal(); e.source_allowed = 0; check(e, SM_TCA_TC_REQUEST_HOLD);
	e = normal(); e.policy_good_except_tca = 0; check(e, SM_TCA_TC_REQUEST_HOLD);
	e = normal(); e.gauging &= ~0x02; e.battery_before &= ~0x20; e.battery_after &= ~0x20;
	check(e, SM_TCA_NORMAL_TERMINATION); /* FC is not TC and is not mandatory. */
	e = normal(); e.battery_before &= ~0x4000; e.battery_after &= ~0x4000;
	check(e, SM_TCA_NO_REQUEST); /* Observational only; not charge permission. */
}
int main(void)
{
	frames(); classification();
	printf("{\"frame_cases\":%u,\"classification_cases\":%u,\"passed\":true}\n",
		frame_cases, classification_cases);
	return 0;
}
