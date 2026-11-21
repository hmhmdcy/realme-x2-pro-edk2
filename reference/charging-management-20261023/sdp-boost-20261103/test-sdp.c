/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <limits.h>
#include <stdio.h>

#include "mp2650-core.h"

static struct sm_sample sample(void)
{
	return (struct sm_sample){
		.valid = 1,
		.online = 1,
		.protection_ok = 1,
		.budget_ua = 500000,
		.temp_decic = 250,
		.pack_uv = 7600000,
		.cell1_uv = 3800000,
		.cell2_uv = 3800000,
	};
}

static int policy(struct sm_sample *s, struct sm_target *t)
{
	return sm_policy(s, 4362500, 1100000, 2000000, t);
}

static void sdp_budget_tests(void)
{
	struct sm_sample s;
	struct sm_target t;

	/* A data-only SDP gets the board input ceiling instead of BC1.2 500 mA. */
	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = 900000;
	assert(!policy(&s, &t));
	assert(t.enable && t.input_ua == 900000);

	/* The boost is exclusively tied to the SDP classification. */
	s = sample();
	s.sdp = 0;
	s.sdp_boost_ua = 900000;
	assert(!policy(&s, &t));
	assert(t.input_ua == 500000);

	/* Zero disables the override without changing the SDP source budget. */
	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = 0;
	assert(!policy(&s, &t));
	assert(t.input_ua == 500000);

	/* A lower override never reduces the source allowance. */
	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = 70000;
	assert(!policy(&s, &t));
	assert(t.input_ua == 500000);

	/* The Type-C/PD/board caps still bound the SDP override. */
	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = 1500000;
	assert(!sm_policy(&s, 4362500, 1100000, 1000000, &t));
	assert(t.input_ua == 1000000);

	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = INT_MAX;
	assert(!policy(&s, &t));
	assert(t.input_ua == SM_OEM_INPUT_MAX_UA);

	/* Unknown source data is not turned into an invented 900 mA budget. */
	s = sample();
	s.budget_ua = 0;
	s.sdp = 1;
	s.sdp_boost_ua = 900000;
	assert(policy(&s, &t) == -ENODATA);
	assert(!t.enable);

	/* Hardware programming still accepts the boosted target. */
	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = 900000;
	assert(!policy(&s, &t));
	assert(t.input_ua == 900000 && t.input_ua / 50000 == 18);
}

static void existing_safety_tests(void)
{
	struct sm_sample s;
	struct sm_target t;
	enum sm_policy_reason reason;

	/* Temperature faults win over a valid SDP boost. */
	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = 900000;
	s.temp_decic = 530;
	assert(sm_policy_with_reason(&s, 4362500, 1100000, 2000000, &t,
				     &reason) == -ERANGE);
	assert(!t.enable && reason == SM_POLICY_REASON_TEMPERATURE);

	/* Cell OVP is evaluated before the target is emitted. */
	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = 900000;
	s.cell1_uv = 4420000;
	s.cell2_uv = 3180000;
	assert(sm_policy_with_reason(&s, 4362500, 1100000, 2000000, &t,
				     &reason) == -EOVERFLOW);
	assert(!t.enable && reason == SM_POLICY_REASON_BAND_OVP);

	/* The gauge's charge-stop request remains a stop request. */
	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = 900000;
	s.gauge_flags = 0x4000;
	assert(sm_policy_with_reason(&s, 4362500, 1100000, 2000000, &t,
				     &reason) == -EAGAIN);
	assert(!t.enable && reason == SM_POLICY_REASON_GAUGE_CHARGE_STOP);

	/* Thermal gating still rejects an out-of-profile band. */
	s = sample();
	s.sdp = 1;
	s.sdp_boost_ua = 900000;
	assert(sm_policy_with_band_reason(&s, 4362500, 1100000, 2000000, 6,
					  &t, &reason) == -ERANGE);
	assert(!t.enable && reason == SM_POLICY_REASON_TEMPERATURE);

	/* A non-SDP source keeps its original 500 mA budget. */
	s = sample();
	s.sdp = 0;
	s.sdp_boost_ua = 900000;
	assert(!policy(&s, &t));
	assert(t.input_ua == 500000);
}

int main(void)
{
	sdp_budget_tests();
	existing_safety_tests();
	printf("{\"sdp_budget_cases\":8,\"existing_safety_cases\":5,\"passed\":true}\n");
	return 0;
}
