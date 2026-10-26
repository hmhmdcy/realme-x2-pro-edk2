/* SPDX-License-Identifier: GPL-2.0-only */
/* Boundary fakes only. The tested sm_step_locked body is extracted verbatim. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <mp2650-core.h>
#include <charge-cycle.h>
#include <oem-full-cycle.h>
typedef uint64_t u64;

typedef uint64_t ktime_t;
static uint64_t clock_ns;
static bool control = true;
static unsigned int assertions, sequences;
#define CHECK(x) do { int check_once = !!(x); if (!check_once) fprintf(stderr, "failed line %d: %s\n", __LINE__, #x); assert(check_once); assertions++; } while (0)
#define NS(x) ((uint64_t)(x) * 1000000000ULL)
#define dev_warn_ratelimited(...) ((void)0)
static uint64_t ktime_get_boottime(void) { return clock_ns; }
static uint64_t ktime_get_boottime_ns(void) { return clock_ns; }

struct bus {
	unsigned int regs[256], writes, reads;
	int fail_stop_write;
};
struct sm_charger {
	struct sm_io io;
	struct sm_sample sample;
	struct sm_target target;
	int cell_ceiling_uv, current_cap_ua, input_cap_ua;
	int last_error, stop_error;
	bool auto_requested, latched, paused, sample_full, source_inhibit;
	ktime_t sampled_at;
	struct sm_charge_cycle cycle;
	struct sm_oem_full_state full_state;
	struct sm_oem_full_result full_result;
	bool full_holding, hold_requested, gauge_charge_stop;
	struct sm_thermal_state thermal;
	enum sm_policy_reason thermal_reason;
};
struct frame {
	struct sm_sample sample;
	int collect_error;
	bool full, source_inhibit;
};
static struct frame next;

static int read_register(void *ctx, unsigned int reg)
{
	struct bus *b = ctx;
	b->reads++;
	assert(reg < 256);
	return b->regs[reg];
}
static int write_register(void *ctx, unsigned int reg, unsigned int value)
{
	struct bus *b = ctx;
	assert(reg < 256 && value < 256);
	b->writes++;
	if (reg == 8 && b->fail_stop_write && (value & 0x18) == 8)
		return -EREMOTEIO;
	b->regs[reg] = value;
	return 0;
}
static int sm_collect(struct sm_charger *c, struct sm_sample *sample)
{
	*sample = next.sample;
	c->source_inhibit = next.source_inhibit;
	c->sample_full = next.full;
	/* These are the real collect()'s agreed physical-detach side effects.
	 * Unknown source (invalid/error), even online=0, never runs this block.
	 */
	if (!next.collect_error && sample->valid && !sample->online) {
		sm_cycle_update(&c->cycle, clock_ns, 0, 0);
		c->latched = false;
		c->thermal.hold = SM_THERMAL_NONE;
		sm_oem_full_init(&c->full_state);
	}
	return next.collect_error;
}

#include "sm-step-extracted.inc"

static struct frame normal(void)
{
	return (struct frame){ .sample = { .valid = 1, .online = 1,
		.protection_ok = 1, .budget_ua = 500000, .temp_decic = 250,
		.pack_uv = 8600000, .cell1_uv = 4300000, .cell2_uv = 4300000 } };
}
static void initialize(struct sm_charger *c, struct bus *bus)
{
	*c = (struct sm_charger){ .cell_ceiling_uv = 4362500,
		.current_cap_ua = 250000, .input_cap_ua = 900000,
		.auto_requested = true };
	*bus = (struct bus){ .regs = {
		[0] = 10, [0x0f] = 10, [2] = 5, [3] = 0x31,
		[4] = 0x68, [5] = 0, [7] = 0, [8] = 0x16, [9] = 0x48 } };
	c->io = (struct sm_io){ bus, read_register, write_register };
	clock_ns = 0;
	sm_cycle_init(&c->cycle, clock_ns);
	sm_oem_full_init(&c->full_state);
	next = normal();
	CHECK(sm_step_locked(c) == 0 && c->target.enable && !c->latched);
	CHECK(bus->writes == 0); /* Identical settings do not toggle CHG_EN. */
}
static int at(struct sm_charger *c, unsigned long long seconds, struct frame f)
{
	clock_ns = NS(seconds);
	next = f;
	return sm_step_locked(c);
}
static int stopped(const struct bus *bus) { return (bus->regs[8] & 0x18) == 8; }
static int enabled(const struct bus *bus) { return (bus->regs[8] & 0x18) == 0x10; }

