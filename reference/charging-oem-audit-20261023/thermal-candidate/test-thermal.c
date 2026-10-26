/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include "mp2650-core.h"

static unsigned int cases;
struct state { struct sm_thermal_state thermal; int latched; };

static struct sm_sample good(void)
{
	return (struct sm_sample){ .valid = 1, .online = 1, .protection_ok = 1,
		.budget_ua = 500000, .temp_decic = 250, .pack_uv = 7600000,
		.cell1_uv = 3800000, .cell2_uv = 3800000 };
}

/* The proposed driver ordering. Does not access a device or perform writes. */
static int step(struct state *state, struct sm_sample s, int collect_error,
		int *enable)
{
	struct sm_target target = { 0 };
	enum sm_policy_reason reason = SM_POLICY_REASON_NONE;
	int held, ret = collect_error;

	if (!ret)
		ret = sm_policy_with_reason(&s, 4362500, 250000, 900000,
					    &target, &reason);
	held = sm_thermal_gate(&state->thermal, s.temp_decic,
		!collect_error && s.valid && s.online && s.protection_ok &&
		(!ret || sm_policy_reason_is_thermal(reason)));
	if (!ret && s.online && held) {
		ret = -ERANGE;
		reason = SM_POLICY_REASON_TEMPERATURE;
	}
	state->latched = sm_sample_latch(state->latched, ret,
		sm_policy_reason_is_thermal(reason), s.fault);
	*enable = !ret && !state->latched && target.enable;
	cases++;
	return ret;
}

static void expect_temp(struct state *state, int temp, int should_enable)
{
	struct sm_sample s = good();
	int enable;
	s.temp_decic = temp;
	step(state, s, 0, &enable);
	assert(enable == should_enable && !state->latched);
}

static void sequences(void)
{
	struct state state = { 0 };
	struct sm_sample s;
	int enable;
	expect_temp(&state, 250, 1);
	expect_temp(&state, 530, 0);
	expect_temp(&state, 529, 0);
	expect_temp(&state, 511, 0);
	expect_temp(&state, 510, 1);
	expect_temp(&state, 530, 0);
	expect_temp(&state, -30, 0);
	expect_temp(&state, -10, 0);
	expect_temp(&state, -1, 0);
	expect_temp(&state, 0, 1);
	expect_temp(&state, -21, 0);
	expect_temp(&state, 540, 0);
	expect_temp(&state, 520, 0);
	expect_temp(&state, 510, 1);
	/* A returned value cannot hide an already latched electrical failure. */
	state.latched = 1;
	s = good(); s.temp_decic = 540;
	assert(step(&state, s, 0, &enable) == -ERANGE && !enable && state.latched);
	s.temp_decic = 250;
	assert(step(&state, s, 0, &enable) == 0 && !enable && state.latched);
	/* Detach is already agreed by collect: no thermal error on offline data. */
	state = (struct state){ 0 };
	expect_temp(&state, 530, 0);
	s = good(); s.online = 0;
	assert(!step(&state, s, 0, &enable) && !enable && !state.latched);
	/* The actual collector may clear thermal history only at that agreed
	 * physical-detach branch; generic missing budgets must not clear it. */
	state.thermal = (struct sm_thermal_state){ 0 };
	s = good();
	assert(!step(&state, s, 0, &enable) && enable && !state.latched);
	/* A real acquisition failure while hot does not update history or recover. */
	state = (struct state){ 0 };
	expect_temp(&state, 530, 0);
	s = good();
	assert(step(&state, s, -EREMOTEIO, &enable) == -EREMOTEIO && !enable);
	assert(state.thermal.hold == SM_THERMAL_HOT && state.latched);
	assert(step(&state, s, 0, &enable) == 0 && !enable && state.latched);
	/* Exactly band OVP can recover, while actual REG14 remains a hard latch. */
	state = (struct state){ 0 };
	s = good(); s.cell1_uv = s.cell2_uv = 4300000; s.pack_uv = 8600000;
	assert(!step(&state, s, 0, &enable) && enable);
	s.temp_decic = 440;
	assert(step(&state, s, 0, &enable) == -EOVERFLOW && !enable && !state.latched);
	s.temp_decic = 250;
	assert(!step(&state, s, 0, &enable) && enable);
	s.temp_decic = 440; s.fault = 1;
	assert(step(&state, s, 0, &enable) == -EIO && !enable && state.latched);
	s.temp_decic = 250; s.fault = 0;
	assert(!step(&state, s, 0, &enable) && !enable && state.latched);
}

static void reasons_and_safety(void)
{
	struct sm_sample s;
	struct sm_target t;
	enum sm_policy_reason reason;
	int ret;
	/* Every original global hard-error domain wins over simultaneous heat. */
	for (int n = 0; n < 9; n++) {
		s = good(); s.temp_decic = 540;
		switch (n) {
		case 0: s.valid = 0; break;
		case 1: s.protection_ok = 0; break;
		case 2: s.cell1_uv = 1900000; break;
		case 3: s.cell1_uv = 4700000; break;
		case 4: s.pack_uv = 8000000; break;
		case 5: s.fault = 1; break;
		case 6: s.gauge_flags = 0x4000; break;
		case 7: s.session_seconds = 36000; break;
		case 8: s.budget_ua = 0; break;
		}
		ret = sm_policy_with_reason(&s, 4362500, 250000, 900000, &t, &reason);
		assert(ret && reason == SM_POLICY_REASON_NONE && !t.enable);
		assert(sm_sample_latch(0, ret, sm_policy_reason_is_thermal(reason), s.fault));
		cases++;
	}
	s = good(); s.temp_decic = 540;
	assert(sm_policy_with_reason(&s, 3700000, 250000, 900000, &t, &reason) == -ERANGE);
	assert(reason == SM_POLICY_REASON_NONE); cases++;
	/* Normal valid targets remain at or below every original temperature CV. */
	for (int temp = -20; temp < 530; temp++) {
		s = good(); s.temp_decic = temp;
		assert(!sm_policy_with_reason(&s, 4362500, 250000, 900000, &t, &reason));
		assert(reason == SM_POLICY_REASON_NONE && t.enable);
		assert(t.cell_uv <= (temp < 0 ? 3980000 : temp < 440 ? 4362500 : 4130000));
		assert(t.current_ua <= 250000 && t.input_ua <= 500000);
		cases++;
	}
	/* Invalid snapshots never mutate a previously empty thermal history. */
	struct sm_thermal_state thermal = { 0 };
	assert(!sm_thermal_gate(&thermal, 1000, 0)); cases++;
	assert(thermal.hold == SM_THERMAL_NONE);
	assert(sm_thermal_gate(&thermal, 530, 1)); cases++;
	assert(sm_thermal_gate(&thermal, 250, 0)); cases++;
	assert(thermal.hold == SM_THERMAL_HOT);
}

int main(void)
{
	sequences();
	reasons_and_safety();
	printf("{\"thermal_cases\":%u,\"passed\":true}\n", cases);
	return 0;
}
