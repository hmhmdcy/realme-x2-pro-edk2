"""Fault-inject the actual power callbacks, including shared regulator references."""
from pathlib import Path
import hashlib,json,subprocess
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE/'power-sequence-test';P.mkdir(mode=0o700)
source=(R/'s5kgw1.c').read_text()
def block(marker):
 a=source.index(marker);b=source.index('{',a);depth=1;i=b+1
 while depth:
  depth+=int(source[i]=='{')-int(source[i]=='}');i+=1
 return source[a:i]
enum=block('enum s5kgw1_supply {')+';'
off=block('static int s5kgw1_power_off(')
on=block('static int s5kgw1_power_on(')
prefix=r'''
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
struct device {void *data;}; struct gpio_desc {int value;};
struct clk {int refs;}; struct regulator {int index,refs;};
#define dev_err(dev,fmt,...) ((void)(dev))
static const char *fail_name;
static int fail_count;
static char events[4096];
static unsigned int event_count;
static int op(const char *name) {
 strcat(events,name);strcat(events,";");event_count++;
 if(fail_count && fail_name && !strcmp(name,fail_name)) {fail_count--;return -EIO;}
 return 0;
}
static void *dev_get_drvdata(struct device *d) {return d->data;}
#define to_s5kgw1(p) ((struct s5kgw1 *)(p))
static int pinctrl_pm_select_default_state(struct device *d) {(void)d;return op("default");}
static int pinctrl_pm_select_sleep_state(struct device *d) {(void)d;return op("sleep");}
static int gpiod_set_value_cansleep(struct gpio_desc *g,int v) {
 int r=op(v?"reset1":"reset0");if(!r)g->value=v;return r;
}
static int regulator_enable(struct regulator *r) {
 char name[16];sprintf(name,"enable%d",r->index);
 int ret=op(name);if(!ret)r->refs++;return ret;
}
static int regulator_disable(struct regulator *r) {
 char name[16];sprintf(name,"disable%d",r->index);
 int ret=op(name);if(!ret) {assert(r->refs>2);r->refs--;} return ret;
}
static int clk_prepare_enable(struct clk *c) {int r=op("clock1");if(!r)c->refs++;return r;}
static void clk_disable_unprepare(struct clk *c) {op("clock0");assert(c->refs==1);c->refs--;}
static void usleep_range(unsigned int lo,unsigned int hi) {
 char name[20];(void)hi;sprintf(name,"wait%u",lo);op(name);
}
'''
sensor=r'''
struct s5kgw1 {
 struct device *dev;struct gpio_desc *reset;struct clk *clock;
 struct regulator *supplies[S5KGW1_NUM_SUPPLIES];
 bool supply_enabled[S5KGW1_NUM_SUPPLIES],clock_enabled,power_fault;
};
'''
main=r'''
static struct s5kgw1 s;
static struct device d;
static struct gpio_desc gpio;
static struct clk clock;
static struct regulator regs[4];
static unsigned int cases;
static void init(bool af) {
 memset(&s,0,sizeof(s));memset(&gpio,0,sizeof(gpio));memset(&clock,0,sizeof(clock));
 d.data=&s;s.dev=&d;s.reset=&gpio;s.clock=&clock;
 for(unsigned int i=0;i<4;i++) {regs[i]=(struct regulator){.index=i,.refs=2};s.supplies[i]=&regs[i];}
 if(!af)s.supplies[S5KGW1_VAF]=NULL;
 events[0]=0;event_count=0;fail_name=NULL;fail_count=0;
}
static void clean(void) {
 assert(!s.clock_enabled && !clock.refs);
 for(unsigned int i=0;i<4;i++) {assert(!s.supply_enabled[i]);assert(regs[i].refs==2);}
}
int main(void) {
 const char *on_failures[]={"default","reset1","enable0","enable1","enable2","enable3","reset0","clock1"};
 const char *off_failures[]={"reset1","disable2","disable1","disable3","disable0","sleep"};
 for(unsigned int af=0;af<2;af++) {
  init(af);assert(!s5kgw1_power_on(&d));
  const char *expected=af?
   "default;reset1;wait1000;enable0;wait1000;enable1;wait1000;enable2;enable3;wait1000;reset0;wait1000;clock1;wait5000;":
   "default;reset1;wait1000;enable0;wait1000;enable1;wait1000;enable2;wait1000;reset0;wait1000;clock1;wait5000;";
  assert(!strcmp(events,expected));
  assert(!s5kgw1_power_off(&d));clean();cases++;
  /* A clean failed resume unwinds all references and permits a fresh attempt. */
  for(unsigned int i=0;i<ARRAY_SIZE(on_failures);i++) {
   if(!af && !strcmp(on_failures[i],"enable3"))continue;
   init(af);fail_name=on_failures[i];fail_count=1;
   assert(s5kgw1_power_on(&d)==-EIO);assert(!fail_count);clean();
   assert(!s.power_fault);fail_name=NULL;
   assert(!s5kgw1_power_on(&d));assert(!s5kgw1_power_off(&d));clean();cases++;
  }
  /* Failed disables retain the driver's reference; resume is blocked. */
  for(unsigned int i=0;i<ARRAY_SIZE(off_failures);i++) {
   if(!af && !strcmp(off_failures[i],"disable3"))continue;
   init(af);assert(!s5kgw1_power_on(&d));
   fail_name=off_failures[i];fail_count=1;
   assert(s5kgw1_power_off(&d)==-EIO);assert(!fail_count);assert(s.power_fault);
   for(unsigned int j=0;j<4;j++) {
    assert(regs[j].refs==2+(int)s.supply_enabled[j]);
    assert(regs[j].refs>=2);
   }
   unsigned int before=event_count;
   assert(s5kgw1_power_on(&d)==-EIO && event_count==before);
   fail_name=NULL;assert(!s5kgw1_power_off(&d));clean();
   assert(s.power_fault);cases++;
  }
  init(af);assert(!s5kgw1_power_on(&d));
  unsigned int before=event_count;assert(s5kgw1_power_on(&d)==-EIO && event_count==before);
  assert(!s5kgw1_power_off(&d));clean();cases++;
 }
 printf("passed %u\n",cases);return 0;
}
'''
(P/'harness.c').write_text(prefix+enum+sensor+off+on+main)
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-O2','-fsanitize=undefined',str(P/'harness.c'),'-o',str(P/'harness')],check=True)
text=subprocess.check_output([str(P/'harness')],text=True).strip()
assert text=='passed 30',text
report=dict(stage=272,actual_power_callbacks_executed=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
 cases=30,with_and_without_optional_af_supply=True,oem_power_on_order_and_delays_verified=True,
 shared_regulator_references_preserved=True,resume_failure_unwinds_and_retries=True,
 failed_disable_reference_retained=True,uncertain_suspend_latches_fault_and_blocks_resume=True,
 duplicate_power_on_blocked=True,undefined_behavior_sanitizer=True,phone_unchanged=True,
 actual_regulators_gpio_clock_and_pm_still_unverified=True)
(R/'power-sequence-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
