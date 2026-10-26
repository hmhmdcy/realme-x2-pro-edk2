/* SPDX-License-Identifier: GPL-2.0-only */
/* Compare against independent verbatim OEM bodies, not a second new model. */
#include "oracle-fixture.h"
#include "mp2650-core.h"
#include "oem-full-cycle.h"
static unsigned int checks,samples,absolute_differences;
#define CHECK(x) do { if(!(x))fprintf(stderr,"line %d sample %u: %s\n",__LINE__,samples,#x);assert(x);checks++; } while(0)
static void point(struct oplus_chg_chip *o,struct sm_thermal_state *s,int temp)
{
 int old_good,held,band;struct sm_target target;enum sm_policy_reason reason;
 struct sm_sample sample={.valid=1,.online=1,.protection_ok=1,.budget_ua=1500000,
  .temp_decic=temp,.cell1_uv=3800000,.cell2_uv=3800000,.pack_uv=7600000};
 o->temperature=temp;old_good=oplus_chg_check_tbatt_is_good(o);held=sm_thermal_gate(s,temp,1);samples++;
 band=o->tbatt_status==BATTERY_STATUS__REMOVED?-2:o->tbatt_status==BATTERY_STATUS__LOW_TEMP?-1:
  o->tbatt_status==BATTERY_STATUS__HIGH_TEMP?6:o->tbatt_status-BATTERY_STATUS__COLD_TEMP;
 CHECK(s->band==band);CHECK(s->pre_shake==o->tbatt_pre_shake);
 CHECK(s->bounds[0]==o->limits.cold_bat_decidegc);CHECK(s->bounds[1]==o->limits.little_cold_bat_decidegc);
 CHECK(s->bounds[2]==o->limits.cool_bat_decidegc);CHECK(s->bounds[3]==o->limits.little_cool_bat_decidegc);
 CHECK(s->bounds[4]==o->limits.normal_bat_decidegc);CHECK(s->bounds[5]==o->limits.warm_bat_decidegc);
 CHECK(s->bounds[6]==o->limits.hot_bat_decidegc);
 CHECK(held==(!old_good||temp < -20||temp >= 530));
 if(held&&!old_good)CHECK(s->hold!=SM_THERMAL_NONE);
 if(held&&old_good)absolute_differences++;
 int ret=sm_policy_with_band_reason(&sample,4362500,250000,900000,s->band,&target,&reason);
 if(held){CHECK(ret==-ERANGE);CHECK(reason==SM_POLICY_REASON_TEMPERATURE);CHECK(!target.enable);}
 else{
  int expected=oplus_chg_get_float_voltage(o)*1000;
  if(expected>4362500)expected=4362500;
  expected=3712500+(expected-3712500)/12500*12500;
  CHECK(ret==0);CHECK(target.enable);CHECK(target.cell_uv==expected);
  CHECK(target.current_ua==250000);CHECK(target.input_ua==900000);
  struct sm_oem_full_state f;sm_oem_full_init(&f);
  struct sm_oem_full_sample in={.valid=1,.source_known=1,.online=1,.protection_good=1,.policy_good=1,
   .temp_decic=temp,.max_cell_uv=3800000,.cell_target_uv=target.cell_uv,.gauge_current_ua=250000,
   .policy_band_valid=1,.policy_band=s->band};
  struct sm_oem_full_result out=sm_oem_full_step(&f,0,&in);
  CHECK(!out.stop_all);CHECK(f.band==s->band);
  CHECK(out.voltage_threshold_uv==oplus_chg_get_float_voltage(o)*1000+18000);
  CHECK(out.sw_threshold_uv==sm_full_bands[s->band].sw_uv);
  CHECK(out.recharge_threshold_uv==target.cell_uv-sm_full_bands[s->band].recharge_drop_uv);
 }
}
static void sequence(const int *temps,unsigned int n)
{
 struct oplus_chg_chip o=oracle_init();struct sm_thermal_state s={0};
 for(unsigned int i=0;i<n;i++)point(&o,&s,temps[i]);
}
int main(void)
{
 const int cold[]={250,-1,0,1,2,3,4,5,4,3,2,1,0,-1,-2,-3,-4,-5,-6,-5,0,5};
 const int warm[]={250,440,439,438,439,438,421,420,421,420,419,420,421,438,439,440};
 const int outer[]={250,-21,-20,-1,0,-21,0,531,530,529,540,510,509,250,-200,-190,-189,-20};
 const int middle[]={250,49,50,49,31,30,29,50,120,119,101,100,99,120,159,160,159,179,180,159,140,139,160};
 sequence(cold,sizeof(cold)/sizeof(cold[0]));sequence(warm,sizeof(warm)/sizeof(warm[0]));
 sequence(outer,sizeof(outer)/sizeof(outer[0]));sequence(middle,sizeof(middle)/sizeof(middle[0]));
 /* Reproducible walks visit transitions, equality and shifted outer bounds. */
 unsigned int rng=0x71d61;struct oplus_chg_chip o=oracle_init();struct sm_thermal_state s={0};int temp=250;
 for(unsigned int i=0;i<20000;i++){
  rng=rng*1664525u+1013904223u;temp+=(int)((rng>>16)%81)-40;
  if(temp < -220)temp=-220;
  if(temp>570)temp=570;
  point(&o,&s,temp);
 }
 /* These are intentionally not invoked as a new high-power normal subpolicy.
  * Mark source fixtures used; its separate 97-case oracle already proved them.
  */
 (void)battery_temp_normal_anti_shake_handle;(void)oplus_chg_check_tbatt_normal_status;
 (void)oplus_chg_check_sw_full;(void)oplus_chg_check_hw_full;(void)oplus_chg_check_rechg_status;
 printf("{\"passed\":true,\"samples\":%u,\"assertions\":%u,\"absolute_stop_stricter_samples\":%u,\"oracle_general_band_equal\":true}\n",samples,checks,absolute_differences);
 return 0;
}
