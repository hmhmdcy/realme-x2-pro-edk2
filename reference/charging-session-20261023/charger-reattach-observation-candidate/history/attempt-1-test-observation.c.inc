/* Real header/poll/source fragment; fake OS boundary, no hardware IO. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "reattach-observation.h"
#include "../thermal-bands-candidate/oem-full-cycle.h"
#include "../thermal-bands-candidate/charge-cycle.h"

#define NS 1000000000ULL
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; };
struct notifier_block { int unused; };
struct sm_charger {
	int lock, paused;
	struct delayed_work work;
	struct sm_reattach_observation reattach;
	struct { int online, valid; } sample;
	struct notifier_block supply_notifier;
	void *psy, *input, *protection;
};
#define container_of(p, type, member) ((type *)((char *)(p) - offsetof(type, member)))
#define to_delayed_work(p) container_of(p, struct delayed_work, work)
#define READ_ONCE(x) (x)
#define PSY_EVENT_PROP_CHANGED 1
#define NOTIFY_DONE 0
static int queue_dummy;
#define system_wq (&queue_dummy)
static sm_observe_ns now_ns, advance_notify_ns;
static int step_ret, notify_result, held, steps, scheduled, notifications, expedited;
static unsigned int delay_ms;
static void mutex_lock(int *lock) { assert(!*lock && !held); *lock = held = 1; }
static void mutex_unlock(int *lock) { assert(*lock && held); *lock = held = 0; }
static sm_observe_ns ktime_get_boottime_ns(void) { return now_ns; }
static unsigned int msecs_to_jiffies(unsigned int ms) { return ms; }
static int schedule_delayed_work(struct delayed_work *work, unsigned int delay)
{ assert(work && held); scheduled++; delay_ms = delay; return 1; }
static int mod_delayed_work(void *queue, struct delayed_work *work, unsigned int delay)
{ assert(queue == system_wq && work && !held && delay == 0); expedited++; return 1; }
static void power_supply_changed(void *psy) { assert(psy && !held); notifications++; }
static int sm_step_locked(struct sm_charger *c)
{
	int source, ret = step_ret;
	sm_observe_ns now = now_ns;
	assert(held); steps++;
#include "actual-source.inc"
	return ret;
}
static bool sm_notification_locked(struct sm_charger *c)
{ assert(c && held); now_ns += advance_notify_ns; return notify_result; }
#include "actual-poll.inc"
#include "actual-notifier.inc"

static void reset(struct sm_charger *c)
{
	memset(c, 0, sizeof(*c));
	c->psy = c; c->input = &c->sample; c->protection = &c->reattach;
	now_ns = advance_notify_ns = 0;
	step_ret = notify_result = held = steps = scheduled = notifications = expedited = 0;
	delay_ms = 0;
}

static void poll(struct sm_charger *c, sm_observe_ns now, int online, int valid, int ret)
{
	now_ns = now; c->sample.online = online; c->sample.valid = valid; step_ret = ret;
	sm_poll(&c->work.work); assert(!held && !c->lock);
}

static void test_initial_unknown_and_real_edge(void)
{
	struct sm_reattach_observation s = { 0 };
	sm_reattach_source(&s, 0, 1); assert(!s.active);
	sm_reattach_source(&s, NS / 10, -1);
	sm_reattach_source(&s, NS / 5, 1); assert(!s.active);
	sm_reattach_source(&s, NS / 2, 0);
	sm_reattach_source(&s, NS * 3 / 4, -1); assert(s.off_ready);
	sm_reattach_source(&s, NS, 1);
	assert(s.active && !s.off_ready && s.until_ns == 4 * NS);
	assert(sm_reattach_delay_ms(&s, NS) == 250);
	puts("ok initial online/unknown inert; only retained real off followed by agreed on arms");
}

static void test_flap_deadline_and_fresh_rearm(void)
{
	struct sm_reattach_observation s = { 0 };
	sm_reattach_source(&s, 0, 0); sm_reattach_source(&s, NS, 1);
	for (unsigned int i = 1; i < 12; i++) {
		sm_reattach_source(&s, NS + i * NS / 4, i % 3 == 0 ? -1 : i % 2);
		assert(s.active && !s.off_ready && s.until_ns == 4 * NS);
	}
	/* An on at expiry cannot consume an off seen only inside the old window. */
	sm_reattach_source(&s, 4 * NS, 1);
	assert(!s.active && !s.off_ready && sm_reattach_delay_ms(&s, 4 * NS) == 1000);
	sm_reattach_source(&s, 4 * NS + NS / 10, 0);
	sm_reattach_source(&s, 4 * NS + NS / 5, 1);
	assert(s.active && s.until_ns == 7 * NS + NS / 5);
	puts("ok repeated/flapping/unknown observations do not extend deadline; fresh off after expiry can rearm");
}

