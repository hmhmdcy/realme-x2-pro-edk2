/* SPDX-License-Identifier: GPL-2.0-only */
#include "oracle-fixture.h"
static unsigned int checks;
#define CHECK(x) do { assert(x); checks++; } while(0)
static int at(struct oplus_chg_chip *c,int temp)
{ c->temperature=temp;return oplus_chg_check_tbatt_is_good(c); }
int main(void)
{
 struct oplus_chg_chip c=oracle_init();
 const int cold_wave[]={250,-1,0,1,4,5,4,0,-1,-4,-5,-6};
 const int cold_expected[]={8,4,4,4,4,5,5,5,5,5,5,4};
 for(unsigned int i=0;i<sizeof(cold_wave)/sizeof(cold_wave[0]);i++){
  CHECK(at(&c,cold_wave[i]));CHECK(c.tbatt_status==cold_expected[i]);
 }
 c=oracle_init();
 const int warm_wave[]={250,440,439,438,421,420,419,420,439,440};
 const int warm_expected[]={8,9,9,9,9,9,8,8,8,9};
 for(unsigned int i=0;i<sizeof(warm_wave)/sizeof(warm_wave[0]);i++){
  CHECK(at(&c,warm_wave[i]));CHECK(c.tbatt_status==warm_expected[i]);
  if(i==1){CHECK(c.setter_status==9);CHECK(c.setter_pre==250);CHECK(c.setter_warm_bound==440);CHECK(c.limits.warm_bat_decidegc==420);}
 }
 /* The initial sample seeds pre_shake before the first status transition. */
 c=oracle_init();CHECK(at(&c,-1));CHECK(c.limits.little_cold_bat_decidegc==0);
 CHECK(at(&c,0));CHECK(c.limits.little_cold_bat_decidegc==-5);
 /* Direction memory is not refreshed on ordinary same-band samples. */
 c=oracle_init();CHECK(at(&c,250));CHECK(at(&c,440));CHECK(at(&c,500));CHECK(c.tbatt_pre_shake==440);
 /* Exact parent update order exposes normal-child initialization's write. */
 c=oracle_init();CHECK(at(&c,450));CHECK(c.tbatt_pre_shake==450);
 CHECK(at(&c,460));CHECK(c.tbatt_pre_shake==450);
 oplus_chg_check_tbatt_normal_status(&c);CHECK(c.tbatt_pre_shake==460);CHECK(c.tbatt_normal_pre_shake==999);
 CHECK(at(&c,250));oplus_chg_check_tbatt_normal_status(&c);CHECK(c.tbatt_normal_pre_shake==250);
 CHECK(at(&c,260));oplus_chg_check_tbatt_normal_status(&c);CHECK(c.tbatt_pre_shake==250);
 /* Absolute original comparator is >hot, unlike r6's deliberately >=hot. */
 c=oracle_init();CHECK(at(&c,530));CHECK(c.tbatt_status==9);CHECK(!at(&c,531));CHECK(c.tbatt_status==3);
 CHECK(c.limits.hot_bat_decidegc==510);CHECK(!at(&c,511));CHECK(at(&c,510));
 /* Warm/Cold Full exit is SOC-dependent, before status change setters. */
 c=oracle_init();CHECK(at(&c,440));c.soc=99;c.batt_full=1;c.charging_state=CHARGING_STATUS_FULL;
 CHECK(at(&c,419));CHECK(!c.batt_full&&c.starts==1&&c.charging_state==CHARGING_STATUS_CCCV);
 c=oracle_init();CHECK(at(&c,440));c.soc=100;c.batt_full=1;c.charging_state=CHARGING_STATUS_FULL;
 CHECK(at(&c,419));CHECK(c.batt_full&&c.starts==0);
 /* Same-threshold cross-band counts really carry in the original SW body. */
 c=oracle_init();CHECK(at(&c,49));c.batt_volt=4351;c.icharging=-110;
 CHECK(!oplus_chg_check_sw_full(&c));CHECK(!oplus_chg_check_sw_full(&c));CHECK(c.sw_full_count==2);
 CHECK(at(&c,50));CHECK(!oplus_chg_check_sw_full(&c));CHECK(c.sw_full_count==3);
 CHECK(oplus_chg_get_float_voltage(&c)==4400);
 c.batt_volt=5000;CHECK(!oplus_chg_check_hw_full(&c));CHECK(!oplus_chg_check_hw_full(&c));
 CHECK(!oplus_chg_check_hw_full(&c));CHECK(oplus_chg_check_hw_full(&c));
 c.batt_volt=5000;oplus_chg_check_rechg_status(&c);c.batt_volt=4300;
 for(int i=0;i<5;i++){oplus_chg_check_rechg_status(&c);CHECK(c.starts==0);}
 oplus_chg_check_rechg_status(&c);CHECK(c.starts==1);
 printf("{\"passed\":true,\"assertions\":%u,\"cold_wave_samples\":12,\"warm_wave_samples\":10,\"normal_child_side_effect_demonstrated\":true,\"cross_band_sw_count_carries\":true}\n",checks);
 return 0;
}
