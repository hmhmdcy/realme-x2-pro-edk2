/* Host harness compiles the actual candidate notification/poll/resume bodies.
 * Kernel transport and workqueue boundaries are simulated; no hardware claim.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "charging-notify.h"

enum { POWER_SUPPLY_HEALTH_GOOD = 1, POWER_SUPPLY_HEALTH_UNSPEC_FAILURE = 5,
       POWER_SUPPLY_PROP_STATUS = 0, BATTERY_CHARGING = 1, BATTERY_DISCHARGING = 2,
       BATTERY_FULL = 4 };
struct work_struct { int dummy; };
struct delayed_work { struct work_struct work; };
struct mutex { bool held; };
struct power_supply { int unused; };
struct sm_sample {
	int valid, online, protection_ok, budget_ua, temp_decic;
	int pack_uv, cell1_uv, cell2_uv, gauge_flags, fault;
	unsigned int session_seconds;
};
struct sm_target { int enable, input_ua, current_ua, cell_uv; };
struct sm_charger {
	struct power_supply *psy, *battery;
	struct mutex lock;
	struct delayed_work work;
	struct sm_sample sample;
	struct sm_target target;
	int last_error, stop_error;
	bool auto_requested, latched, paused, source_inhibit;
	struct sm_notify_state notified;
	bool notified_valid;
};
struct device { struct sm_charger *data; };
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
#define to_delayed_work(ptr) container_of(ptr, struct delayed_work, work)
static void *system_wq;
static struct sm_charger *active;
static struct power_supply battery, charger;
static int current_reg, after_step_reg, battery_status, battery_error;
static int steps, reads, battery_reads, queues, notifications, cases;
static char trace[1024];
static size_t trace_at;
static void mark(char letter) { assert(trace_at + 1 < sizeof(trace)); trace[trace_at++] = letter; trace[trace_at] = 0; }
static void mutex_lock(struct mutex *lock) { assert(!lock->held); lock->held = true; }
static void mutex_unlock(struct mutex *lock) { assert(lock->held); lock->held = false; }
static unsigned int msecs_to_jiffies(unsigned int milliseconds) { return milliseconds; }
static int sm_step_locked(struct sm_charger *c)
{
	assert(c == active && c->lock.held);
	steps++; mark('S'); current_reg = after_step_reg;
	return c->last_error;
}
static int sm_read(void *ctx, unsigned int reg)
{
	assert(ctx == active && active->lock.held && reg == 0x13);
	reads++; mark('R'); return current_reg;
}
static int sm_psy_int(struct power_supply *psy, int property, int *value)
{
	assert(psy == &battery && property == POWER_SUPPLY_PROP_STATUS && active->lock.held);
	battery_reads++; mark('B');
	if (!battery_error) *value = battery_status;
	return battery_error;
}
static int schedule_delayed_work(struct delayed_work *work, unsigned int delay)
{
	assert(work == &active->work && delay == 1000 && active->lock.held);
	queues++; mark('Q'); return 1;
}
static void power_supply_changed(struct power_supply *psy)
{
	assert(psy == &charger && !active->lock.held);
	notifications++; mark('N');
}
static struct sm_charger *dev_get_drvdata(struct device *dev) { return dev->data; }
static int mod_delayed_work(void *queue, struct delayed_work *work, unsigned int delay)
{
	assert(queue == system_wq && work == &active->work && delay == 0 && active->lock.held);
	queues++; mark('M'); return 1;
}

static bool sm_notification_locked(struct sm_charger *c)
{
	struct sm_notify_state state = {
		.health = c->last_error || c->latched || c->stop_error ?
			POWER_SUPPLY_HEALTH_UNSPEC_FAILURE : POWER_SUPPLY_HEALTH_GOOD,
		.error = c->last_error,
		.stop_error = c->stop_error,
		.latched = c->latched,
		.source_inhibit = c->source_inhibit,
		.auto_requested = c->auto_requested,
		.valid = c->sample.valid,
		.online = c->sample.online,
		.protection_ok = c->sample.protection_ok,
		.fault = c->sample.fault,
		.target_enable = c->target.enable,
		.input_ua = c->target.input_ua,
		.current_ua = c->target.current_ua,
		.cell_uv = c->target.cell_uv,
	};
	bool changed;
	int reg;

	/* Sample after sm_step_locked() has completed any hardware writes. */
	reg = sm_read(c, 0x13);
	if (reg < 0)
		state.charger_error = reg;
	else
		state.charger_status = reg & 0x0e; /* ONLINE and CHG_STAT only */
	state.battery_error = sm_psy_int(c->battery, POWER_SUPPLY_PROP_STATUS,
				       &state.battery_status);
	changed = !c->notified_valid || sm_notify_changed(&c->notified, &state);
	c->notified = state;
	c->notified_valid = true;
	return changed;
}

static void sm_poll(struct work_struct *work)
{
	struct sm_charger *c = container_of(to_delayed_work(work),
					 struct sm_charger, work);
	bool notify = false;

	mutex_lock(&c->lock);
	if (c->paused) goto out;
	sm_step_locked(c);
	notify = sm_notification_locked(c);
	schedule_delayed_work(&c->work, msecs_to_jiffies(1000));
out:
	mutex_unlock(&c->lock);
	if (notify)
		power_supply_changed(c->psy);
}

static int sm_resume(struct device *dev)
{
	struct sm_charger *c = dev_get_drvdata(dev);

	mutex_lock(&c->lock);
	c->paused = false;
	/* The first fresh post-resume sample is always reported. */
	c->notified_valid = false;
	mod_delayed_work(system_wq, &c->work, 0);
	mutex_unlock(&c->lock);
	return 0;
}

