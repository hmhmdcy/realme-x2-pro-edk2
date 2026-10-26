from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=(HERE/'kernel/camss-icp-a5-boot.c').read_text();fn=s[s.index('static enum hrtimer_restart boot_timeout'):s.index('static void command_failure')]
fn+=s[s.index('int camss_a5_runtime_resume'):s.index('static int firmware_region_get')]
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
typedef uint32_t u32;
#define BIT(n) (1U<<(n))
#define A5_ENABLE BIT(9)
#define A5_WAKE BIT(4)
#define A5_CONTROL 8
#define A5_INT_ENABLE 16
#define WRITE_ONCE(a,b) ((a)=(b))
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define spin_lock_irqsave(p,f) ((void)(p),(f)=1)
#define spin_unlock_irqrestore(p,f) ((void)(p),(void)(f))
enum hrtimer_restart {HRTIMER_NORESTART};struct hrtimer {int unused;};
struct camss_a5_resources {void *sierra;};struct reset_control {int unused;};
struct camss_a5 {struct hrtimer boot_timer;int control_lock;struct camss_a5_resources resources;struct reset_control *reset;bool power_held,cpu_enabled,boot_expired,reset_asserted;};
static unsigned writes;static u32 readl(void *p){return *(u32*)p;}static void writel(u32 v,void *p){writes++;*(u32*)p=v;}
#define EXPORT_SYMBOL_GPL(n)
static int reset_line,clocks_on,reset_fail,resources_fail,provider_calls;
static int reset_control_deassert(struct reset_control *r) {(void)r;provider_calls++;if(reset_fail==1)return -EIO;reset_line=0;return 0;}
static int reset_control_assert(struct reset_control *r) {(void)r;provider_calls++;if(reset_fail==2)return -EIO;reset_line=1;return 0;}
static int camss_a5_resources_resume(struct camss_a5_resources *r) {(void)r;provider_calls++;assert(!reset_line&&!clocks_on);if(resources_fail==1)return -EIO;clocks_on=1;return 0;}
static int camss_a5_resources_suspend(struct camss_a5_resources *r) {(void)r;provider_calls++;assert(reset_line&&clocks_on);if(resources_fail==2)return -EIO;clocks_on=0;return 0;}
'''
main=r'''
int main(void) {u32 regs[8];struct camss_a5 a={0};a.resources.sierra=regs;
 for(unsigned k=0;k<3;k++) {
  for(unsigned i=0;i<8;i++)regs[i]=0x1210;writes=0;a.power_held=k!=1;a.cpu_enabled=k!=2;a.boot_expired=false;
  assert(boot_timeout(&a.boot_timer)==HRTIMER_NORESTART);
  if(!k){assert(writes==2&&regs[4]==0&&regs[2]==0x1000&&a.boot_expired&&a.cpu_enabled);}
  else assert(!writes&&!a.boot_expired);
 }
 a.cpu_enabled=false;reset_line=1;clocks_on=reset_fail=resources_fail=provider_calls=0;
 assert(!camss_a5_runtime_resume(&a)&&clocks_on&&!reset_line&&!a.reset_asserted);
 assert(!camss_a5_runtime_suspend(&a)&&!clocks_on&&reset_line&&a.reset_asserted&&provider_calls==4);
 a.cpu_enabled=true;provider_calls=0;assert(camss_a5_runtime_suspend(&a)==-EBUSY&&!provider_calls);a.cpu_enabled=false;
 reset_fail=1;provider_calls=0;assert(camss_a5_runtime_resume(&a)==-EIO&&!clocks_on&&provider_calls==1);
 reset_fail=0;resources_fail=1;assert(camss_a5_runtime_resume(&a)==-EIO&&!clocks_on&&!reset_line&&!a.reset_asserted);
 resources_fail=0;reset_fail=2;clocks_on=1;provider_calls=0;assert(camss_a5_runtime_suspend(&a)==-EIO&&clocks_on&&provider_calls==1);
 reset_fail=0;resources_fail=2;assert(camss_a5_runtime_suspend(&a)==-EIO&&clocks_on&&reset_line&&a.reset_asserted);
 puts("BOOT_TIMEOUT_PM_PASS scenarios=9");return 0;}
'''
src=P/'boot-timeout-test-private.c';src.write_text(prefix+fn+main);out=P/'boot-timeout-test-private'
q=subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',str(src),'-o',str(out)],capture_output=True);(P/'boot-timeout-build-private.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
q=subprocess.run([str(out)],capture_output=True);(P/'boot-timeout-run-private.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
report=dict(stage=356,actual_timer_callback_body=True,actual_runtime_pm_wrapper_bodies=True,scenarios=9,reset_released_before_clock_enable_verified=True,reset_asserted_before_clock_disable_verified=True,provider_errors_and_live_cpu_rejection_verified=True,control_enable_and_wake_cleared=True,powered_off_or_cpu_off_registers_untouched=True,cleanup_ownership_retained=True,kernel_timer_dispatch_not_mock_proven=True,passed=True)
(HERE/'boot-timeout-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
