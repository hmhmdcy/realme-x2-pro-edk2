/* SPDX-License-Identifier: GPL-2.0-only */
/* New affected paths only. Driver bodies below are extracted, not rewritten. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "mp2650-core.h"
#include "oem-full-cycle.h"
#include <charge-cycle.h>
#include <gauge-protocol.h>
#include <reattach-observation.h>

typedef uint64_t u64;
typedef uint64_t ktime_t;
static uint64_t now;
static bool control = true;
static unsigned int assertions, groups;
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); assert(x); } assertions++; } while (0)
#define NS(s) ((uint64_t)(s) * 1000000000ULL)
#define dev_warn_ratelimited(...) ((void)0)
#define I2C_LOCK_SEGMENT 1
static uint64_t ktime_get_boottime(void) { return now; }
static uint64_t ktime_get_boottime_ns(void) { return now; }
struct i2c_client { void *adapter; };
static int gauge_words[256], lock_depth, locks, unlocks, soc_reads, mac_reads;
static void i2c_lock_bus(void *adapter, int flag) { (void)adapter; assert(flag == 1 && !lock_depth); lock_depth++; locks++; }
static void i2c_unlock_bus(void *adapter, int flag) { (void)adapter; assert(flag == 1 && lock_depth == 1); lock_depth--; unlocks++; }
static int sm_gauge_word_locked(struct i2c_client *g, unsigned int reg, bool write, unsigned int value)
{
    (void)g; (void)value; assert(lock_depth == 1 && !write && reg < 256);
    if (reg == 0x2c) soc_reads++;
    return gauge_words[reg];
}
static int sm_gauge_mac_locked(struct i2c_client *g, unsigned int command, unsigned char *packet)
{
    (void)g; assert(lock_depth == 1 && command == 0x0071); mac_reads++;
    memset(packet, 0, 36); packet[2] = packet[4] = 0xa0; packet[3] = packet[5] = 0x0f;
    return 0;
}
struct bus { unsigned int regs[256], writes; int read08_error; };
struct sm_charger {
    struct i2c_client *gauge;
    struct sm_io io;
    struct sm_sample sample;
    struct sm_target target;
    int cell_ceiling_uv, current_cap_ua, input_cap_ua, last_error, stop_error;
    bool auto_requested, latched, paused, sample_full, source_inhibit;
    ktime_t sampled_at;
    struct sm_charge_cycle cycle;
    struct sm_oem_full_state full_state;
    struct sm_oem_full_result full_result;
    bool full_holding, hold_requested, gauge_charge_stop;
    struct sm_thermal_state thermal;
    struct sm_reattach_observation reattach;
    enum sm_policy_reason thermal_reason;
};
struct frame { struct sm_sample sample; int error; bool hardware_full, source_inhibit; };
static struct frame next;
static int read_register(void *ctx, unsigned int reg)
{ struct bus *b = ctx; assert(reg < 256); return reg == 8 && b->read08_error ? b->read08_error : (int)b->regs[reg]; }
static int write_register(void *ctx, unsigned int reg, unsigned int value)
{ struct bus *b = ctx; assert(reg < 256 && value < 256); b->writes++; b->regs[reg] = value; return 0; }
static int sm_collect(struct sm_charger *c, struct sm_sample *s)
{
    *s = next.sample; c->source_inhibit = next.source_inhibit; c->sample_full = next.hardware_full;
    if (!next.error && s->valid && !s->online) {
        sm_cycle_update(&c->cycle, now, 0, 0); c->latched = false;
        c->thermal = (struct sm_thermal_state){0}; sm_oem_full_init(&c->full_state);
    }
    return next.error;
}
static int sm_read(struct sm_charger *c, unsigned int reg) { return c->io.read(c->io.ctx,reg); }
#include "actual-functions.inc"

static struct frame sample(int temp, int cell, int soc)
{
    return (struct frame){ .sample = { .valid = 1, .online = 1, .protection_ok = 1, .budget_ua = 500000,
        .temp_decic = temp, .cell1_uv = cell, .cell2_uv = cell, .pack_uv = 2 * cell,
        .gauge_current_ua = 50000, .soc_valid = 1, .soc_percent = soc } };
}
static int at(struct sm_charger *c, unsigned int seconds, struct frame f)
{ now = NS(seconds); next = f; return sm_step_locked(c); }
static void full(struct sm_charger *c, struct bus *bus, int temp, int cell)
{
    *c = (struct sm_charger){ .cell_ceiling_uv = 4362500, .current_cap_ua = 250000,
        .input_cap_ua = 900000, .auto_requested = true };
    *bus = (struct bus){ .regs = { [0]=10, [0x0f]=10, [2]=5, [3]=0x31, [4]=0x68, [8]=0x16, [9]=0x48 } };
    c->io = (struct sm_io){bus,read_register,write_register};
    sm_cycle_init(&c->cycle, 0); sm_oem_full_init(&c->full_state);
    struct frame f = sample(temp,cell,99); f.hardware_full = true;
    CHECK(at(c,1,f)==0 && c->full_state.full && c->full_holding && !c->target.enable);
}
static int charging(const struct bus *bus) { return (bus->regs[8] & 0x18) == 0x10; }
static int inhibited(const struct bus *bus) { return (bus->regs[8] & 0x18) == 8; }

/* Unchanged oracle fixture + original actual functions, not a new model. */
#include <oracle-fixture.h>
static void oracle_cases(void)
{
    struct oplus_chg_chip c;
    groups++;
    c = oracle_init(); c.temperature=440; (void)oplus_chg_check_tbatt_is_good(&c);
    CHECK(c.tbatt_status==BATTERY_STATUS__WARM_TEMP);
    c.soc=99; c.batt_full=1; c.charging_state=CHARGING_STATUS_FULL; c.temperature=419;
    CHECK(oplus_chg_check_tbatt_is_good(&c) && c.starts==1 && !c.batt_full && c.tbatt_when_full==200);
    c = oracle_init(); c.temperature=-1; (void)oplus_chg_check_tbatt_is_good(&c);
    c.soc=99; c.batt_full=1; c.charging_state=CHARGING_STATUS_FULL; c.temperature=5;
    CHECK(oplus_chg_check_tbatt_is_good(&c) && c.starts==1 && !c.batt_full);
    for (int blocked=0; blocked<3; blocked++) {
        c=oracle_init(); c.temperature=440; (void)oplus_chg_check_tbatt_is_good(&c);
        c.soc=blocked==0 ? 100 : 99; c.batt_full=blocked!=1;
        c.charging_state=blocked==2 ? CHARGING_STATUS_CCCV : CHARGING_STATUS_FULL; c.temperature=419;
        (void)oplus_chg_check_tbatt_is_good(&c); CHECK(c.starts==0);
    }
    c=oracle_init(); c.soc=99; c.batt_full=1; c.charging_state=CHARGING_STATUS_FULL; c.temperature=150;
    (void)oplus_chg_check_tbatt_is_good(&c); CHECK(c.starts==0);
    /* Merely reference other already-frozen functions to satisfy -Wunused;
     * their old suites are NOT executed by this targeted fixture. */
    (void)oplus_chg_check_tbatt_normal_status; (void)oplus_chg_check_sw_full;
    (void)oplus_chg_check_hw_full; (void)oplus_chg_check_rechg_status;
}
static void gauge_cases(void)
{
    struct i2c_client g={0}; struct sm_charger c={.gauge=&g}; struct sm_sample s={0};
    groups++; memset(gauge_words,0,sizeof(gauge_words));
    gauge_words[0x06]=2981; gauge_words[0x08]=8000; gauge_words[0x0c]=50;
    int values[]={0,99,100,101,0xffff,-EREMOTEIO};
    for (unsigned int i=0; i<sizeof(values)/sizeof(values[0]); i++) {
        int v=values[i]; gauge_words[0x2c]=v;
        s.soc_valid=1; s.soc_percent=99;
        CHECK(sm_gauge_sample(&c,&s)==0);
        CHECK(s.soc_valid==(v>=0 && v<=100));
        CHECK(s.soc_percent==(v>=0 && v<=100 ? v : -1));
        CHECK(s.cell1_uv==4000000 && s.gauge_current_ua==50000);
    }
    int prior_reads=soc_reads; gauge_words[0x06]=-EIO;
    CHECK(sm_gauge_sample(&c,&s)==-EIO && !s.soc_valid && s.soc_percent==-1 && soc_reads==prior_reads);
    CHECK(!lock_depth && locks==unlocks && soc_reads==6 && mac_reads==6);
}
int main(void)
{
    struct sm_charger c; struct bus bus; struct frame f;
    oracle_cases(); gauge_cases();
    groups++; full(&c,&bus,440,4100000);
    CHECK(at(&c,2,sample(419,4300000,99))==0 && c.full_result.recharge && !c.full_state.full && charging(&bus));
    CHECK(c.target.cell_uv==4362500 && c.target.current_ua==250000 && c.target.input_ua==500000);
    CHECK(c.full_result.tick==0 && c.cycle.timed_out==0);
    groups++; full(&c,&bus,-1,3900000);
    CHECK(at(&c,2,sample(5,4300000,99))==0 && c.full_result.recharge && !c.full_state.full && charging(&bus));

    groups++;
    for (int variant=0; variant<3; variant++) {
        full(&c,&bus,440,4100000); f=sample(419,4300000,variant==0 ? 100 : 99);
        if (variant==1) f.sample.soc_valid=0;
        if (variant==2) f.sample.soc_percent=101;
        CHECK(at(&c,2,f)==0 && c.full_state.full && !c.full_result.recharge && !charging(&bus));
        CHECK(at(&c,3,sample(419,4300000,99))==0 && c.full_state.full && !c.full_result.recharge);
    }
    groups++; full(&c,&bus,440,4100000); f=sample(419,4200000,100);
    CHECK(at(&c,2,f)==0 && c.full_state.full && c.full_state.recharge_count==1);
    for (unsigned int t=3; t<7; t++) CHECK(at(&c,t,f)==0 && c.full_state.recharge_count==1 && c.full_state.full);
    for (unsigned int t=7; t<=22; t+=5) CHECK(at(&c,t,f)==0 && c.full_state.full);
    CHECK(at(&c,27,f)==0 && c.full_result.recharge && !c.full_state.full && charging(&bus));

    groups++; full(&c,&bus,250,4300000);
    CHECK(at(&c,2,sample(150,4300000,99))==0 && c.full_state.full && !c.full_result.recharge);
    groups++; full(&c,&bus,440,4100000); c.auto_requested=false;
    CHECK(at(&c,2,sample(419,4300000,99))==0 && c.full_state.full && !c.full_result.recharge && inhibited(&bus));
    c.auto_requested=true;
    CHECK(at(&c,3,sample(419,4300000,99))==0 && c.full_state.full && !c.full_result.recharge && c.full_holding);
    full(&c,&bus,440,4100000); c.full_holding=false;
    CHECK(at(&c,2,sample(419,4300000,99))==0 && c.full_state.full && !c.full_result.recharge);
    groups++; full(&c,&bus,440,4100000);
    bus.regs[8] = (bus.regs[8] & ~0x18U) | 8U; /* successful suspend stop retains old software flag */
    CHECK(c.full_holding && at(&c,2,sample(419,4300000,99))==0 && c.full_state.full &&
          !c.full_result.recharge && !charging(&bus));
    full(&c,&bus,440,4100000); bus.read08_error=-EREMOTEIO;
    CHECK(at(&c,2,sample(419,4300000,99))==-EREMOTEIO && c.latched && c.full_state.full && !c.full_result.recharge);

    groups++;
    for (int bad=0; bad<5; bad++) {
        full(&c,&bus,440,4100000); f=sample(419,4300000,99);
        if (bad==0) c.latched=true;
        if (bad==1) c.cycle.timed_out=1;
        if (bad==2) f.sample.gauge_flags=SM_FULL_OCA;
        if (bad==3) f.sample.gauge_flags=SM_FULL_TCA;
        if (bad==4) f.error=-EREMOTEIO;
        (void)at(&c,2,f);
        CHECK(c.full_state.full && !c.full_result.recharge && inhibited(&bus));
        if (bad<=2 || bad==4) CHECK(c.latched);
        if (bad==1) CHECK(c.cycle.timed_out);
    }
    groups++; full(&c,&bus,440,4100000); f=sample(531,4100000,99);
    CHECK(at(&c,2,f)!=0 && c.full_state.full && !c.full_result.recharge && inhibited(&bus));
    CHECK(at(&c,3,sample(419,4300000,99))==0 && c.full_state.full && !c.full_result.recharge);
    full(&c,&bus,440,4100000); f=sample(419,4300000,99); f.sample.valid=0; f.sample.online=0; f.error=-ENODATA; f.source_inhibit=true;
    (void)at(&c,2,f); CHECK(c.full_state.full && !c.full_result.recharge && inhibited(&bus));
    CHECK(at(&c,3,sample(419,4300000,99))==0 && c.full_state.full && !c.full_result.recharge);
    printf("{\"passed\":true,\"groups\":%u,\"assertions\":%u,\"old_matrix_rerun\":false}\n",groups,assertions);
    return 0;
}
