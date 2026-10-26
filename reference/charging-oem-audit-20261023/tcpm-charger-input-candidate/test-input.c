/* Actual driver functions are extracted by test.py; only their IO is modeled. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include "kernel-usb-types.inc"
#include "negotiated-input.h"

enum power_supply_property {
	POWER_SUPPLY_PROP_ONLINE, POWER_SUPPLY_PROP_USB_TYPE,
	POWER_SUPPLY_PROP_CURRENT_NOW, POWER_SUPPLY_PROP_CURRENT_MAX,
	POWER_SUPPLY_PROP_VOLTAGE_NOW, POWER_SUPPLY_PROP_PRESENT,
	POWER_SUPPLY_PROP_HEALTH, PROP_COUNT
};
union power_supply_propval { int intval; };
struct device;
struct power_supply { int id; };
struct notifier_block { int unused; };
struct delayed_work { int unused; };
struct sm_sample { int online, valid, protection_ok, budget_ua, fault; };
struct sm_charge_cycle { int retained; };
struct sm_thermal_state { int retained; };
struct sm_oem_full_state { int retained; };
struct sm_charger {
	struct power_supply *input, *protection, *typec;
	bool source_inhibit, sample_full, latched, paused;
	struct sm_charge_cycle cycle;
	struct sm_thermal_state thermal;
	struct sm_oem_full_state full_state;
	struct notifier_block supply_notifier;
	struct delayed_work work;
};
#define POWER_SUPPLY_HEALTH_GOOD 1
#define PSY_EVENT_PROP_CHANGED 1
#define NOTIFY_DONE 0
#define READ_ONCE(x) (x)
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
static int system_wq;
static int values[3][PROP_COUNT], calls[3][PROP_COUNT];
static int failure_supply, failure_prop, failure_number, failure_code;
static int mutate_call, mutate_prop, mutate_value;
static int after_gauge_prop, after_gauge_value;
static int hardware_online, register14_reads, gauge_reads, resets, notifications;
static struct power_supply native = {0}, tcpm = {1}, protection = {2};
static int power_supply_get_property(struct power_supply *p,
		enum power_supply_property prop, union power_supply_propval *v)
{
	int n = ++calls[p->id][prop];
	if (p->id == failure_supply && (int)prop == failure_prop && n == failure_number)
		return failure_code;
	if (p->id == 1 && prop == POWER_SUPPLY_PROP_ONLINE && n == mutate_call)
		values[1][mutate_prop] = mutate_value;
	v->intval = values[p->id][prop];
	return 0;
}
static int sm_read(struct sm_charger *c, unsigned int reg)
{
	(void)c;
	if (reg == 0x13) return hardware_online ? 0x1b : 0;
	assert(reg == 0x14); register14_reads++; return 0;
}
static int sm_gauge_sample(struct sm_charger *c, struct sm_sample *s)
{
	(void)c; (void)s; gauge_reads++;
	if (after_gauge_prop >= 0) values[1][after_gauge_prop] = after_gauge_value;
	return 0;
}
static uint64_t ktime_get_boottime_ns(void) { return 1000000000; }
static void sm_cycle_update(struct sm_charge_cycle *c, uint64_t t, int online, int full)
{
	(void)t; (void)full; assert(!online); resets++; c->retained = 0;
}
static void sm_oem_full_init(struct sm_oem_full_state *s) { s->retained = 0; }
static void mod_delayed_work(int queue, struct delayed_work *w, int delay)
{
	(void)queue; (void)w; assert(!delay); notifications++;
}
#include "actual-input-functions.inc"

static struct sm_charger setup(bool negotiated)
{
	struct sm_charger c = {.input=&native, .protection=&protection,
		.typec=negotiated ? &tcpm : NULL, .latched=true,
		.cycle={1234}, .thermal={4}, .full_state={7}};
	memset(values, 0, sizeof(values)); memset(calls, 0, sizeof(calls));
	values[0][POWER_SUPPLY_PROP_ONLINE] = hardware_online = 1;
	values[0][POWER_SUPPLY_PROP_CURRENT_MAX] = 500000;
	values[1][POWER_SUPPLY_PROP_ONLINE] = 1;
	values[1][POWER_SUPPLY_PROP_USB_TYPE] = POWER_SUPPLY_USB_TYPE_C;
	values[1][POWER_SUPPLY_PROP_CURRENT_NOW] = 500000;
	values[1][POWER_SUPPLY_PROP_CURRENT_MAX] = 500000;
	values[1][POWER_SUPPLY_PROP_VOLTAGE_NOW] = 5000000;
	values[2][POWER_SUPPLY_PROP_PRESENT] = 1;
	values[2][POWER_SUPPLY_PROP_HEALTH] = POWER_SUPPLY_HEALTH_GOOD;
	failure_supply = failure_prop = failure_number = -1; failure_code = -EIO;
	mutate_call = -1; mutate_prop = 0; mutate_value = 0;
	after_gauge_prop = -1; after_gauge_value = 0;
	register14_reads = gauge_reads = resets = notifications = 0;
	return c;
}
static void history_preserved(const struct sm_charger *c)
{
	assert(c->latched && c->cycle.retained == 1234 && c->thermal.retained == 4);
	assert(c->full_state.retained == 7 && !resets);
}
int main(void)
{
	struct sm_charger c;
	struct sm_sample s;
	struct sm_input_allowance a;
	int cases = 0;
	c = setup(false);
	assert(!sm_collect(&c, &s) && s.valid && s.budget_ua == 500000);
	assert(calls[0][POWER_SUPPLY_PROP_CURRENT_MAX] == 2 && !calls[1][POWER_SUPPLY_PROP_ONLINE]);
	assert(gauge_reads == 1 && register14_reads == 1); history_preserved(&c); cases++;
	c = setup(true);
	assert(!sm_collect(&c, &s) && s.valid && s.budget_ua == 500000);
	assert(!calls[0][POWER_SUPPLY_PROP_CURRENT_MAX] && calls[1][POWER_SUPPLY_PROP_CURRENT_NOW] == 4);
	assert(register14_reads == 1); history_preserved(&c); cases++;
	/* Capable of 3A/PPS, currently operating at fixed 5V/500mA. */
	c = setup(true); values[1][POWER_SUPPLY_PROP_USB_TYPE] = POWER_SUPPLY_USB_TYPE_PD_PPS;
	values[1][POWER_SUPPLY_PROP_CURRENT_MAX] = 3000000;
	assert(!sm_collect(&c, &s) && s.budget_ua == 500000); cases++;
	const int types[] = {POWER_SUPPLY_USB_TYPE_PD, POWER_SUPPLY_USB_TYPE_PD_PPS,
		POWER_SUPPLY_USB_TYPE_PD_SPR_AVS, POWER_SUPPLY_USB_TYPE_PD_PPS_SPR_AVS};
	const int modes[] = {1, 2, 3, 2};
	for (unsigned i=0; i<sizeof(types)/sizeof(types[0]); i++) {
		c=setup(true); values[1][POWER_SUPPLY_PROP_USB_TYPE]=types[i];
		values[1][POWER_SUPPLY_PROP_ONLINE]=modes[i];
		values[1][POWER_SUPPLY_PROP_VOLTAGE_NOW]=9000000;
		assert(!sm_input_budget(&c, &a) && a.operating_ua == 500000); cases++;
	}
	/* ONLINE=0 during a live physical attachment must not clear session history. */
	c=setup(true); values[1][POWER_SUPPLY_PROP_ONLINE]=0;
	assert(sm_collect(&c, &s)==-ENODATA && c.source_inhibit && !s.valid && s.online);
	history_preserved(&c); assert(!gauge_reads && !register14_reads); cases++;
	/* An agreed physical detach still resets exactly as in the installed driver. */
	c=setup(true); values[0][POWER_SUPPLY_PROP_ONLINE]=hardware_online=0;
	assert(!sm_collect(&c, &s) && s.valid && !s.online && resets==1);
	assert(!c.latched && !c.cycle.retained && !c.thermal.retained && !c.full_state.retained);
	assert(!calls[1][POWER_SUPPLY_PROP_ONLINE]); cases++;
	c=setup(true); hardware_online=0;
	assert(sm_collect(&c, &s)==-EAGAIN && c.source_inhibit); history_preserved(&c); cases++;
	for (int prop=POWER_SUPPLY_PROP_ONLINE; prop<=POWER_SUPPLY_PROP_VOLTAGE_NOW; prop++) {
		c=setup(true); failure_supply=1; failure_prop=prop; failure_number=1;
		assert(sm_collect(&c, &s)==-EIO && c.source_inhibit && !s.valid);
		assert(!calls[0][POWER_SUPPLY_PROP_CURRENT_MAX]); history_preserved(&c); cases++;
	}
	/* Both an intra-snapshot change and a change across gauge acquisition fail closed. */
	for (int prop=POWER_SUPPLY_PROP_ONLINE; prop<=POWER_SUPPLY_PROP_VOLTAGE_NOW; prop++) {
		c=setup(true); mutate_call=2; mutate_prop=prop;
		mutate_value=prop==POWER_SUPPLY_PROP_USB_TYPE ? POWER_SUPPLY_USB_TYPE_PD : values[1][prop]+1;
		assert(sm_collect(&c, &s)<0 && c.source_inhibit && !s.valid); history_preserved(&c); cases++;
		c=setup(true); after_gauge_prop=prop;
		after_gauge_value=prop==POWER_SUPPLY_PROP_USB_TYPE ? POWER_SUPPLY_USB_TYPE_PD : values[1][prop]+1;
		assert(sm_collect(&c, &s)<0 && c.source_inhibit && !s.valid);
		assert(gauge_reads==1 && register14_reads==1); history_preserved(&c); cases++;
	}
	c=setup(true); values[1][POWER_SUPPLY_PROP_USB_TYPE]=POWER_SUPPLY_USB_TYPE_UNKNOWN;
	assert(sm_collect(&c, &s)==-EOPNOTSUPP && c.source_inhibit); cases++;
	c=setup(true); values[1][POWER_SUPPLY_PROP_CURRENT_NOW]=0;
	assert(sm_collect(&c, &s)==-ENODATA && !gauge_reads && c.source_inhibit); cases++;
	c=setup(true); values[1][POWER_SUPPLY_PROP_CURRENT_NOW]=500001;
	assert(sm_collect(&c, &s)==-EAGAIN && c.source_inhibit); cases++;
	c=setup(true); values[1][POWER_SUPPLY_PROP_CURRENT_NOW]=-1;
	assert(sm_collect(&c, &s)==-EPROTO && c.source_inhibit); cases++;
	c=setup(true); values[1][POWER_SUPPLY_PROP_VOLTAGE_NOW]=0;
	assert(sm_collect(&c, &s)==-EPROTO && c.source_inhibit); cases++;
	c=setup(true); values[1][POWER_SUPPLY_PROP_VOLTAGE_NOW]=9000000;
	assert(sm_collect(&c, &s)==-EPROTO && c.source_inhibit); cases++;
	for (unsigned i=0; i<sizeof(types)/sizeof(types[0]); i++) {
		c=setup(true); values[1][POWER_SUPPLY_PROP_USB_TYPE]=types[i];
		values[1][POWER_SUPPLY_PROP_ONLINE]=1;
		assert(!sm_input_budget(&c, &a)); cases++;
	}
	c=setup(true); values[1][POWER_SUPPLY_PROP_USB_TYPE]=POWER_SUPPLY_USB_TYPE_PD_PPS;
	values[1][POWER_SUPPLY_PROP_ONLINE]=3;
	assert(sm_input_budget(&c, &a)==-EPROTO); cases++;
	c=setup(true); values[1][POWER_SUPPLY_PROP_USB_TYPE]=POWER_SUPPLY_USB_TYPE_PD_SPR_AVS;
	values[1][POWER_SUPPLY_PROP_ONLINE]=2;
	assert(sm_input_budget(&c, &a)==-EPROTO); cases++;
	c=setup(true); struct power_supply unrelated={0};
	assert(!sm_supply_changed(&c.supply_notifier, PSY_EVENT_PROP_CHANGED, &tcpm) && notifications==1);
	sm_supply_changed(&c.supply_notifier, PSY_EVENT_PROP_CHANGED, &native);
	sm_supply_changed(&c.supply_notifier, PSY_EVENT_PROP_CHANGED, &protection);
	sm_supply_changed(&c.supply_notifier, PSY_EVENT_PROP_CHANGED, &unrelated);
	sm_supply_changed(&c.supply_notifier, 9, &tcpm);
	assert(notifications==3); c.paused=true;
	sm_supply_changed(&c.supply_notifier, PSY_EVENT_PROP_CHANGED, &tcpm);
	assert(notifications==3); cases++;
	printf("{\"passed\":true,\"actual_function_cases\":%d}\n", cases);
	return 0;
}