static void reset(struct sm_charger *c)
{
	*c = (struct sm_charger){ .psy = &charger, .battery = &battery,
		.sample = { .valid = 1, .online = 1, .protection_ok = 1 },
		.target = { 1, 100000, 250000, 4362500 }, .auto_requested = true };
	active = c;
	current_reg = 0; after_step_reg = 0x1b;
	battery_status = BATTERY_DISCHARGING; battery_error = 0;
	steps = reads = battery_reads = queues = notifications = 0;
	trace_at = 0; trace[0] = 0;
}
static void poll(struct sm_charger *c)
{
	trace_at = 0; trace[0] = 0;
	sm_poll(&c->work.work);
	assert(!c->lock.held);
}
static void expect_change(struct sm_charger *c)
{
	int old = notifications;
	poll(c); assert(notifications == old + 1);
	poll(c); assert(notifications == old + 1);
	cases++;
}

int main(void)
{
	struct sm_charger c;
	struct device dev = { &c };
	struct sm_notify_state a = { 0 }, b = { 0 };
	reset(&c);
	poll(&c);
	assert(!strcmp(trace, "SRBQN"));
	assert(c.notified.charger_status == (0x1b & 0x0e));
	assert(c.notified.battery_status == BATTERY_DISCHARGING);
	assert(c.notified.health == POWER_SUPPLY_HEALTH_GOOD);
	assert(notifications == 1 && steps == 1 && reads == 1 && battery_reads == 1);
	cases++;
	/* Stable operation still performs every safety step and STATUS read. */
	for (int i = 0; i < 100; i++) {
		c.sample.temp_decic++; c.sample.pack_uv += 1000;
		c.sample.cell1_uv += 1000; c.sample.cell2_uv -= 1000;
		c.sample.session_seconds++; c.sample.gauge_flags++;
		poll(&c); assert(!strcmp(trace, "SRBQ"));
	}
	assert(notifications == 1 && steps == 101 && reads == 101 && battery_reads == 101);
	cases++;
	/* ADC/other status bits never create 1Hz notification churn. */
	after_step_reg ^= 0xf1; poll(&c); assert(notifications == 1); cases++;
	/* Real battery status is independent of the charger's switch state. */
	battery_status = BATTERY_CHARGING; expect_change(&c);
	battery_status = BATTERY_FULL; expect_change(&c);
	battery_status = BATTERY_DISCHARGING; expect_change(&c);
	/* Each read error is reported once, then recovery is reported once. */
	battery_error = -EIO; expect_change(&c);
	assert(c.notified.battery_error == -EIO && c.notified.battery_status == 0);
	battery_error = -ENODEV; expect_change(&c);
	battery_error = 0; expect_change(&c);
	after_step_reg = -EREMOTEIO; expect_change(&c);
	assert(c.notified.charger_error == -EREMOTEIO && c.notified.charger_status == 0);
	/* Notification-only transport errors must not mutate safety state. */
	assert(c.last_error == 0 && c.stop_error == 0 && !c.latched);
	assert(c.target.enable == 1 && c.auto_requested); cases++;
	after_step_reg = 0x1b; expect_change(&c);
	after_step_reg = 0; expect_change(&c);
	after_step_reg = 0x1b; expect_change(&c);
	after_step_reg = 0x0e; expect_change(&c);
	c.last_error = -EAGAIN; expect_change(&c);
	c.source_inhibit = true; expect_change(&c);
	c.last_error = 0; c.source_inhibit = false; expect_change(&c);
	c.stop_error = -EIO; expect_change(&c);
	c.stop_error = 0; expect_change(&c);
	c.latched = true; expect_change(&c);
	c.latched = false; expect_change(&c);
	c.auto_requested = false; expect_change(&c);
	c.auto_requested = true; expect_change(&c);
	c.target.enable = 0; expect_change(&c);
	c.target.enable = 1; expect_change(&c);
	c.target.input_ua = 500000; expect_change(&c);
	c.target.current_ua = 300000; expect_change(&c);
	c.target.cell_uv = 3980000; expect_change(&c);
	c.sample.valid = 0; expect_change(&c);
	c.sample.online = 0; expect_change(&c);
	c.sample.protection_ok = 0; expect_change(&c);
	c.sample.fault = 1; expect_change(&c);
	/* Paused work does no sampling, queueing, or stale notification. */
	c.paused = true;
	int before_steps = steps, before_reads = reads, before_battery = battery_reads;
	int before_queues = queues, before_notifications = notifications;
	poll(&c); assert(trace[0] == 0);
	assert(steps == before_steps && reads == before_reads && battery_reads == before_battery);
	assert(queues == before_queues && notifications == before_notifications); cases++;
	/* Resume queues immediately and invalidates exactly one notification. */
	assert(sm_resume(&dev) == 0);
	assert(!c.paused && !c.notified_valid && queues == before_queues + 1);
	poll(&c); assert(notifications == before_notifications + 1);
	poll(&c); assert(notifications == before_notifications + 1); cases++;
	/* The actual helper must notice each discrete field, independent of padding. */
	assert(!sm_notify_changed(&a, &b)); cases++;
#define FIELD(name) do { b = a; b.name = 1; assert(sm_notify_changed(&a, &b)); assert(sm_notify_changed(&b, &a)); cases++; } while (0)
	FIELD(charger_status); FIELD(charger_error); FIELD(battery_status); FIELD(battery_error);
	FIELD(health); FIELD(error); FIELD(stop_error); FIELD(latched); FIELD(source_inhibit);
	FIELD(auto_requested); FIELD(valid); FIELD(online); FIELD(protection_ok); FIELD(fault);
	FIELD(target_enable); FIELD(input_ua); FIELD(current_ua); FIELD(cell_uv);
	printf("{\"passed\":true,\"cases\":%d,\"stable_polls_checked\":100}\n", cases);
	return 0;
}
