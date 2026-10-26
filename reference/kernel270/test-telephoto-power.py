"""Exercise actual power callbacks with failed APIs and shared regulator users."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel270');B=P/'power-test-r1';B.mkdir(mode=0o700)
source=(R/'s5k3m5.c').read_text()
def function(name):
 start=source.index('static int '+name+'(');brace=source.index('{',start);i=brace+1;depth=1
 while depth:
  if source[i]=='{':depth+=1
  elif source[i]=='}':depth-=1
  i+=1
 return source[start:i]+'\n'
actual=function('s5k3m5_clock19_power_off')+function('s5k3m5_clock19_power_on')
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define dev_err(...) ((void)0)
struct device { int unused; };
struct regulator { int users, baseline; };
struct clock { bool enabled; };
struct gpio { int value; };
struct supply { struct regulator *consumer; };
struct s5k3m5 {
 struct device *dev;
 struct supply supplies[4];
 struct clock *mclk;
 struct gpio *reset_gpio;
 bool supply_enabled[4], clock_enabled, power_fault;
};
static int api_count, fail_a, fail_b;
static bool active_pins;
static bool failed(void) { ++api_count; return api_count==fail_a || api_count==fail_b; }
static int pinctrl_pm_select_default_state(struct device *d) { (void)d;if(failed())return -EIO;active_pins=true;return 0; }
static int pinctrl_pm_select_sleep_state(struct device *d) { (void)d;if(failed())return -EIO;active_pins=false;return 0; }
static int gpiod_set_value_cansleep(struct gpio *g,int v) { if(failed())return -EIO;g->value=v;return 0; }
static void usleep_range(unsigned a,unsigned b) { assert(a<=b); }
static int regulator_enable(struct regulator *r) { if(failed())return -EIO;++r->users;return 0; }
static int regulator_disable(struct regulator *r) { if(failed())return -EIO;assert(r->users>r->baseline);--r->users;return 0; }
static int clk_prepare_enable(struct clock *c) { if(failed())return -EIO;assert(!c->enabled);c->enabled=true;return 0; }
static void clk_disable_unprepare(struct clock *c) { assert(c->enabled);c->enabled=false; }
'''
suffix=r'''
int main(void)
{
 unsigned cases=0, success=0, clean_fail=0, latched=0;
 for(int shared=0;shared<2;++shared)for(int first=0;first<21;++first)for(int second=0;second<21;++second) {
  struct regulator regs[4]={{0}};struct clock clk={0};struct gpio reset={.value=1};struct device dev={0};
  struct s5k3m5 s={.dev=&dev,.mclk=&clk,.reset_gpio=&reset};
  for(int i=1;i<4;++i) { regs[i].baseline=regs[i].users=shared;s.supplies[i].consumer=&regs[i]; }
  api_count=0;fail_a=first;fail_b=second;active_pins=false;
  int ret=s5k3m5_clock19_power_on(&s);
  if(ret==0) {
   ++success;assert(clk.enabled && s.clock_enabled && !reset.value && active_pins);
   for(int i=1;i<4;++i)assert(regs[i].users==shared+1 && s.supply_enabled[i]);
   int off=s5k3m5_clock19_power_off(&s);if(off)assert(s.power_fault);
  } else if(!s.power_fault) {
   ++clean_fail;assert(!clk.enabled && reset.value && !active_pins);
   for(int i=1;i<4;++i)assert(regs[i].users==shared && !s.supply_enabled[i]);
  }
  for(int i=1;i<4;++i)assert(regs[i].users==shared+(s.supply_enabled[i]?1:0));
  if(s.power_fault) {
   ++latched;assert(s5k3m5_clock19_power_on(&s)==-EIO);
  }
  /* A failed disable retains its consumer ownership for managed cleanup. */
  fail_a=fail_b=0;assert(s5k3m5_clock19_power_off(&s)==0);
  assert(!clk.enabled && !s.clock_enabled && reset.value && !active_pins);
  for(int i=1;i<4;++i)assert(regs[i].users==shared && !s.supply_enabled[i]);
  if(!s.power_fault) { assert(s5k3m5_clock19_power_on(&s)==0);assert(s5k3m5_clock19_power_off(&s)==0); }
  for(int i=1;i<4;++i)assert(regs[i].users==shared && !s.supply_enabled[i]);
  ++cases;
 }
 assert(success && clean_fail && latched);
 printf("{\"cases\":%u,\"power_on_success_cases\":%u,\"clean_rollback_cases\":%u,\"fault_latched_cases\":%u}\n",cases,success,clean_fail,latched);
}
'''
c=B/'power.c';c.write_text(prefix+actual+suffix)
q=subprocess.run(['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(c),'-o',str(B/'power')],capture_output=True)
(B/'compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
q=subprocess.run([str(B/'power')],capture_output=True,timeout=15)
(B/'run-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,'Review the actual callback failure, not a rewritten implementation'
counts=json.loads(q.stdout);report=dict(stage=270,**counts,actual_source_functions=True,
 source_sha256=hashlib.sha256(source.encode()).hexdigest(),function_sha256=hashlib.sha256(actual.encode()).hexdigest(),
 asan_ubsan_passed=True,shared_consumer_references_preserved=True,failed_disables_keep_owned_reference=True,
 clean_rollback_retry_and_fault_latch_checked=True,api_fault_model_only=True,not_kernel_concurrency_or_hardware_injection=True)
(R/'telephoto-power-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