int main(void)
{
	struct sm_charger c;
	struct bus bus;
	struct frame f;
	_Static_assert(SM_OEM_MAX_SECONDS == SM_CYCLE_LIMIT_SECONDS, "cycle/OEM limit drift");

	/* Hot stop, hysteresis hold, and valid warm recovery. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.temp_decic = 530;
	CHECK(at(&c, 10, f) == -ERANGE && !c.latched && stopped(&bus));
	CHECK(c.thermal_reason == SM_POLICY_REASON_TEMPERATURE && c.thermal.hold == SM_THERMAL_HOT);
	f.sample.temp_decic = 520; f.sample.cell1_uv = f.sample.cell2_uv = 4100000; f.sample.pack_uv = 8200000;
	CHECK(at(&c, 11, f) == -ERANGE && !c.latched && !c.target.enable && stopped(&bus));
	f.sample.temp_decic = 510;
	CHECK(at(&c, 12, f) == 0 && !c.latched && c.target.enable && enabled(&bus));
	CHECK(c.thermal.hold == SM_THERMAL_NONE && c.thermal_reason == SM_POLICY_REASON_NONE);

	/* Cold stop and OEM 2 C return threshold. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.temp_decic = -21;
	CHECK(at(&c, 10, f) == -ERANGE && !c.latched && stopped(&bus));
	f.sample.temp_decic = -1; f.sample.cell1_uv = f.sample.cell2_uv = 3900000; f.sample.pack_uv = 7800000;
	CHECK(at(&c, 11, f) == -ERANGE && !c.latched && stopped(&bus));
	f.sample.temp_decic = 0;
	CHECK(at(&c, 12, f) == 0 && !c.latched && enabled(&bus));

	/* Warm-band voltage inhibit is recoverable; normal cells can cool back. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.temp_decic = 450;
	CHECK(at(&c, 10, f) == -EOVERFLOW && !c.latched && stopped(&bus));
	CHECK(c.thermal_reason == SM_POLICY_REASON_BAND_OVP);
	f.sample.cell1_uv = f.sample.cell2_uv = 4130000; f.sample.pack_uv = 8260000;
	CHECK(at(&c, 11, f) == 0 && !c.latched && enabled(&bus));
	CHECK(c.target.cell_uv == 4125000);
	CHECK(at(&c, 12, normal()) == 0 && c.target.cell_uv == 4362500 && enabled(&bus));

	/* A prior real fault remains across thermal hold and temperature recovery. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.fault = 1;
	CHECK(at(&c, 10, f) == -EIO && c.latched && stopped(&bus));
	f = normal(); f.sample.temp_decic = 530;
	CHECK(at(&c, 11, f) == -ERANGE && c.latched && stopped(&bus));
	CHECK(at(&c, 12, normal()) == 0 && c.latched && !c.target.enable && stopped(&bus));

	/* MAC/bus failure while thermally inhibited cannot masquerade as thermal. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.temp_decic = 530;
	CHECK(at(&c, 10, f) == -ERANGE && !c.latched);
	f = normal(); f.sample.valid = 0; f.collect_error = -EREMOTEIO;
	CHECK(at(&c, 11, f) == -EREMOTEIO && c.latched && stopped(&bus));
	CHECK(c.thermal_reason == SM_POLICY_REASON_NONE && c.thermal.hold == SM_THERMAL_HOT);
	CHECK(at(&c, 12, normal()) == 0 && c.latched && !c.target.enable && stopped(&bus));

	/* A failed stop is not pardoned by an otherwise recoverable thermal reason. */
	sequences++;
	initialize(&c, &bus);
	bus.fail_stop_write = 1;
	f = normal(); f.sample.temp_decic = 530;
	CHECK(at(&c, 10, f) == -ERANGE && c.latched && c.stop_error == -EREMOTEIO);
	CHECK(!c.target.enable && !stopped(&bus)); /* No false hardware-stop claim. */
	bus.fail_stop_write = 0;
	CHECK(at(&c, 11, normal()) == 0 && c.latched && stopped(&bus) && !c.target.enable);

	/* Full may remain attached for days, then recharge with a fresh period. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.full = true;
	CHECK(at(&c, 100, f) == 0 && c.sample.session_seconds == 0);
	CHECK(c.full_holding && c.hold_requested && !c.target.enable && (bus.regs[8] & 0x18) == 0);
	CHECK(at(&c, 86400, f) == 0 && c.sample.session_seconds == 0 && !c.cycle.timed_out);
	CHECK(at(&c, 172800, f) == 0 && c.sample.session_seconds == 0 && !c.latched);
	f = normal(); f.sample.cell1_uv = f.sample.cell2_uv = 4262000; f.sample.pack_uv = 8524000;
	for (unsigned int i = 1; i <= 5; i++)
		CHECK(at(&c, 172800 + i * 5, f) == 0 && c.full_holding && !c.target.enable);
	CHECK(at(&c, 172830, f) == 0 && c.full_result.recharge && !c.full_holding && enabled(&bus));
	CHECK(at(&c, 172831, f) == 0 && c.sample.session_seconds == 1 && enabled(&bus));

	/* Timeout is an established fault; later Full/AUTO cannot clear it. */
	sequences++;
	initialize(&c, &bus);
	CHECK(at(&c, 36000, normal()) == -ETIME && c.cycle.timed_out && c.latched && stopped(&bus));
	f = normal(); f.full = true;
	CHECK(at(&c, 36001, f) == -ETIME && c.cycle.timed_out && c.latched && stopped(&bus));
	c.latched = false; /* Emulate the existing explicit AUTO recovery request. */
	CHECK(at(&c, 36002, f) == -ETIME && c.latched && stopped(&bus));

	/* Fresh Full cannot reset the timer while the thermal hysteresis holds. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.temp_decic = 530;
	CHECK(at(&c, 100, f) == -ERANGE && c.sample.session_seconds == 100);
	f.full = true; f.sample.temp_decic = 520;
	f.sample.cell1_uv = f.sample.cell2_uv = 4100000; f.sample.pack_uv = 8200000;
	CHECK(at(&c, 110, f) == -ERANGE && c.sample.session_seconds == 110 && c.cycle.anchor_ns == 0);
	f.sample.temp_decic = 510;
	CHECK(at(&c, 120, f) == 0 && c.sample.session_seconds == 0 && c.cycle.anchor_ns == NS(120));

	/* Early source failure online=0 means UNKNOWN, not physical detach. */
	sequences++;
	initialize(&c, &bus);
	f = (struct frame){ .collect_error = -ENODATA, .source_inhibit = true };
	CHECK(at(&c, 37, f) == -ENODATA && c.cycle.attached && c.cycle.anchor_ns == 0);
	CHECK(c.sample.session_seconds == 37 && !c.latched && stopped(&bus));
	CHECK(at(&c, 50, normal()) == 0 && c.sample.session_seconds == 50 && enabled(&bus));

	/* Source budget loss after the agreed online read also preserves the period. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.valid = 0; f.sample.budget_ua = 0;
	f.collect_error = -ENODATA; f.source_inhibit = true;
	CHECK(at(&c, 37, f) == -ENODATA && !c.latched && stopped(&bus));
	CHECK(c.sample.session_seconds == 37 && c.cycle.anchor_ns == 0);
	CHECK(at(&c, 50, normal()) == 0 && c.sample.session_seconds == 50 && enabled(&bus));

	/* Global voltage/fault errors simultaneous with heat are still hard faults. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.temp_decic = 530; f.sample.cell1_uv = 4700000; f.sample.pack_uv = 9000000;
	CHECK(at(&c, 10, f) == -ERANGE && c.latched && c.thermal_reason == SM_POLICY_REASON_NONE);
	CHECK(at(&c, 11, normal()) == 0 && c.latched && stopped(&bus));

	/* A physical detach clears Full/cycle/fault and stays a normal stop. */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.full = true;
	CHECK(at(&c, 1, f) == 0 && c.full_holding);
	c.latched = true;
	f = (struct frame){ .sample = { .valid = 1, .protection_ok = 1 } };
	CHECK(at(&c, 2, f) == 0 && !c.latched && !c.target.enable && stopped(&bus));
	CHECK(!c.full_state.full && !c.cycle.attached && !c.cycle.timed_out && !c.full_holding);

	/* The sixth new software-Full sample ends an unexpired period before
	 * this poll's 36000s accumulation, matching OEM Full-before-time order.
	 */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.cell1_uv = f.sample.cell2_uv = 4351000;
	f.sample.pack_uv = 8702000; f.sample.gauge_current_ua = 110000;
	for (unsigned int i = 0; i < 5; i++)
		CHECK(at(&c, 35975 + i * 5, f) == 0 && !c.full_state.full && !c.cycle.timed_out);
	CHECK(at(&c, 36000, f) == 0 && c.full_state.full && c.full_result.entered_full);
	CHECK(c.sample.session_seconds == 0 && !c.cycle.timed_out && !c.latched);
	CHECK(c.full_holding && !c.target.enable && (bus.regs[8] & 0x18) == 0);

	/* Hardware termination between software ticks + lower budget must go
	 * straight to charge hold, never through ordinary sm_apply CHG enable.
	 */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.full = true; f.sample.budget_ua = 100000;
	CHECK(at(&c, 1, f) == 0 && c.full_holding && !c.target.enable);
	CHECK(bus.regs[0] == 2 && bus.regs[0x0f] == 2 && (bus.regs[8] & 0x18) == 0);

	/* TCA is a raw preserved stop request and can recover automatically;
	 * OCA/global voltage/old timeout keep their stronger hard-fault meaning.
	 */
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.gauge_flags = 0x4000;
	CHECK(at(&c, 10, f) == -EAGAIN && c.gauge_charge_stop && !c.latched && stopped(&bus));
	CHECK(c.sample.gauge_flags == 0x4000 && !c.full_state.full);
	CHECK(at(&c, 11, normal()) == 0 && !c.gauge_charge_stop && !c.latched && enabled(&bus));
	f.sample.gauge_flags = 0xc000;
	CHECK(at(&c, 12, f) == -EIO && c.latched && !c.gauge_charge_stop && stopped(&bus));
	CHECK(at(&c, 13, normal()) == 0 && c.latched && stopped(&bus));
	f.sample.gauge_flags = 0x4000;
	CHECK(at(&c, 14, f) == -EAGAIN && c.latched && c.gauge_charge_stop && stopped(&bus));
	sequences++;
	initialize(&c, &bus);
	f = normal(); f.sample.gauge_flags = 0x4000; f.sample.cell1_uv = 4700000; f.sample.pack_uv = 9000000;
	CHECK(at(&c, 10, f) == -ERANGE && c.latched && !c.gauge_charge_stop && stopped(&bus));

	/* Hold transaction failures latch even when Full itself is normal. */
	sequences++;
	initialize(&c, &bus);
	bus.fail_stop_write = 1;
	f = normal(); f.full = true; f.sample.budget_ua = 100000;
	CHECK(at(&c, 10, f) == -EREMOTEIO && c.latched && !c.full_holding && !c.target.enable);
	bus.fail_stop_write = 0;
	CHECK(at(&c, 11, normal()) == 0 && c.latched && stopped(&bus) && !c.full_holding);

	/* TCA cannot replace an established timeout with a recoverable request. */
	sequences++;
	initialize(&c, &bus);
	CHECK(at(&c, 36000, normal()) == -ETIME && c.cycle.timed_out && c.latched);
	f = normal(); f.sample.gauge_flags = 0x4000;
	CHECK(at(&c, 36001, f) == -ETIME && c.cycle.timed_out && c.latched && !c.gauge_charge_stop);
	CHECK(c.sample.gauge_flags == 0x4000 && stopped(&bus) && !c.full_state.full);

	printf("{\"integration_sequences\":%u,\"assertions\":%u,\"passed\":true}\n", sequences, assertions);
	return 0;
}
