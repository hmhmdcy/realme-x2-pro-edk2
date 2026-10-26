/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
enum { BATTERY_STATUS__INVALID, BATTERY_STATUS__REMOVED, BATTERY_STATUS__LOW_TEMP,
 BATTERY_STATUS__HIGH_TEMP, BATTERY_STATUS__COLD_TEMP, BATTERY_STATUS__LITTLE_COLD_TEMP,
 BATTERY_STATUS__COOL_TEMP, BATTERY_STATUS__LITTLE_COOL_TEMP, BATTERY_STATUS__NORMAL, BATTERY_STATUS__WARM_TEMP };
typedef int OPLUS_CHG_TBATT_STATUS;
enum { BATTERY_STATUS__NORMAL_PHASE1, BATTERY_STATUS__NORMAL_PHASE2, BATTERY_STATUS__NORMAL_PHASE3,
 BATTERY_STATUS__NORMAL_PHASE4, BATTERY_STATUS__NORMAL_PHASE5, BATTERY_STATUS__NORMAL_PHASE6 };
typedef int OPLUS_CHG_TBATT_NORMAL_STATUS;
enum { CHG_STOP_VOTER__FULL=1, CHARGING_STATUS_CCCV=0, CHARGING_STATUS_FULL=1 };
#define HYSTERISIS_DECIDEGC 20
#define HYSTERISIS_DECIDEGC_0C 5
#define TBATT_PRE_SHAKE_INVALID 999
#define TEMP_CNT 1
#define FULL_COUNTS_SW 5
#define FULL_COUNTS_HW 4
#define D_RECHGING_CNT 5
#define chg_debug(...) ((void)0)
#define charger_xlog_printk(...) ((void)0)
struct limits {
#include "oracle-limit-fields.inc"
};
struct bounds { int cold_bound,little_cold_bound,cool_bound,little_cool_bound,normal_bound,warm_bound,hot_bound; };
struct normal_bounds { int phase1_bound,phase2_bound,phase3_bound,phase4_bound,phase5_bound,phase6_bound; };
struct oplus_chg_chip {
 struct limits limits; struct bounds anti_shake_bound; struct normal_bounds tbatt_normal_anti_shake_bound;
 int temperature,tbatt_pre_shake,tbatt_status,tbatt_normal_pre_shake,tbatt_normal_status;
 int batt_exist,soc,batt_full,charging_state,tbatt_when_full;
 int charger_exist,icharging,batt_volt,sw_full_count,sw_full,authenticate,hmac,in_rechging;
 int starts,setters,setter_status,setter_pre,setter_warm_bound,short_prohibit,short_disable_rechg;
};
static bool vbatt_higherthan_4180mv;
static int oplus_vooc_get_allow_reading(void) { return 1; }
static void oplus_chg_set_float_voltage(struct oplus_chg_chip *c)
{ c->setters++;c->setter_status=c->tbatt_status;c->setter_pre=c->tbatt_pre_shake;c->setter_warm_bound=c->limits.warm_bat_decidegc; }
static void oplus_chg_set_charging_current(struct oplus_chg_chip *c) { (void)c; }
static void oplus_chg_voter_charging_start(struct oplus_chg_chip *c,int voter)
{ assert(voter==CHG_STOP_VOTER__FULL);c->starts++;c->charging_state=CHARGING_STATUS_CCCV; }
static int oplus_short_c_batt_is_prohibit_chg(struct oplus_chg_chip *c) { return c->short_prohibit; }
static int oplus_short_c_batt_is_disable_rechg(struct oplus_chg_chip *c) { return c->short_disable_rechg; }
#include "oracle-functions.inc"
static struct oplus_chg_chip oracle_init(void)
{
 struct oplus_chg_chip c={.limits={
#include "oracle-limits.inc"
 },.tbatt_status=BATTERY_STATUS__NORMAL,.tbatt_pre_shake=999,.tbatt_normal_pre_shake=999,
 .tbatt_normal_status=BATTERY_STATUS__NORMAL_PHASE1,.soc=100,.charger_exist=1,.authenticate=1,.hmac=1};
 c.anti_shake_bound=(struct bounds){-20,0,50,120,160,440,530};
 c.tbatt_normal_anti_shake_bound=(struct normal_bounds){0,0,0,0,0,420};
 return c;
}
