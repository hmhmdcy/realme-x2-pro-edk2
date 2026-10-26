/* Seventeen exact current functions. All MMIO/PHY/PM/IRQ/request boundaries
 * below are fake. No physical HALT, DMA lifetime or Linux IRQ timing proof. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32; typedef uint64_t u64; typedef int irqreturn_t; typedef int pm_message_t;
#define PMSG_RESUME 1
#define PMSG_AUTO_RESUME 2
#define PMSG_IS_AUTO(x) ((x)==PMSG_AUTO_RESUME)
#define DWC3_GCTL_PRTCAP_DEVICE 1
#define DWC3_GCTL_PRTCAP_HOST 2
#define DWC3_GCTL_PRTCAP_OTG 3
#define DWC3_OTG_ROLE_HOST 1
#define DWC3_OTG_ROLE_DEVICE 2
#define DWC3_ERR_NONE 0
#define DWC3_ERR_RECOVERY 1
#define DWC3_ERR_UNRECOVERABLE 2
#define DWC3_ERR_RECOVERY_MAX 3
#define DWC3_GUSB2PHYCFG(i) (0+(i))
#define DWC3_DCTL 4
#define DWC3_DSTS 5
#define DWC3_DEVTEN 6
#define DWC3_GEVNTCOUNT(i) 7
#define DWC3_GEVNTADRLO(i) 8
#define DWC3_GEVNTADRHI(i) 9
#define DWC3_GEVNTSIZ(i) 10
#define DWC3_DCTL_RUN_STOP 1U
#define DWC3_DCTL_TRGTULST_MASK 2U
#define DWC3_DCTL_TRGTULST_RX_DET 4U
#define DWC3_DCTL_KEEP_CONNECT 8U
#define DWC3_DSTS_DEVCTRLHLT 1U
#define DWC3_GUSB2PHYCFG_SUSPHY 64U
#define DWC3_GUSB2PHYCFG_ENBLSLPM 128U
#define DWC3_GEVNTSIZ_INTMASK 0x80000000U
#define DWC3_GEVNTSIZ_SIZE(x) ((u32)(x))
#define DWC3_GEVNTCOUNT_MASK 0xffffU
#define DWC3_EVENT_PENDING 1U
#define DWC3_VER_IS_WITHIN(...) false
#define DWC3_VER_IS_PRIOR(...) false
#define EP0_SETUP_PHASE 0
#define DWC3_PULL_UP_TIMEOUT 500
#define USB_STATE_NOTATTACHED 0
#define IRQ_NONE 0
#define IRQ_HANDLED 1
#define IRQ_WAKE_THREAD 2
#define msecs_to_jiffies(x) (x)
#define lower_32_bits(x) ((u32)(x))
#define upper_32_bits(x) ((u32)((x)>>32))
#define min(a,b) ((a)<(b)?(a):(b))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
enum { SUSPENDED, ACTIVE, RESUMING };
struct device { int rpm, refs, puts, disables, pm_enables, marks; };
struct usb_gadget { int state; };
struct work_struct { int queued; };
struct dwc3;
struct dwc3_ep { int number; };
struct dwc3_event_buffer { struct dwc3 *dwc; u32 count,flags,lpos,length; u64 dma; char *cache,*buf; };
struct dwc3 {
 struct device *dev; struct usb_gadget *gadget; void *gadget_driver,*reset;
 int current_dr_role,current_otg_role,num_usb2_ports,num_usb3_ports,irq_gadget,lock,connect_mutex;
 void *usb2_generic_phy[2],*usb3_generic_phy[2];
 bool needs_full_reinit,dis_u2_susphy_quirk,dis_enblslpm_quirk,susphy_state;
 bool pending_events,softconnect,pullups_connected,connected,delayed_status;
 int ep0state,ep0_in_setup,err_state; u32 err_recovery_count; u64 err_event_seq;
 struct work_struct err_recovery_work; struct dwc3_event_buffer *ev_buf; struct dwc3_ep *eps[2];
};
static struct device dev; static struct usb_gadget gadget; static struct dwc3 d;
static struct dwc3_ep eps[2]; static struct dwc3_event_buffer evt; static char cache[64],dma_buf[64];
static struct {
 u32 regs[32]; bool powered,running,on_timeout,off_timeout,irq_registered;
 int init_errno,attempt,start_errno[4],core_inits,core_exits,phy_init,phy_power,clock_on,clock_off,resets;
 int spin,mutex,queues,irq_depth,irq_joins,run_on,run_off,ep_stops,callbacks,after_exit_access;
 int inject_at_attempt; bool inject_after_unlock; char log[4096];
} f;
static unsigned cases;
static void dwc3_schedule_err_recovery(struct dwc3 *p);
static int dwc3_event_buffers_setup(struct dwc3 *p); /* actual definition is non-static below */
static void take(void){assert(f.spin==0);f.spin++;}
static void drop(void){assert(f.spin==1);f.spin--;}
static void unlock_and_deliver(void){
 drop();
 if(f.inject_after_unlock){
  f.inject_after_unlock=false;assert(f.irq_registered&&f.irq_depth==0);
  /* A real IRQ may take the released lock before recovery publication. */
  take();dwc3_schedule_err_recovery(&d);drop();
 }
}
#define spin_lock_irqsave(lock,flags) do{(void)(lock);(flags)=0;take();}while(0)
#define spin_unlock_irqrestore(lock,flags) do{(void)(lock);(void)(flags);unlock_and_deliver();}while(0)
#define spin_lock(lock) do{(void)(lock);take();}while(0)
#define spin_unlock(lock) do{(void)(lock);drop();}while(0)
static void mutex_lock(int *p){(void)p;assert(!f.mutex&&!f.spin);f.mutex++;}
static void mutex_unlock(int *p){(void)p;assert(f.mutex==1&&!f.spin);f.mutex--;}
static void lockdep_assert_held(int *p){(void)p;assert(f.mutex);}
static bool pm_runtime_suspended(struct device *p){return p->rpm==SUSPENDED;}
static bool device_may_wakeup(struct device *p){(void)p;return false;}
static void dev_err(struct device *p,const char *fmt,...){
 (void)p;va_list args;va_start(args,fmt);size_t n=strlen(f.log);vsnprintf(f.log+n,sizeof(f.log)-n,fmt,args);va_end(args);
}
#define dev_warn dev_err
static u32 dwc3_readl(struct dwc3 *p,u32 reg){
 (void)p;assert(reg<32);if(!f.powered)f.after_exit_access++;
 if(reg==DWC3_DSTS){if(f.running)return f.on_timeout&&f.run_on==1?DWC3_DSTS_DEVCTRLHLT:0;return f.off_timeout?0:DWC3_DSTS_DEVCTRLHLT;}
 return f.regs[reg];
}
static void dwc3_writel(struct dwc3 *p,u32 reg,u32 value){
 (void)p;assert(reg<32);if(!f.powered)f.after_exit_access++;f.regs[reg]=value;
 if(reg==DWC3_DEVTEN&&!value&&f.inject_at_attempt==f.attempt){f.inject_after_unlock=true;f.inject_at_attempt=0;}
}
static void dwc3_gadget_dctl_write_safe(struct dwc3 *p,u32 reg){(void)p;f.regs[DWC3_DCTL]=reg;f.running=!!(reg&DWC3_DCTL_RUN_STOP);if(f.running)f.run_on++;else f.run_off++;}
static void __dwc3_gadget_set_speed(struct dwc3 *p){(void)p;}
static void dwc3_pre_run_stop(struct dwc3 *p,int on){(void)p;(void)on;}
static void usleep_range(unsigned a,unsigned b){(void)a;(void)b;}
static void __dwc3_gadget_ep_disable(struct dwc3_ep *p){(void)p;assert(f.spin);f.ep_stops++;}
static int dwc3_core_soft_reset(struct dwc3 *p){
 (void)p;if(!f.powered){f.after_exit_access++;return -EIO;}f.attempt++;return 0;
}
static int __dwc3_gadget_start(struct dwc3 *p){(void)p;assert(f.attempt>0&&f.attempt<4);if(f.start_errno[f.attempt])return f.start_errno[f.attempt];f.regs[DWC3_DEVTEN]=0xff;return 0;}
static void dwc3_stop_active_transfers(struct dwc3 *p){(void)p;assert(f.spin);}
static void dwc3_ep0_send_delayed_status(struct dwc3 *p){(void)p;}
static void reinit_completion(int *p){*p=0;}
static int wait_for_completion_timeout(int *p,int timeout){(void)p;(void)timeout;return 1;}
static void dwc3_ep0_reset_state(struct dwc3 *p){p->ep0state=EP0_SETUP_PHASE;}
static void usb_gadget_set_state(struct usb_gadget *p,int state){p->state=state;}
static void dwc3_disconnect_gadget_sleepable(struct dwc3 *p){(void)p;assert(f.mutex&&!f.spin);f.callbacks++;}
static void synchronize_irq(int irq){(void)irq;assert(f.irq_registered&&!f.spin);f.irq_joins++;}
static bool schedule_work(struct work_struct *work){work->queued=1;f.queues++;return true;}
static void reset_control_assert(void *p){(void)p;f.resets++;}
static int reset_control_deassert(void *p){(void)p;return 0;}
static int dwc3_clk_enable(struct dwc3 *p){(void)p;f.clock_on++;return 0;}
static void dwc3_clk_disable(struct dwc3 *p){(void)p;f.clock_off++;}
static void dwc3_phy_power_off(struct dwc3 *p){(void)p;assert(f.phy_power==1);f.phy_power--;f.powered=false;f.core_exits++;}
static void dwc3_phy_exit(struct dwc3 *p){(void)p;assert(f.phy_init==1);f.phy_init--;}
static int dwc3_core_init(struct dwc3 *p){
 f.core_inits++;if(f.init_errno)return f.init_errno;f.phy_init++;f.phy_power++;f.powered=true;return dwc3_event_buffers_setup(p);
}
static void dwc3_set_prtcap(struct dwc3 *p,int role,bool keep){(void)p;(void)role;(void)keep;}
static void dwc3_enable_susphy(struct dwc3 *p,bool on){(void)p;(void)on;}
static void phy_pm_runtime_get_sync(void *p){(void)p;}
static void dwc3_otg_init(struct dwc3 *p){(void)p;}
static void dwc3_otg_host_init(struct dwc3 *p){(void)p;}
static void pm_runtime_get(struct device *p){p->refs++;}
static void pm_runtime_put(struct device *p){assert(p->refs>0);p->refs--;p->puts++;}
static void disable_irq_nosync(int irq){(void)irq;f.irq_depth++;}
static void enable_irq(int irq){(void)irq;assert(f.irq_depth>0);f.irq_depth--;}
static void pm_runtime_mark_last_busy(struct device *p){p->marks++;}
static void pinctrl_pm_select_default_state(struct device *p){(void)p;}
static void pm_runtime_disable(struct device *p){p->disables++;}
static int pm_runtime_set_active(struct device *p){p->rpm=ACTIVE;return 0;}
static void pm_runtime_set_suspended(struct device *p){p->rpm=SUSPENDED;}
static void pm_runtime_enable(struct device *p){assert(p->disables>0);p->disables--;p->pm_enables++;}
#include "actual-functions.inc"
#include "rejected-diagnostic-functions.inc"

