#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
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
struct camss_a5_session{struct camss_a5_session *next;};
struct resource{void *sierra;unsigned enabled_groups,held_domains,ipe_reset_acks[2];};
struct camss_a5{struct resource resources;void *dev,*reset;int irq,boot_timer,pc_error;bool cpu_enabled,irq_enabled,initialized,reset_asserted,power_held,ipe_dma_pending,session_uncertain;unsigned session_count;struct{struct camss_a5_session *first;}sessions;};
#define list_for_each_entry_safe(p,n,h,m) for(p=(h)->first,n=p?p->next:NULL;p;p=n,n=p?p->next:NULL)
static struct camss_a5 *active;
static u32 registers[256];
static bool held,backing,stuck_before,stuck_after;
static int assert_error,deassert_error,ipe_error,free_error,pm_error,command_error,destroy_error;
static unsigned tick,assert_tick,deassert_tick,ipe_tick,free_tick,pm_tick,asserts,deasserts,pm_calls,irq_calls,commands,destroys;
static void hrtimer_cancel(int *p){*p=0;}
static u32 readl(void *p){assert(!held);if(stuck_after && p==registers+A5_CONTROL/4)return A5_ENABLE|A5_WAKE;return *(u32*)p;}
static void writel(u32 value,void *p){assert(!held);if(stuck_before && p==registers+A5_CONTROL/4)value|=A5_ENABLE|A5_WAKE;*(u32*)p=value;}
static int reset_control_assert(void *p){(void)p;++asserts;assert_tick=++tick;if(assert_error)return assert_error;held=true;registers[A5_CONTROL/4]=0;stuck_before=false;return 0;}
static int reset_control_deassert(void *p){(void)p;++deasserts;deassert_tick=++tick;if(deassert_error)return deassert_error;held=false;return 0;}
static void udelay(unsigned value){assert(value==2 && held);}
static void disable_irq(int irq){(void)irq;++irq_calls;}
static int send_command(struct camss_a5 *a,u32 type,u32 response){assert(a->cpu_enabled && a->initialized && a->irq_enabled && !held && type==SYS_PC_PREP && response==PC_DONE);++commands;return command_error;}
#define readl_poll_timeout(addr,value,condition,interval,timeout) ({(void)(interval);(void)(timeout);value=readl(addr);(condition)?0:-ETIMEDOUT;})
static int ipe_destroy_locked(struct camss_a5 *a,struct camss_a5_session *s){++destroys;if(destroy_error){a->session_uncertain=true;return destroy_error;}assert(a->sessions.first==s && a->session_count);a->sessions.first=s->next;--a->session_count;return 0;}
static int camss_a5_ipe_quiesce(struct resource *r){assert(!held && !active->cpu_enabled && !active->irq_enabled);ipe_tick=++tick;if(ipe_error)return ipe_error;r->ipe_reset_acks[0]=r->ipe_reset_acks[1]=3;return 0;}
static void invalidate_sessions(struct camss_a5 *a){assert(!a->cpu_enabled && !a->ipe_dma_pending && !held);a->sessions.first=NULL;a->session_count=0;a->session_uncertain=false;}
static void capture_shared_state(struct camss_a5 *a){assert(!a->cpu_enabled && !a->irq_enabled && !a->ipe_dma_pending && !held);}
static int free_memory(struct camss_a5 *a){assert(!a->cpu_enabled && !a->irq_enabled && !a->ipe_dma_pending && !held);if(backing){free_tick=++tick;if(free_error)return free_error;backing=false;}return 0;}
static bool camss_a5_backing_owned(struct camss_a5 *a){(void)a;return backing;}
static int camss_a5_resources_suspend(struct resource *r){assert(!held && !active->cpu_enabled && !backing);r->enabled_groups=r->held_domains=0;return 0;}
static int camss_a5_runtime_suspend(struct camss_a5 *a);
static int pm_runtime_put_sync_suspend(void *p){(void)p;++pm_calls;pm_tick=++tick;int ret=camss_a5_runtime_suspend(active);return pm_error?pm_error:ret;}
#include "body.inc"
int main(int argc,char **argv)
{
 assert(argc==2);unsigned mode=atoi(argv[1]);backing=true;
 struct camss_a5_session two={0},one={.next=&two};
 struct camss_a5 a={.resources={.sierra=registers,.enabled_groups=15,.held_domains=7},.power_held=true,.cpu_enabled=true,.irq_enabled=true,.initialized=true,.boot_timer=1};active=&a;
 registers[A5_CONTROL/4]=A5_ENABLE|A5_WAKE;registers[A5_STATUS/4]=A5_WFI;
 int expected=0;bool force=false;
 if(mode==1 || mode==7 || mode==9 || mode==15 || mode==21){a.session_uncertain=true;a.ipe_dma_pending=true;a.session_count=2;a.sessions.first=&one;force=true;}
 if(mode==2){a.initialized=false;force=true;}
 if(mode==3){command_error=-EIO;force=true;}
 if(mode==4){registers[A5_STATUS/4]=0;force=true;}
 if(mode==5){stuck_before=true;force=true;}
 if(mode==6){a.initialized=false;assert_error=-EBUSY;expected=-EBUSY;force=true;}
 if(mode==7){deassert_error=-EIO;expected=-EIO;}
 if(mode==8){a.initialized=false;stuck_after=true;expected=-EIO;force=true;}
 if(mode==9){ipe_error=-ETIMEDOUT;expected=-ETIMEDOUT;}
 if(mode==10){free_error=-EIO;expected=-EIO;}
 if(mode==11){pm_error=-EIO;expected=-EIO;}
 if(mode==12){a.cpu_enabled=a.irq_enabled=a.initialized=false;}
 if(mode==13){a.session_count=2;a.sessions.first=&one;destroy_error=-ETIMEDOUT;force=true;}
 if(mode==14){a.cpu_enabled=a.irq_enabled=a.initialized=a.power_held=false;backing=false;a.resources.enabled_groups=a.resources.held_domains=0;}
 if(mode==15 || mode==16 || mode==19){held=a.reset_asserted=true;a.initialized=a.irq_enabled=false;registers[A5_CONTROL/4]=0;force=false;}
 if(mode==16){a.cpu_enabled=false;deassert_error=-EIO;expected=-EIO;}
 if(mode==17){a.irq_enabled=false;force=true;}
 if(mode==18){assert(camss_a5_runtime_suspend(&a)==-EBUSY && !pm_calls);}
 if(mode==19){a.cpu_enabled=false;stuck_after=true;expected=-EIO;}
 if(mode==20){a.session_count=2;a.sessions.first=&one;}
 if(mode==21){assert(!quiesce_locked(&a) && backing && a.power_held && !free_tick && !pm_calls && !held && !a.ipe_dma_pending);}
 assert(stop_locked(&a)==expected && !a.boot_timer);
 if(expected && mode!=11){
  assert(backing && a.power_held && !pm_calls);
  if(mode!=10)assert(!free_tick);
  if(mode==7 || mode==16)assert(held && a.reset_asserted);
  if(mode==8 || mode==19)assert(a.cpu_enabled);
  if(mode==9)assert(a.ipe_dma_pending && a.resources.ipe_reset_acks[0]==0);
  assert_error=deassert_error=ipe_error=free_error=0;stuck_after=false;assert(!stop_locked(&a));
 }
 assert(!held && !a.reset_asserted && !a.cpu_enabled && !a.irq_enabled && !a.initialized && !a.ipe_dma_pending && !backing && !a.power_held);
 if(force)assert(asserts && deasserts && deassert_tick>assert_tick);
 if(mode==1 || mode==7 || mode==9 || mode==15 || mode==21)assert(a.resources.ipe_reset_acks[0]==3 && a.resources.ipe_reset_acks[1]==3 && free_tick>ipe_tick);
 if(mode!=14)assert(pm_calls==1 && pm_tick>free_tick);else assert(!pm_calls);
 if(mode==17)assert(!commands);
 if(mode==20)assert(destroys==2 && !asserts);
 unsigned old_asserts=asserts,old_deasserts=deasserts,old_pm=pm_calls;assert(!stop_locked(&a));assert(asserts==old_asserts && deasserts==old_deasserts && pm_calls==old_pm);
 puts("STOP_PULSE_MODEL_PASS");return 0;
}