static void test_expiry_long_gap_bad_clock_and_overflow(void)
{
	struct sm_reattach_observation s = { 0 };
	sm_reattach_source(&s, 0, 0); sm_reattach_source(&s, NS, 1);
	assert(sm_reattach_delay_ms(&s, 4 * NS - 1) == 1);
	assert(sm_reattach_delay_ms(&s, 4 * NS) == 1000 && !s.active);
	sm_reattach_source(&s, 5 * NS, 0); sm_reattach_source(&s, 6 * NS, 1);
	assert(sm_reattach_delay_ms(&s, 100 * NS) == 1000 && !s.active && !s.off_ready);
	sm_reattach_source(&s, 101 * NS, 0); sm_reattach_source(&s, 102 * NS, 1);
	assert(sm_reattach_delay_ms(&s, 101 * NS) == 1000 && !s.active && !s.off_ready);
	sm_reattach_source(&s, 102 * NS, 1); assert(!s.active);
	memset(&s, 0, sizeof(s));
	sm_reattach_source(&s, UINT64_MAX - NS, 0);
	sm_reattach_source(&s, UINT64_MAX - NS + 1, 1);
	assert(!s.active && !s.until_ns && sm_reattach_delay_ms(&s, UINT64_MAX) == 1000);
	puts("ok hard expiry/deadline clamp/long gap/backward clock/overflow never catch up or wrap");
}

static void test_actual_poll_source_semantics_and_notifications(void)
{
	struct sm_charger c; reset(&c); notify_result = 1;
	poll(&c, NS, 1, 0, -ENODATA); assert(delay_ms == 1000 && !c.reattach.active);
	poll(&c, 2 * NS, 0, 1, 0); assert(delay_ms == 1000 && c.reattach.off_ready);
	poll(&c, 2 * NS + NS / 10, 0, 0, -EIO); assert(c.reattach.off_ready && !c.reattach.active);
	/* sm_collect already agreed source and ACOK; budget error is NOT unknown off. */
	poll(&c, 3 * NS, 1, 0, -ENODATA);
	assert(delay_ms == 250 && c.reattach.until_ns == 6 * NS);
	assert(steps == 4 && scheduled == 4 && notifications == 4);
	poll(&c, 6 * NS, 1, 1, 0); assert(delay_ms == 1000 && !c.reattach.active);
	puts("ok actual poll/source expression preserves early unknown vs agreed on budget ENODATA and lock-outside notify");
}

static void test_actual_notifier_pause_and_elapsed_work(void)
{
	struct sm_charger c; reset(&c);
	poll(&c, 0, 0, 1, 0); poll(&c, NS, 1, 1, 0);
	struct sm_reattach_observation before = c.reattach;
	for (unsigned int i = 0; i < 100; i++)
		assert(sm_supply_changed(&c.supply_notifier, PSY_EVENT_PROP_CHANGED, c.input) == NOTIFY_DONE);
	assert(expedited == 100 && memcmp(&before, &c.reattach, sizeof(before)) == 0);
	c.paused = 1; int old_steps = steps, old_schedule = scheduled;
	sm_supply_changed(&c.supply_notifier, PSY_EVENT_PROP_CHANGED, c.input);
	poll(&c, 2 * NS, 0, 1, 0);
	assert(expedited == 100 && steps == old_steps && scheduled == old_schedule && !held);
	c.paused = 0; poll(&c, 10 * NS, 1, 1, 0);
	assert(delay_ms == 1000 && !c.reattach.active);
	/* A slow safety/notification step crossing expiry cannot requeue fast. */
	poll(&c, 11 * NS, 0, 1, 0); poll(&c, 12 * NS, 1, 1, 0);
	advance_notify_ns = NS;
	poll(&c, 14 * NS + NS / 2, 1, 1, 0);
	assert(delay_ms == 1000 && !c.reattach.active);
	puts("ok actual notifier never touches window; paused poll queues nothing; resume/slow work do not backfill");
}

static void test_existing_boottime_full_and_timeout(void)
{
	struct sm_oem_full_state full;
	struct sm_oem_full_sample sample = { .valid = 1, .source_known = 1, .online = 1,
		.protection_good = 1, .policy_good = 1, .temp_decic = 250,
		.policy_band_valid = 1, .policy_band = 4, .max_cell_uv = 4351000,
		.gauge_current_ua = 50000, .cell_target_uv = 4362500 };
	struct sm_charge_cycle cycle;
	sm_oem_full_init(&full); sm_cycle_init(&cycle, 100 * NS);
	for (unsigned int i = 0; i <= 20; i++) {
		sm_observe_ns t = 100 * NS + i * NS / 4;
		struct sm_oem_full_result result = sm_oem_full_step(&full, t, &sample);
		assert(!result.full && !result.stop_all);
		assert(full.sw_count == (i == 20 ? 2 : 1));
		assert(sm_cycle_update(&cycle, t, 1, 0) == i / 4);
	}
	assert(sm_cycle_update(&cycle, 36099 * NS, 1, 0) == 35999 && !cycle.timed_out);
	assert(sm_cycle_update(&cycle, 36100 * NS, 1, 0) == 36000 && cycle.timed_out);
	puts("ok actual unchanged Full5s and timeout BOOTTIME gates cannot accelerate at4Hz");
}

int main(void)
{
	test_initial_unknown_and_real_edge();
	test_flap_deadline_and_fresh_rearm();
	test_expiry_long_gap_bad_clock_and_overflow();
	test_actual_poll_source_semantics_and_notifications();
	test_actual_notifier_pause_and_elapsed_work();
	test_existing_boottime_full_and_timeout();
	puts("passed: six affected groups; no kernel/IO/device access");
	return 0;
}
