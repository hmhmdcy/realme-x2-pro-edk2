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
struct camss_a5 {
 struct {void *sierra;} resources;
 void *dev,*reset;int irq,boot_timer,pc_error;
 bool cpu_enabled,irq_enabled,initialized,reset_asserted,power_held;
};
static unsigned ticks,reset_tick,free_tick,pm_tick,pm_calls;
static bool backing=true;
static int reset_error,free_error,pm_error,command_error,poll_error;
static u32 registers[256];
static void hrtimer_cancel(int *t) {*t=0;}
static u32 readl(void *p) {return *(u32 *)p;}
static void writel(u32 value,void *p) {*(u32 *)p=value;}
static void disable_irq(int irq) {(void)irq;}
static int reset_control_assert(void *reset) {(void)reset;reset_tick=++ticks;return reset_error;}
static int send_command(struct camss_a5 *a,u32 type,u32 response) {(void)a;assert(type==SYS_PC_PREP && response==PC_DONE);return command_error;}
#define readl_poll_timeout(addr,value,condition,interval,timeout) ({ \
 (void)(interval);(void)(timeout);value=readl(addr);(void)(condition);poll_error;})
static void capture_shared_state(struct camss_a5 *a) {(void)a;}
static int free_memory(struct camss_a5 *a) {
 assert(!a->cpu_enabled);assert(!reset_tick || a->reset_asserted);free_tick=++ticks;
 if(free_error)return free_error;backing=false;return 0;
}
static int pm_runtime_put_sync_suspend(void *dev) {(void)dev;++pm_calls;pm_tick=++ticks;return pm_error;}
#include "stop-method.inc"
int main(int argc,char **argv)
{
 assert(argc==2);int scenario=atoi(argv[1]);struct camss_a5 a={.resources.sierra=registers,.power_held=true,.cpu_enabled=true,.irq_enabled=true};
 int expected=0;registers[A5_CONTROL/4]=A5_ENABLE|A5_WAKE;registers[A5_STATUS/4]=A5_WFI;
 if(scenario==1){free_error=-EIO;expected=-EIO;}
 if(scenario==2){reset_error=-EBUSY;expected=-EBUSY;}
 if(scenario==3){pm_error=-EIO;expected=-EIO;}
 if(scenario==4){a.initialized=true;command_error=-EIO;}
 if(scenario==5){a.initialized=true;poll_error=-ETIMEDOUT;}
 if(scenario==6){a.cpu_enabled=false;a.power_held=false;}
 assert(stop_locked(&a)==expected && !a.boot_timer);
 if(scenario==2){assert(backing && a.cpu_enabled && a.power_held && !free_tick && !pm_calls);return 0;}
 assert(!a.cpu_enabled);
 if(scenario==1){
  assert(backing && a.power_held && !pm_calls);free_error=0;assert(stop_locked(&a)==0);
 }
 assert(!backing && !a.power_held);
 if(scenario!=6)assert(pm_tick>free_tick && free_tick>reset_tick);
 else assert(!pm_calls && !reset_tick);
 if(scenario==4)assert(a.pc_error==-EIO);
 if(scenario==5)assert(a.pc_error==-ETIMEDOUT);
 unsigned old_pm=pm_calls;assert(stop_locked(&a)==0 && pm_calls==old_pm);
 puts("A5_STOP_DMA_ORDER_PASS");
}
