#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint32_t u32;
#define BIT(n) (1U<<(n))
#define __iomem
#define A5_INT_ENABLE 0x10
#define A5_CONTROL 8
#define A5_RESET 4
#define A5_INIT_REQUEST 0x48
#define A5_STATUS 0x200
#define A5_ENABLE BIT(9)
#define A5_WAKE BIT(4)
#define A5_WFI BIT(7)
#define SYS_PC_PREP 0x10002
#define PC_DONE 0x20002
#define dev_info(...) ((void)0)
struct resources {void *sierra;unsigned enabled_groups,held_domains;};
struct camss_a5 {
 struct resources resources;
 void *dev,*reset;int irq,boot_timer,pc_error;
 bool cpu_enabled,irq_enabled,initialized,reset_asserted,power_held;
};
static unsigned ticks,reset_tick,free_tick,pm_tick,pm_calls,suspend_calls,captures;
static bool backing=true,stuck_control;
static int reset_error,free_error,pm_error,command_error,poll_error,suspend_error;
static u32 registers[256];
static struct camss_a5 *active;
static void hrtimer_cancel(int *t) {*t=0;}
static u32 readl(void *p) {return *(u32 *)p;}
static void writel(u32 v,void *p) {
 if(stuck_control && p==registers+A5_CONTROL/4)v|=A5_ENABLE|A5_WAKE;
 *(u32 *)p=v;
}
static void disable_irq(int irq) {(void)irq;}
static int reset_control_assert(void *reset) {(void)reset;reset_tick=++ticks;return reset_error;}
static int send_command(struct camss_a5 *a,u32 type,u32 response) {
 assert(a->cpu_enabled && a->initialized && a->irq_enabled);
 assert(type==SYS_PC_PREP && response==PC_DONE);return command_error;
}
#define readl_poll_timeout(addr,value,condition,interval,timeout) ({ \
 (void)(interval);(void)(timeout);value=readl(addr); \
 poll_error ? poll_error : ((condition) ? 0 : -ETIMEDOUT);})
static void capture_shared_state(struct camss_a5 *a) {
 assert(!a->cpu_enabled && (!backing || a->power_held));++captures;
}
static int free_memory(struct camss_a5 *a) {
 assert(!a->cpu_enabled && !a->irq_enabled);
 if(backing)assert(a->power_held);
 free_tick=++ticks;if(free_error)return free_error;backing=false;return 0;
}
static int camss_a5_resources_suspend(struct resources *r) {
 ++suspend_calls;assert(!active->cpu_enabled && !backing);
 r->enabled_groups=0;r->held_domains=0;return suspend_error;
}
static int camss_a5_runtime_suspend(struct camss_a5 *a);
static int pm_runtime_put_sync_suspend(void *dev) {
 (void)dev;++pm_calls;pm_tick=++ticks;
 int ret=camss_a5_runtime_suspend(active);return pm_error ? pm_error : ret;
}
#include "body.inc"
int main(int argc,char **argv)
{
 assert(argc==2);int scenario=atoi(argv[1]);
 struct camss_a5 a={.resources={.sierra=registers,.enabled_groups=15,.held_domains=7},
 .power_held=true,.cpu_enabled=true,.irq_enabled=true,.initialized=true,.boot_timer=1};active=&a;
 registers[A5_CONTROL/4]=A5_ENABLE|A5_WAKE;registers[A5_STATUS/4]=A5_WFI;
 int expected=0;bool forced=false;
 if(scenario==1){free_error=-EIO;expected=-EIO;}
 if(scenario==2){a.initialized=false;forced=true;reset_error=-EBUSY;expected=-EBUSY;}
 if(scenario==3){pm_error=-EIO;expected=-EIO;}
 if(scenario==4){command_error=-EIO;forced=true;}
 if(scenario==5){registers[A5_STATUS/4]=0;forced=true;}
 if(scenario==6){a.cpu_enabled=false;a.initialized=false;a.irq_enabled=false;a.power_held=false;backing=false;a.resources.enabled_groups=0;a.resources.held_domains=0;}
 if(scenario==7){stuck_control=true;forced=true;}
 if(scenario==8){stuck_control=true;forced=true;reset_error=-EBUSY;expected=-EBUSY;}
 if(scenario==9){assert(camss_a5_runtime_suspend(&a)==-EBUSY && !suspend_calls && !reset_tick);}
 if(scenario==10){suspend_error=-EIO;expected=-EIO;}
 if(scenario==11){
  assert(!quiesce_locked(&a) && !a.cpu_enabled && !a.irq_enabled && !a.initialized && !a.reset_asserted);
  assert(backing && a.power_held && !reset_tick && !free_tick && !pm_calls);
  assert(!quiesce_locked(&a) && backing && a.power_held && !reset_tick && !free_tick && !pm_calls);
 }
 if(scenario==12){a.initialized=false;forced=true;}
 assert(stop_locked(&a)==expected && !a.boot_timer);
 if(scenario==2 || scenario==8){
  assert(backing && a.cpu_enabled && !a.irq_enabled && a.power_held && !a.reset_asserted && !free_tick && !pm_calls && !captures);
  reset_error=0;assert(!stop_locked(&a));
 }
 if(scenario==1){assert(backing && a.power_held && !a.cpu_enabled && !reset_tick && !pm_calls);free_error=0;assert(!stop_locked(&a));}
 assert(!a.cpu_enabled && !a.irq_enabled && !a.initialized && !backing && !a.power_held);
 assert((reset_tick!=0)==forced && a.reset_asserted==forced);
 if(scenario!=6){assert(pm_calls==1 && suspend_calls==1 && pm_tick>free_tick && !a.resources.enabled_groups && !a.resources.held_domains);}
 else assert(!pm_calls && !suspend_calls);
 if(scenario==4)assert(a.pc_error==-EIO);
 if(scenario==5)assert(a.pc_error==-ETIMEDOUT);
 if(scenario==7 || scenario==8)assert(a.pc_error==-EIO);
 unsigned old_pm=pm_calls,old_suspend=suspend_calls,old_reset=reset_tick;
 assert(!stop_locked(&a) && pm_calls==old_pm && suspend_calls==old_suspend && reset_tick==old_reset);
 puts("A5_COOPERATIVE_STOP_MODEL_PASS");
}
