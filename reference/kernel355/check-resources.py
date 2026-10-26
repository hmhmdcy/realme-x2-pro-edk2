"""Exercise the actual resume/suspend bodies with failing clock/PD providers."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=(HERE/'kernel/camss-icp-a5-resources.c').read_text()
constants=s[s.index('static const unsigned int group_offset'):s.index('static void camss_a5_delete_link')]
body=s[s.index('int camss_a5_resources_suspend'):].replace('EXPORT_SYMBOL_GPL(camss_a5_resources_suspend);','').replace('EXPORT_SYMBOL_GPL(camss_a5_resources_resume);','').replace('EXPORT_SYMBOL_GPL(camss_a5_resources_release);','')
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define BIT(n) (1U<<(n))
#define dev_err(...) ((void)0)
struct device {int id;}; struct clk {int id;};
struct clk_bulk_data {struct clk *clk;};
struct dev_pm_domain_list {struct device **pd_devs;};
struct camss_a5_resources {struct device *dev; struct dev_pm_domain_list *domains; struct clk_bulk_data clocks[19]; unsigned enabled_groups,held_domains;};
static int counter,fail_at,puts_fail,refs[3],enabled[4],events[30],event_count;
static int fail(void) {return counter++==fail_at;}
static int clk_set_rate(struct clk *c,unsigned long hz) {assert(hz && c->id>=0);return fail()?-EIO:0;}
static int group_id(struct clk_bulk_data *clocks) {int id=clocks->clk->id;return id==0?0:id==4?1:id==9?2:3;}
static int clk_bulk_prepare_enable(unsigned n,struct clk_bulk_data *c) {int g=group_id(c);assert(n==(g?5:4));if(fail())return -EIO;assert(!enabled[g]);enabled[g]=1;events[event_count++]=10+g;return 0;}
static void clk_bulk_disable_unprepare(unsigned n,struct clk_bulk_data *c) {int g=group_id(c);assert(n==(g?5:4)&&enabled[g]);enabled[g]=0;events[event_count++]=20+g;}
static int pm_runtime_resume_and_get(struct device *d) {if(fail())return -EIO;assert(!refs[d->id]);refs[d->id]++;events[event_count++]=30+d->id;return 0;}
static int pm_runtime_put_sync(struct device *d) {assert(refs[d->id]==1);refs[d->id]--;events[event_count++]=40+d->id;return puts_fail==d->id?-EIO:0;}
'''
main=r'''
int main(void) {
 struct device owner={99},pd[3]={{0},{1},{2}},*devices[3]={&pd[0],&pd[1],&pd[2]};
 struct dev_pm_domain_list domains={devices};struct clk clks[19];struct camss_a5_resources r={0};
 unsigned scenarios=0;int expected[]={10,30,11,31,12,32,13,23,42,22,41,21,40,20};
 assert(camss_a5_resources_resume(&r)==-EINVAL);assert(camss_a5_resources_suspend(&r)==-EINVAL);scenarios++;
 for(int trial=-1;trial<11;trial++) {
  memset(&r,0,sizeof(r));r.dev=&owner;r.domains=&domains;
  for(int i=0;i<19;i++){clks[i].id=i;r.clocks[i].clk=&clks[i];}
  counter=event_count=0;fail_at=trial;puts_fail=-1;
  int ret=camss_a5_resources_resume(&r);
  if(trial==-1) {
   assert(ret==0&&r.enabled_groups==15&&r.held_domains==7);
   assert(camss_a5_resources_resume(&r)==-EBUSY);
   assert(camss_a5_resources_release(&r)==-EBUSY);
   assert(camss_a5_resources_suspend(&r)==0);
   assert(event_count==14&&!memcmp(events,expected,sizeof(expected)));
  } else assert(ret==-EIO);
  assert(!r.enabled_groups&&!r.held_domains);
  for(int i=0;i<4;i++)assert(enabled[i]==0);
  for(int i=0;i<3;i++)assert(refs[i]==0);
  assert(camss_a5_resources_suspend(&r)==0);assert(camss_a5_resources_release(&r)==0&&!r.dev);scenarios++;
 }
 for(int p=0;p<3;p++) {
  memset(&r,0,sizeof(r));r.dev=&owner;r.domains=&domains;
  for(int i=0;i<19;i++)r.clocks[i].clk=&clks[i];
  fail_at=-1;counter=event_count=0;puts_fail=p;
  assert(camss_a5_resources_resume(&r)==0);
  assert(camss_a5_resources_suspend(&r)==-EIO);
  assert(!r.enabled_groups&&!r.held_domains);
  for(int i=0;i<4;i++)assert(!enabled[i]);
  for(int i=0;i<3;i++)assert(!refs[i]);
  scenarios++;
 }
 printf("{\"scenarios\":%u,\"passed\":true}\n",scenarios);
 return 0;
}
'''
src=P/'resources-test-private.c';src.write_text(prefix+constants+body+main);out=P/'resources-test-private'
q=subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-o',str(out),str(src)],capture_output=True);(P/'resources-test-build-private.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
q=subprocess.run([str(out)],capture_output=True);(P/'resources-test-run-private.log').write_bytes(q.stdout+q.stderr);q.check_returncode();d=json.loads(q.stdout)
report=dict(stage=355,actual_resume_suspend_bodies=True,provider_mocked=True,partial_clock_or_domain_enable_unwound=True,reverse_stop_order_verified=True,provider_put_error_reported=True,device_test_separate=True,**d)
(HERE/'resources-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
