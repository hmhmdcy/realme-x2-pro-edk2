/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include "oem-full-cycle.h"

static unsigned int sequences, assertions;
#define NS(x) ((sm_full_ns)(x) * 1000000000ULL)
#define CHECK(x) do { int check_once = !!(x); if (!check_once) fprintf(stderr, "line %d: %s\n", __LINE__, #x); assert(check_once); assertions++; } while (0)

static struct sm_oem_full_sample good(void)
{
	return (struct sm_oem_full_sample){ .valid = 1, .source_known = 1,
		.online = 1, .protection_good = 1, .policy_good = 1,
		.temp_decic = 250, .max_cell_uv = 4351000,
		.gauge_current_ua = 110000, .cell_target_uv = 4362500 };
}

static void hardware_full(struct sm_oem_full_state *s, struct sm_oem_full_sample *in)
{
	sm_oem_full_init(s);
	in->hardware_full = 1;
	struct sm_oem_full_result r = sm_oem_full_step(s, 0, in);
	CHECK(r.entered_full && r.full && r.hold_charge_only && !r.stop_all);
	in->hardware_full = 0;
}

int main(void)
{
	struct sm_oem_full_state s;
	struct sm_oem_full_sample in;
	struct sm_oem_full_result r;
	int ua;

	sequences++;
	CHECK(sm_oem_gauge_current_ua(110, &ua) == 0 && ua == 110000);
	CHECK(sm_oem_gauge_current_ua(0xffff, &ua) == 0 && ua == -1000);
	CHECK(sm_oem_gauge_current_ua(0x8000, &ua) == 0 && ua == -32768000);
	CHECK(sm_oem_gauge_current_ua(0x7fff, &ua) == 0 && ua == 32767000);
	CHECK(sm_oem_gauge_current_ua(0x10000, &ua) == -EINVAL);
	CHECK(sm_oem_gauge_current_ua(0, NULL) == -EINVAL);

	/* OEM first sample counts as one; charging <=110mA qualifies on #6. */
	sequences++;
	sm_oem_full_init(&s); in = good();
	for (unsigned int i = 0; i < 6; i++) {
		r = sm_oem_full_step(&s, NS(i * 5), &in);
		CHECK(r.tick && !r.stop_all);
		CHECK(r.full == (i == 5));
	}
	CHECK(r.entered_full && r.cause == SM_FULL_SOFTWARE && r.hold_charge_only);

	/* Zero/discharging uses #11. The register sign is not an input cap. */
	sequences++;
	const int discharging[] = { 0, -1000, -110000 };
	for (unsigned int current = 0; current < 3; current++) {
		sm_oem_full_init(&s); in = good(); in.gauge_current_ua = discharging[current];
		for (unsigned int i = 0; i < 11; i++) {
			r = sm_oem_full_step(&s, NS(i * 5), &in);
			CHECK(r.full == (i == 10));
		}
	}

	/* It is one shared SW counter: sign branch changes do not reset it. */
	sequences++;
	sm_oem_full_init(&s); in = good(); in.gauge_current_ua = 0;
	for (unsigned int i = 0; i < 5; i++) sm_oem_full_step(&s, NS(i * 5), &in);
	in.gauge_current_ua = 110000;
	r = sm_oem_full_step(&s, NS(25), &in);
	CHECK(r.full && r.cause == SM_FULL_SOFTWARE);
	sm_oem_full_init(&s); in = good();
	for (unsigned int i = 0; i < 5; i++) sm_oem_full_step(&s, NS(i * 5), &in);
	in.gauge_current_ua = 0;
	r = sm_oem_full_step(&s, NS(25), &in);
	CHECK(!r.full && s.sw_count == 6);
	for (unsigned int i = 6; i < 11; i++) r = sm_oem_full_step(&s, NS(i * 5), &in);
	CHECK(r.full);

	/* Current >110mA or voltage == SW threshold breaks the strict > run. */
	sequences++;
	sm_oem_full_init(&s); in = good();
	for (unsigned int i = 0; i < 5; i++) sm_oem_full_step(&s, NS(i * 5), &in);
	in.gauge_current_ua = 110001;
	r = sm_oem_full_step(&s, NS(25), &in);
	CHECK(!r.full && s.sw_count == 0);
	in = good(); in.max_cell_uv = 4350000;
	r = sm_oem_full_step(&s, NS(30), &in);
	CHECK(!r.full && s.sw_count == 0 && r.sw_threshold_uv == 4350000);
	in.max_cell_uv = 4350001;
	for (unsigned int i = 0; i < 6; i++) r = sm_oem_full_step(&s, NS(35 + i * 5), &in);
	CHECK(r.full);

	/* Pure OEM voltage fallback is >=OEM CV+18mV, exactly four samples.
	 * These nominal inputs do not authorize increasing Linux's lower CV or
	 * bypassing policy OVP: caller policy_good must reject such an unsafe
	 * current state in production, even though the reference branch is tested.
	 */
	sequences++;
	sm_oem_full_init(&s); in = good(); in.gauge_current_ua = 500000;
	in.max_cell_uv = 4418000;
	for (unsigned int i = 0; i < 4; i++) {
		r = sm_oem_full_step(&s, NS(i * 5), &in);
		CHECK(r.full == (i == 3) && r.voltage_threshold_uv == 4418000);
	}
	CHECK(r.cause == SM_FULL_VOLTAGE);
	sm_oem_full_init(&s); in.max_cell_uv = 4417999;
	for (unsigned int i = 0; i < 4; i++) r = sm_oem_full_step(&s, NS(i * 5), &in);
	CHECK(!r.full && s.voltage_count == 0);

	/* All six real temperature bands have the correct SW/voltage thresholds. */
	sequences++;
	const int temp[] = { -20, 0, 50, 120, 160, 440 };
	const int cv[] = { 3975000, 4362500, 4362500, 4362500, 4362500, 4125000 };
	const int sw[] = { 3930000, 4350000, 4350000, 4350000, 4350000, 4080000 };
	const int recharge[] = { 3675000, 4162500, 4262500, 4262500, 4262500, 4025000 };
	for (unsigned int band = 0; band < 6; band++) {
		sm_oem_full_init(&s); in = good();
		in.temp_decic = temp[band]; in.cell_target_uv = cv[band];
		in.max_cell_uv = sw[band] + 1000;
		for (unsigned int i = 0; i < 6; i++) r = sm_oem_full_step(&s, NS(i * 5), &in);
		CHECK(r.full && r.cause == SM_FULL_SOFTWARE && r.sw_threshold_uv == sw[band]);
		CHECK(r.recharge_threshold_uv == recharge[band]);
		in.max_cell_uv = recharge[band];
		for (unsigned int i = 1; i <= 6; i++) {
			r = sm_oem_full_step(&s, NS(25 + i * 5), &in);
			CHECK(r.recharge == (i == 6));
			CHECK(r.full == (i != 6));
		}
		CHECK(!r.stop_all && !r.hold_charge_only && !s.full);
	}

	/* Fresh low observations must be continuous; equality qualifies. */
	sequences++;
	in = good(); hardware_full(&s, &in); in.max_cell_uv = 4262500;
	for (unsigned int i = 1; i <= 5; i++) r = sm_oem_full_step(&s, NS(i * 5), &in);
	CHECK(r.full && !r.recharge && s.recharge_count == 5);
	in.max_cell_uv++;
	r = sm_oem_full_step(&s, NS(26), &in); /* Non-tick known contradiction. */
	CHECK(s.recharge_count == 0 && !r.tick && r.hold_charge_only);
	in.max_cell_uv--;
	r = sm_oem_full_step(&s, NS(30), &in);
	CHECK(!r.recharge && s.recharge_count == 1);

	/* Prohibited recharge never leaves a ready-to-enable count behind. */
	sequences++;
	in = good(); hardware_full(&s, &in); in.max_cell_uv = 4262500;
	for (unsigned int i = 1; i <= 5; i++) sm_oem_full_step(&s, NS(i * 5), &in);
	in.recharge_forbidden = 1;
	for (unsigned int i = 6; i < 15; i++) {
		r = sm_oem_full_step(&s, NS(i * 5), &in);
		CHECK(r.full && !r.recharge && s.recharge_count == 0);
	}
	in.recharge_forbidden = 0;
	r = sm_oem_full_step(&s, NS(75), &in);
	CHECK(!r.recharge && s.recharge_count == 1);

	/* Strict minimum 5s sample spacing at a faster 1s driver poll. */
	sequences++;
	sm_oem_full_init(&s); in = good();
	for (unsigned int second = 0; second < 25; second++) {
		r = sm_oem_full_step(&s, NS(second), &in);
		CHECK(!r.full && r.tick == (second % 5 == 0));
	}
	r = sm_oem_full_step(&s, NS(25), &in);
	CHECK(r.full && r.tick);
	/* Scheduling jitter is allowed, and a long gap never catches up. */
	sequences++;
	sm_oem_full_init(&s); in = good();
	for (unsigned int i = 0; i < 6; i++) {
		r = sm_oem_full_step(&s, i * 5010000000ULL, &in);
		CHECK(r.full == (i == 5));
	}
	sm_oem_full_init(&s);
	for (unsigned int i = 0; i < 5; i++) sm_oem_full_step(&s, NS(i * 5), &in);
	r = sm_oem_full_step(&s, NS(100), &in);
	CHECK(!r.full && r.tick && s.sw_count == 1);

	/* Every kind of unknown/incomplete/unsafe sample stops immediately and
	 * breaks Full/recharge streaks. None clears an established logical Full.
	 */
	sequences++;
	for (unsigned int failure = 0; failure < 10; failure++) {
		in = good(); hardware_full(&s, &in); in.max_cell_uv = 4262500;
		for (unsigned int i = 1; i <= 5; i++) sm_oem_full_step(&s, NS(i * 5), &in);
		switch (failure) {
		case 0: in.valid = 0; break;
		case 1: in.source_known = 0; break;
		case 2: in.protection_good = 0; break;
		case 3: in.policy_good = 0; break;
		case 4: in.hard_latched = 1; break;
		case 5: in.timeout = 1; break;
		case 6: in.gauge_flags = SM_FULL_OCA; break;
		case 7: in.gauge_flags = SM_FULL_TCA; break;
		case 8: in.temp_decic = 530; break;
		default: in.cell_target_uv = 4500001; break;
		}
		r = sm_oem_full_step(&s, NS(26), &in);
		CHECK(r.stop_all && r.full && !r.recharge && !r.entered_full && !r.hold_charge_only);
		CHECK(s.full && s.recharge_count == 0);
		in = good(); in.max_cell_uv = 4262500;
		r = sm_oem_full_step(&s, NS(30), &in);
		CHECK(r.full && !r.recharge && s.recharge_count == 1);
	}

	/* TCA alone/with FC/hardwareFull is neither normal Full nor a restart. */
	sequences++;
	sm_oem_full_init(&s); in = good();
	in.gauge_flags = SM_FULL_TCA | 0x20; in.hardware_full = 1;
	r = sm_oem_full_step(&s, 0, &in);
	CHECK(r.stop_all && r.block == SM_FULL_TCA_HOLD && !r.full && !s.full);
	CHECK(in.gauge_flags == (SM_FULL_TCA | 0x20));
	/* FC without threshold/hardware evidence cannot declare Full either. */
	in = good(); in.max_cell_uv = 4200000; in.gauge_flags = 0x20;
	for (unsigned int i = 1; i <= 12; i++) r = sm_oem_full_step(&s, NS(i * 5), &in);
	CHECK(!r.full && !r.entered_full);

	/* A real dual-source detach resets state; UNKNOWN online=0 does not. */
	sequences++;
	in = good(); hardware_full(&s, &in);
	in.source_known = 0; in.online = 0;
	r = sm_oem_full_step(&s, NS(5), &in);
	CHECK(r.stop_all && r.full && s.full);
	in.source_known = 1;
	r = sm_oem_full_step(&s, NS(10), &in);
	CHECK(r.stop_all && !r.full && !s.full && s.band == -1);

	/* Bad BOOTTIME input cannot underflow into a timer/count authorization. */
	sequences++;
	sm_oem_full_init(&s); in = good();
	sm_oem_full_step(&s, NS(100), &in);
	r = sm_oem_full_step(&s, NS(99), &in);
	CHECK(r.stop_all && r.block == SM_FULL_BAD_CLOCK && !r.full && s.sw_count == 0);

	/* Changing bands breaks a partial threshold run, preserving safe hold. */
	sequences++;
	in = good(); hardware_full(&s, &in); in.max_cell_uv = 4160000;
	for (unsigned int i = 1; i <= 5; i++) sm_oem_full_step(&s, NS(i * 5), &in);
	in.temp_decic = 0;
	r = sm_oem_full_step(&s, NS(30), &in);
	CHECK(r.full && !r.recharge && s.recharge_count == 1);

	printf("{\"sequences\":%u,\"assertions\":%u,\"passed\":true}\n", sequences, assertions);
	return 0;
}
