/* Exact extracted functions; fake MMIO/endpoint/IRQ/PM boundaries.
 * This fixture checks the new receipt, never physical HALT or PM unwind. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef uint64_t u64;
#define DWC3_GCTL_PRTCAP_DEVICE 1
#define DWC3_GCTL_PRTCAP_OTG 3
#define DWC3_ERR_NONE 0
#define DWC3_ERR_RECOVERY 1
#define DWC3_ERR_UNRECOVERABLE 2
#define DWC3_ERR_RECOVERY_MAX 3
#define DWC3_GUSB2PHYCFG(i) (0+(i))
#define DWC3_DCTL 4
#define DWC3_DSTS 5
#define DWC3_DEVTEN 6
#define DWC3_DCTL_RUN_STOP 1U
#define DWC3_DCTL_TRGTULST_MASK 2U
#define DWC3_DCTL_TRGTULST_RX_DET 4U
#define DWC3_DCTL_KEEP_CONNECT 8U
#define DWC3_DSTS_DEVCTRLHLT 1U
#define DWC3_GUSB2PHYCFG_SUSPHY 64U
#define DWC3_GUSB2PHYCFG_ENBLSLPM 128U
#define DWC3_VER_IS_WITHIN(...) false
#define DWC3_VER_IS_PRIOR(...) false
#define EP0_SETUP_PHASE 0
#define DWC3_PULL_UP_TIMEOUT 500
#define USB_STATE_NOTATTACHED 0
#define msecs_to_jiffies(x) (x)
struct device { bool suspended; };
struct usb_gadget { int state; };
struct dwc3_ep { int number; };
struct work_struct { bool queued; };
struct dwc3 {
 struct device *dev; struct usb_gadget *gadget; void *gadget_driver;
 int current_dr_role,irq_gadget,lock,connect_mutex,ep0state,ep0_in_setup,err_state;
 bool softconnect,pullups_connected,connected,delayed_status;
 u32 err_recovery_count; u64 err_event_seq;
 struct work_struct err_recovery_work; struct dwc3_ep *eps[2];
};
static struct device dev;
static struct usb_gadget gadget;
static struct dwc3 d;
static struct dwc3_ep eps[2];
static struct {
 u32 regs[16]; int attempt,start_errno[4],reset_errno[4];
 int spin,mutex,queues,joins,run_on,run_off,stops,event_setups,callbacks;
 int inject_start_at;
 bool running,on_timeout,off_timeout,drop_intent_on_disconnect,post_publish_irq,post_publish_ready;
 char log[4096];
} f;
static unsigned cases;
static void dwc3_schedule_err_recovery(struct dwc3 *dwc);
static void take(void){assert(f.spin==0);f.spin=1;}
static void drop(void){assert(f.spin==1);f.spin=0;}
static void inject_irq(void){take();dwc3_schedule_err_recovery(&d);drop();}
static void unlock(void){
 drop();
 if(f.post_publish_irq&&f.post_publish_ready&&d.err_state==DWC3_ERR_NONE){
  f.post_publish_irq=false;inject_irq();
 }
}
#define spin_lock_irqsave(p,flags) do{(void)(p);(flags)=0;take();}while(0)
#define spin_unlock_irqrestore(p,flags) do{(void)(p);(void)(flags);unlock();}while(0)
static void mutex_lock(int *p){(void)p;assert(!f.mutex&&!f.spin);f.mutex=1;}
static void mutex_unlock(int *p){(void)p;assert(f.mutex==1&&!f.spin);f.mutex=0;}
static void lockdep_assert_held(int *p){(void)p;assert(f.mutex);}
static bool pm_runtime_suspended(struct device *p){return p->suspended;}
static void dev_err(struct device *p,const char *fmt,...){
 (void)p;va_list args;va_start(args,fmt);size_t n=strlen(f.log);
 vsnprintf(f.log+n,sizeof(f.log)-n,fmt,args);va_end(args);
}
#define dev_warn dev_err
static u32 dwc3_readl(struct dwc3 *p,u32 reg){
 (void)p;assert(reg<16);
 if(reg==DWC3_DSTS){
  if(f.running)return f.on_timeout&&f.run_on==1?DWC3_DSTS_DEVCTRLHLT:0;
  return f.off_timeout?0:DWC3_DSTS_DEVCTRLHLT;
 }
 return f.regs[reg];
}
static void dwc3_writel(struct dwc3 *p,u32 reg,u32 value){(void)p;assert(reg<16);f.regs[reg]=value;}
static void dwc3_gadget_dctl_write_safe(struct dwc3 *p,u32 reg){
 (void)p;f.regs[DWC3_DCTL]=reg;f.running=!!(reg&DWC3_DCTL_RUN_STOP);
 if(f.running){f.run_on++;if(f.attempt==2)f.post_publish_ready=true;}else f.run_off++;
}
static void __dwc3_gadget_set_speed(struct dwc3 *p){(void)p;}
static void dwc3_pre_run_stop(struct dwc3 *p,int on){(void)p;(void)on;}
static void usleep_range(unsigned a,unsigned b){(void)a;(void)b;}
static void __dwc3_gadget_ep_disable(struct dwc3_ep *p){(void)p;assert(f.spin);f.stops++;}
static int dwc3_core_soft_reset(struct dwc3 *p){
 (void)p;f.attempt++;assert(f.attempt<4);return f.reset_errno[f.attempt];
}
static int dwc3_event_buffers_setup(struct dwc3 *p){(void)p;f.event_setups++;return 0;}
static int __dwc3_gadget_start(struct dwc3 *p){
 (void)p;assert(f.attempt>0&&f.attempt<4);
 if(f.inject_start_at==f.attempt){f.inject_start_at=0;inject_irq();}
 if(f.start_errno[f.attempt])return f.start_errno[f.attempt];
 f.regs[DWC3_DEVTEN]=0xff;return 0;
}
static void dwc3_stop_active_transfers(struct dwc3 *p){(void)p;assert(f.spin);}
static void dwc3_ep0_send_delayed_status(struct dwc3 *p){(void)p;}
static void reinit_completion(int *p){*p=0;}
static int wait_for_completion_timeout(int *p,int t){(void)p;(void)t;return 1;}
static void dwc3_ep0_reset_state(struct dwc3 *p){p->ep0state=EP0_SETUP_PHASE;}
static void usb_gadget_set_state(struct usb_gadget *p,int state){p->state=state;}
static void dwc3_disconnect_gadget_sleepable(struct dwc3 *p){
 assert(f.mutex&&!f.spin);f.callbacks++;
 if(f.drop_intent_on_disconnect)p->softconnect=false;
}
static void synchronize_irq(int irq){(void)irq;assert(!f.spin);f.joins++;}
static bool schedule_work(struct work_struct *p){p->queued=true;f.queues++;return true;}
#include "actual-functions.inc"
#include "previous-resume.inc"

static void setup(void){
 memset(&d,0,sizeof(d));memset(&dev,0,sizeof(dev));memset(&f,0,sizeof(f));
 d.dev=&dev;d.gadget=&gadget;d.gadget_driver=&d;d.softconnect=true;
 d.current_dr_role=DWC3_GCTL_PRTCAP_DEVICE;d.irq_gadget=7;d.err_event_seq=17;
 for(int i=0;i<2;i++){eps[i].number=i;d.eps[i]=&eps[i];}
}
static struct dwc3_device_resume_result outcome(void){
 struct dwc3_device_resume_result r;memset(&r,0xa5,sizeof(r));
 dwc3_gadget_resume_result(&d,&r);assert(!f.spin&&!f.mutex);return r;
}
static void skipped(struct dwc3_device_resume_result r,const char *stage,int primary){
 assert(!r.requested&&!r.recovery_attempted&&!r.operation_completed);
 assert(r.primary==primary&&r.recovery==0&&!r.detail.pending&&!r.detail.reconnected);
 assert(r.detail.start_seq==0&&r.detail.end_seq==0&&!strcmp(r.detail.stage,stage));
 assert(f.attempt==0&&f.queues==0&&f.run_on==0);
}
static void configure(int n){
 switch(n){
 case 0:d.gadget_driver=NULL;break;
 case 1:d.softconnect=false;break;
 case 2:d.current_dr_role=DWC3_GCTL_PRTCAP_OTG;break;
 case 3:break;
 case 4:f.start_errno[1]=-EIO;break;
 case 5:f.on_timeout=true;f.off_timeout=true;break;
 case 6:f.start_errno[1]=-EIO;f.start_errno[2]=-ENOSPC;break;
 case 7:f.start_errno[1]=-EIO;f.drop_intent_on_disconnect=true;break;
 case 8:f.start_errno[1]=-ENOMEM;d.err_state=DWC3_ERR_UNRECOVERABLE;break;
 case 9:d.err_state=DWC3_ERR_UNRECOVERABLE;break;
 case 10:f.inject_start_at=1;break;
 case 11:f.start_errno[1]=-EIO;f.inject_start_at=2;break;
 case 12:f.start_errno[1]=-EIO;f.post_publish_irq=true;break;
 case 13:dev.suspended=true;break;
 case 14:f.start_errno[1]=-EIO;d.err_recovery_count=DWC3_ERR_RECOVERY_MAX;break;
 case 15:d.err_state=DWC3_ERR_RECOVERY;d.err_recovery_work.queued=true;break;
 default:assert(false);
 }
}
struct trace {
 int ret,attempt,queues,joins,run_on,run_off,stops,event_setups,callbacks,err_state;
 u32 recovery_count,regs[16];u64 seq;bool intent,pullup,running,queued;
};
static struct trace legacy(int scenario,bool previous){
 setup();configure(scenario);struct trace t;memset(&t,0,sizeof(t));
 t.ret=previous?previous_gadget_resume(&d):dwc3_gadget_resume(&d);
 t.attempt=f.attempt;t.queues=f.queues;t.joins=f.joins;t.run_on=f.run_on;t.run_off=f.run_off;
 t.stops=f.stops;t.event_setups=f.event_setups;t.callbacks=f.callbacks;t.err_state=d.err_state;
 t.recovery_count=d.err_recovery_count;memcpy(t.regs,f.regs,sizeof(t.regs));t.seq=d.err_event_seq;
 t.intent=d.softconnect;t.pullup=d.pullups_connected;t.running=f.running;t.queued=d.err_recovery_work.queued;
 assert(!f.spin&&!f.mutex);return t;
}
static void report(const char *message){puts(message);cases++;}
int main(void){
 struct dwc3_device_resume_result r;
 setup();configure(0);skipped(outcome(),"not-requested",0);report("skip: no driver fully initializes a poisoned result");
 setup();configure(1);skipped(outcome(),"not-requested",0);report("skip: no connect intent never labels default recovery zero completed");
 setup();configure(2);skipped(outcome(),"not-device",-EOPNOTSUPP);report("DEVICE entry rejects OTG with zero hardware calls; legacy remains separate");
 setup();configure(3);r=outcome();
 assert(r.requested&&r.primary==0&&!r.recovery_attempted&&r.recovery==0&&r.operation_completed);
 assert(r.detail.reconnected&&!r.detail.pending&&r.detail.start_seq==17&&r.detail.end_seq==17);
 assert(f.attempt==1&&f.run_on==1&&f.running);report("initial connect: actual success has explicit sequence and completion");
 setup();configure(4);r=outcome();
 assert(r.primary==-EIO&&r.recovery_attempted&&r.recovery==0&&r.operation_completed&&r.detail.reconnected);
 assert(f.attempt==2&&f.running&&d.err_state==DWC3_ERR_NONE);report("recovery success retains negative primary and separately proves reconnect");
 setup();configure(5);r=outcome();
 assert(r.primary==-ETIMEDOUT&&r.recovery_attempted&&r.recovery==-ETIMEDOUT&&!r.operation_completed&&!r.detail.reconnected);
 assert(d.err_state==DWC3_ERR_UNRECOVERABLE);report("failed stop: primary and recovery errno remain independent, no completed claim");
 setup();configure(6);r=outcome();
 assert(r.primary==-EIO&&r.recovery==-ENOSPC&&r.recovery_attempted&&!r.detail.reconnected&&!r.operation_completed);
 report("failed reconnect: partial endpoint enable zero completion and separate errno");
 setup();configure(7);r=outcome();
 assert(r.requested&&r.primary==-EIO&&r.recovery_attempted&&r.recovery==0&&!r.detail.reconnected&&!r.operation_completed);
 assert(!d.softconnect&&f.attempt==1);report("disconnect-only zero recovery is not a successful reconnect");
 setup();configure(8);r=outcome();
 assert(r.primary==-ENOMEM&&r.recovery==-EIO&&r.recovery_attempted&&!r.detail.reconnected&&!r.operation_completed);
 assert(d.err_state==DWC3_ERR_UNRECOVERABLE&&f.attempt==1);report("old unrecoverable state is retained after the original first attempt");
 setup();configure(9);r=outcome();
 assert(r.primary==0&&!r.recovery_attempted&&r.detail.reconnected&&!r.operation_completed);
 assert(d.err_state==DWC3_ERR_UNRECOVERABLE&&!r.detail.pending);report("first success never clears an older unrecoverable policy state");
 setup();configure(10);r=outcome();
 assert(r.primary==0&&!r.recovery_attempted&&r.detail.reconnected&&r.detail.pending&&!r.operation_completed);
 assert(r.detail.start_seq==17&&r.detail.end_seq==18&&d.err_recovery_work.queued);
 report("initial-connect IRQ generation is pending at publication, not completed");
 setup();configure(11);r=outcome();
 assert(r.primary==-EIO&&r.recovery==0&&r.recovery_attempted&&r.detail.reconnected&&r.detail.pending&&!r.operation_completed);
 assert(r.detail.start_seq==17&&r.detail.end_seq==18&&d.err_recovery_work.queued);
 report("recovery-connect IRQ generation is retained independently of zero reconnect errno");
 setup();configure(12);r=outcome();
 assert(r.operation_completed&&!r.detail.pending&&d.err_state==DWC3_ERR_RECOVERY&&d.err_recovery_work.queued);
 report("control: a later IRQ may follow the published completion; this is no abort/lifetime token");
 setup();configure(13);r=outcome();
 assert(r.primary==0&&r.detail.reconnected&&!r.operation_completed&&f.run_on==0);
 report("suspended caller cannot convert the run-stop skip zero to completed");
 setup();configure(14);r=outcome();
 assert(r.primary==-EIO&&r.recovery==-EIO&&r.recovery_attempted&&!r.detail.reconnected&&!r.operation_completed&&f.attempt==1);
 report("existing count limit initializes reconnected false and preserves policy");
 setup();configure(15);r=outcome();
 assert(r.primary==0&&!r.recovery_attempted&&r.detail.reconnected&&!r.detail.pending&&!r.operation_completed);
 assert(d.err_state==DWC3_ERR_RECOVERY&&d.err_recovery_work.queued);
 report("existing queued recovery is not silently cleared by a first-connect zero");
 setup();struct dwc3_recovery_result detail;memset(&detail,0xa5,sizeof(detail));mutex_lock(&d.connect_mutex);
 assert(dwc3_gadget_recover_locked(&d,false,&detail)==0);mutex_unlock(&d.connect_mutex);
 assert(!detail.pending&&!detail.reconnected&&detail.start_seq==17&&detail.end_seq==17&&!strcmp(detail.stage,"stale-work"));
 report("stale worker zero is explicitly initialized and never marked reconnected");
 for(int i=0;i<16;i++){
  struct trace old=legacy(i,true),now=legacy(i,false);assert(memcmp(&old,&now,sizeof(old))==0);
 }
 report("legacy differential: all sixteen new outcome scenarios preserve primary, OTG and hardware/schedule trace");
 printf("{\"passed\":true,\"cases\":%u,\"legacy_differential_scenarios\":16,\"PM_unwind_proved\":false}\n",cases);
 return 0;
}