static void setup(void){
 memset(&d,0,sizeof(d));memset(&dev,0,sizeof(dev));memset(&f,0,sizeof(f));memset(&evt,0,sizeof(evt));
 d.dev=&dev;d.gadget=&gadget;d.gadget_driver=&d;d.softconnect=true;d.current_dr_role=DWC3_GCTL_PRTCAP_DEVICE;d.susphy_state=true;
 d.irq_gadget=7;dev.rpm=RESUMING;f.irq_registered=true;evt.dwc=&d;evt.buf=dma_buf;evt.cache=cache;evt.length=64;evt.dma=0x1234;d.ev_buf=&evt;
 for(int i=0;i<2;i++){eps[i].number=i;d.eps[i]=&eps[i];}
}
static void incoming_suspended_irq(void){
 dev.rpm=SUSPENDED;assert(dwc3_check_event_buf(&evt)==IRQ_HANDLED);
 assert(dev.refs==1&&d.pending_events&&f.irq_depth==1);dev.rpm=RESUMING;
}
static void final_failure(void){f.on_timeout=true;f.off_timeout=true;}
static void runtime_pm_error_transition(int ret){
 /* Exact cached runtime.c 934..945 does this after a negative callback.
  * This adapter is explicit, not a claim to simulate the whole PM core. */
 if(ret)dev.rpm=SUSPENDED;else dev.rpm=ACTIVE;
}
int main(void){
 setup();incoming_suspended_irq();final_failure();
 assert(dwc3_runtime_resume(&d)==0);assert(f.powered&&f.phy_power==1&&d.err_state==DWC3_ERR_UNRECOVERABLE);
 assert(!d.pending_events&&dev.refs==0&&f.irq_depth==0&&strstr(f.log,"recovery=-110"));cases++;
 puts("current: actual failed gadget/recovery errno swallowed; active resources and pending tail retained");

 setup();incoming_suspended_irq();final_failure();
 int ret=rejected_return_dwc3_runtime_resume(&d);assert(ret==-ETIMEDOUT);runtime_pm_error_transition(ret);
 assert(dev.rpm==SUSPENDED&&f.powered&&f.phy_init==1&&f.phy_power==1);
 assert(d.pending_events&&dev.refs==1&&f.irq_depth==1&&dev.puts==0);cases++;
 puts("rejected: direct runtime errno leaves core powered, PM suspended, exact pending-event ref and IRQ depth held");

 setup();final_failure();ret=rejected_return_dwc3_pm_resume(&d);
 assert(ret==-ETIMEDOUT&&dev.rpm==SUSPENDED&&f.powered&&f.phy_power==1&&dev.disables==0);cases++;
 puts("rejected: actual system caller marks suspended after negative gadget path with powered resources");

 setup();final_failure();f.inject_at_attempt=1;ret=rejected_exit_dwc3_pm_resume(&d);
 assert(ret==-ETIMEDOUT&&!f.powered&&f.phy_power==0&&f.irq_registered);
 assert(f.regs[DWC3_GEVNTADRLO(0)]==0x1234&&f.regs[DWC3_GEVNTSIZ(0)]==64);
 assert(d.err_state==DWC3_ERR_RECOVERY&&d.err_recovery_work.queued&&f.irq_joins>0);
 dwc3_err_recovery_work(&d.err_recovery_work);assert(f.after_exit_access>0);cases++;
 puts("rejected: HALT unknown skips event cleanup yet core_exit releases PHY; queued actual recovery work accesses after exit");

 setup();f.start_errno[1]=-EIO;f.start_errno[2]=-ENOMEM;f.inject_at_attempt=2;
 ret=rejected_exit_dwc3_pm_resume(&d);assert(ret==-EIO&&!f.powered&&f.irq_registered);
 assert(f.regs[DWC3_GEVNTADRLO(0)]==0&&d.err_state==DWC3_ERR_RECOVERY&&d.err_recovery_work.queued);
 dwc3_err_recovery_work(&d.err_recovery_work);assert(f.after_exit_access>0);cases++;
 puts("rejected: even HALT-confirmed event cleanup plus IRQ join does not drain separately queued recovery work");

 setup();f.start_errno[1]=-EIO;
 assert(dwc3_core_init_for_resume(&d)==0);assert(dwc3_gadget_resume(&d)==-EIO);
 assert(d.err_state==DWC3_ERR_NONE&&f.running&&d.pullups_connected&&strstr(f.log,"recovery=0"));cases++;
 puts("API gap: the same negative primary can accompany successful final reconnect; core needs an outcome, not just errno");

 setup();f.init_errno=-ENODEV;ret=rejected_return_dwc3_pm_resume(&d);
 assert(ret==-ENODEV&&!f.powered&&!f.phy_power&&!f.phy_init&&f.clock_off==1&&f.resets==1&&dev.rpm==SUSPENDED);cases++;
 puts("control: original init-for-resume failure uses its existing clock/reset unwind before gadget starts");
 printf("{\"passed\":true,\"cases\":%u,\"safe_gadget_failure_unwind_proved\":false,\"deployable_patch\":false}\n",cases);
 return 0;
}
