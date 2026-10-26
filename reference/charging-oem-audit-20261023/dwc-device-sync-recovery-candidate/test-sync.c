/* Actual new driver functions and unchanged core PM callers. Hardware and
 * workqueue are fake OS boundaries; connection/IRQ exclusion uses pthreads. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef uint64_t u64;
typedef int pm_message_t;
enum { DWC3_ERR_NONE,DWC3_ERR_RECOVERY,DWC3_ERR_UNRECOVERABLE };
enum { DWC3_GCTL_PRTCAP_DEVICE=1,DWC3_GCTL_PRTCAP_HOST,DWC3_GCTL_PRTCAP_OTG };
enum { DWC3_OTG_ROLE_HOST=1,DWC3_OTG_ROLE_DEVICE };
#define DWC3_ERR_RECOVERY_MAX 3
#define PMSG_RESUME 1
#define PMSG_AUTO_RESUME 2
#define PMSG_IS_AUTO(m) ((m)==PMSG_AUTO_RESUME)
#define DWC3_GUSB2PHYCFG(n) (n)
#define DWC3_GUSB2PHYCFG_SUSPHY 1
#define DWC3_GUSB2PHYCFG_ENBLSLPM 2
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
struct mutex { pthread_mutex_t native; };
struct spinlock { pthread_mutex_t native; };
struct work_struct { int pending,running,queued,coalesced,runs;pthread_mutex_t lock; };
struct device { int rpm,pending_puts,irq_enables,pm_disabled,pm_enabled; };
struct dwc3 {
 struct device *dev;
 struct mutex connect_mutex;
 struct spinlock lock;
 struct work_struct err_recovery_work;
 int err_state;
 u32 err_recovery_count;
 u64 err_event_seq;
 int current_dr_role,current_otg_role,irq_gadget;
 bool softconnect,connected,needs_full_reinit,susphy_state,pending_events;
 void *gadget_driver;
 int num_usb2_ports,num_usb3_ports;
 bool dis_u2_susphy_quirk,dis_enblslpm_quirk;
 void *usb2_generic_phy[2],*usb3_generic_phy[2];
};
static struct dwc3 d;
static struct device dev;
static _Thread_local int connection_held,spin_held;
static int connects,disconnects,callbacks,irq_joins,core_inits,starts,event_setups,susphy_restores;
static int connect_ret[16],reset_ret[16],disconnect_ret[16];
static int irq_on_connect,irq_on_disconnect,irq_after_publish,irq_before_publish;
static bool powered,irq_disabled,disconnect_needs_irq;
static char last_log[1024];static int log_count;
static void dwc3_schedule_err_recovery(struct dwc3 *dwc);
static void inject_irq(void);
static void mutex_lock(struct mutex *m){assert(!connection_held);assert(!pthread_mutex_lock(&m->native));connection_held=1;}
static void mutex_unlock(struct mutex *m){assert(connection_held);connection_held=0;assert(!pthread_mutex_unlock(&m->native));}
static void lockdep_assert_held(struct mutex *m){assert(connection_held);}
static void spin_take(struct spinlock *s){assert(!spin_held);assert(!pthread_mutex_lock(&s->native));spin_held=1;}
static void spin_drop(struct spinlock *s)
{
 assert(spin_held);spin_held=0;assert(!pthread_mutex_unlock(&s->native));
 if(irq_after_publish&&(d.err_state==DWC3_ERR_NONE||d.err_state==DWC3_ERR_UNRECOVERABLE)){
  irq_after_publish=0;inject_irq();
 }
}
#define spin_lock_irqsave(p,f) do{(f)=0;spin_take(p);}while(0)
#define spin_unlock_irqrestore(p,f) do{(void)(f);spin_drop(p);}while(0)
/* Mirrors actual workqueue.c: queue_work_on uses PENDING; process_one_work
 * clears it before invoking the workfn, even while that fn waits on mutex. */
static bool schedule_work(struct work_struct *w)
{
 assert(!pthread_mutex_lock(&w->lock));bool fresh=!w->pending;
 if(fresh){w->pending=1;w->queued++;}else w->coalesced++;
 assert(!pthread_mutex_unlock(&w->lock));return fresh;
}
static void inject_irq(void)
{
 unsigned long flags;spin_lock_irqsave(&d.lock,flags);
 dwc3_schedule_err_recovery(&d);
 spin_unlock_irqrestore(&d.lock,flags);
}
static void dev_err(struct device *p,const char *fmt,...)
{va_list a;va_start(a,fmt);vsnprintf(last_log,sizeof(last_log),fmt,a);va_end(a);log_count++;}
static int dwc3_core_soft_reset(struct dwc3 *p){assert(powered);return reset_ret[connects++];}
static int dwc3_event_buffers_setup(struct dwc3 *p){event_setups++;return 0;}
static int __dwc3_gadget_start(struct dwc3 *p){starts++;return 0;}
static int dwc3_gadget_run_stop(struct dwc3 *p,int on)
{
 assert(on&&powered);int n=connects;
 if(irq_on_connect==n){irq_on_connect=0;inject_irq();}
 if(irq_before_publish==n){irq_before_publish=0;inject_irq();}
 return connect_ret[n-1];
}
static int dwc3_gadget_soft_disconnect(struct dwc3 *p)
{
 assert(powered&&connection_held&&!spin_held);disconnects++;
 if(irq_on_disconnect==disconnects){irq_on_disconnect=0;inject_irq();}
 if(disconnect_needs_irq&&irq_disabled)return -ETIMEDOUT;
 return disconnect_ret[disconnects-1];
}
static void dwc3_disconnect_gadget_sleepable(struct dwc3 *p)
{assert(connection_held&&!spin_held);callbacks++;}
static void synchronize_irq(int irq){assert(connection_held&&!spin_held);irq_joins++;}
static int dwc3_core_init_for_resume(struct dwc3 *p){core_inits++;powered=true;return 0;}
static void dwc3_set_prtcap(struct dwc3 *p,int role,bool keep){}
static bool device_may_wakeup(struct device *p){return false;}
static u32 dwc3_readl(struct dwc3 *p,u32 reg){return 0;}
static void dwc3_writel(struct dwc3 *p,u32 reg,u32 value){}
static void phy_pm_runtime_get_sync(void *p){}
static void dwc3_otg_init(struct dwc3 *p){}
static void dwc3_otg_host_init(struct dwc3 *p){}
static void dwc3_enable_susphy(struct dwc3 *p,bool on){susphy_restores++;}
static void pm_runtime_put(struct device *p){assert(p->rpm==1);p->pending_puts++;}
static void enable_irq(int irq){dev.irq_enables++;irq_disabled=false;}
static void pm_runtime_mark_last_busy(struct device *p){}
static void pinctrl_pm_select_default_state(struct device *p){}
static void pm_runtime_disable(struct device *p){p->pm_disabled++;}
static int pm_runtime_set_active(struct device *p){p->rpm=1;return 0;}
static void pm_runtime_set_suspended(struct device *p){p->rpm=0;}
static void pm_runtime_enable(struct device *p){p->pm_enabled++;}
#include "tested-functions.inc"
static bool initialized;
static void setup(void)
{
 if(initialized){pthread_mutex_destroy(&d.connect_mutex.native);pthread_mutex_destroy(&d.lock.native);pthread_mutex_destroy(&d.err_recovery_work.lock);}
 memset(&d,0,sizeof(d));memset(&dev,0,sizeof(dev));d.dev=&dev;
 assert(!pthread_mutex_init(&d.connect_mutex.native,NULL));assert(!pthread_mutex_init(&d.lock.native,NULL));assert(!pthread_mutex_init(&d.err_recovery_work.lock,NULL));initialized=true;
 d.current_dr_role=DWC3_GCTL_PRTCAP_DEVICE;d.gadget_driver=(void*)1;d.softconnect=true;d.irq_gadget=7;dev.rpm=1;
 connects=disconnects=callbacks=irq_joins=core_inits=starts=event_setups=susphy_restores=0;
 memset(connect_ret,0,sizeof(connect_ret));memset(reset_ret,0,sizeof(reset_ret));memset(disconnect_ret,0,sizeof(disconnect_ret));
 irq_on_connect=irq_on_disconnect=irq_after_publish=irq_before_publish=0;
 powered=true;irq_disabled=disconnect_needs_irq=false;last_log[0]=0;log_count=0;
 assert(!connection_held&&!spin_held);
}
static int resume_failed(void){connect_ret[0]=-ETIMEDOUT;return dwc3_gadget_resume(&d);}
static void begin_work(struct work_struct *w)
{assert(!pthread_mutex_lock(&w->lock));assert(w->pending&&!w->running);w->pending=0;w->running=1;w->runs++;assert(!pthread_mutex_unlock(&w->lock));}
static void finish_work(struct work_struct *w)
{assert(!pthread_mutex_lock(&w->lock));w->running=0;assert(!pthread_mutex_unlock(&w->lock));}
static void run_work(void)
{begin_work(&d.err_recovery_work);dwc3_err_recovery_work(&d.err_recovery_work);finish_work(&d.err_recovery_work);}
static int groups;
static void done(const char *s){groups++;printf("ok: %s\n",s);}
static void test_no_failure(void)
{
 setup();assert(!dwc3_gadget_resume(&d)&&connects==1&&!disconnects&&!log_count&&!d.err_event_seq);
 setup();d.gadget_driver=NULL;assert(!dwc3_gadget_resume(&d)&&!connects);
 setup();d.softconnect=false;assert(!dwc3_gadget_resume(&d)&&!connects);
 setup();d.current_dr_role=DWC3_GCTL_PRTCAP_OTG;assert(resume_failed()==-ETIMEDOUT&&connects==1&&!disconnects&&!log_count);
 done("normal/no-gadget/no-softconnect and OTG keep original first-call behavior");
}
static void test_primary_recovery(void)
{
 setup();assert(resume_failed()==-ETIMEDOUT&&connects==2&&disconnects==1&&callbacks==1&&irq_joins==1);
 assert(d.err_state==DWC3_ERR_NONE&&d.err_recovery_count==1&&!d.err_event_seq);
 assert(strstr(last_log,"primary=-110 recovery=0")&&strstr(last_log,"pending_at_publish=0"));
 setup();reset_ret[0]=-EIO;assert(dwc3_gadget_resume(&d)==-EIO&&connects==2&&d.err_state==DWC3_ERR_NONE);
 assert(strstr(last_log,"primary=-5 recovery=0"));
 done("primary reset/RUN_STOP errors retained separately from successful one-shot recovery");
}
static void test_failure_and_cap(void)
{
 setup();disconnect_ret[0]=-ETIMEDOUT;assert(resume_failed()==-ETIMEDOUT&&connects==1&&disconnects==1&&callbacks==1&&!irq_joins);
 assert(!d.err_recovery_count&&d.err_state==DWC3_ERR_UNRECOVERABLE&&strstr(last_log,"stage=disconnect"));
 setup();connect_ret[1]=-EIO;assert(resume_failed()==-ETIMEDOUT&&d.err_state==DWC3_ERR_UNRECOVERABLE&&d.err_recovery_count==1);
 assert(strstr(last_log,"recovery=-5 stage=connect"));
 setup();d.err_recovery_count=3;assert(resume_failed()==-ETIMEDOUT&&connects==1&&d.err_recovery_count==4);
 assert(d.err_state==DWC3_ERR_UNRECOVERABLE&&strstr(last_log,"count-limit(policy-EIO)"));
 done("disconnect failure stops before reconnect/count; connect error and MAX3 policy-EIO distinct");
}
static void test_old_unrecoverable(void)
{
 setup();d.err_state=DWC3_ERR_UNRECOVERABLE;d.err_recovery_count=2;
 assert(resume_failed()==-ETIMEDOUT&&connects==1&&!disconnects&&d.err_state==DWC3_ERR_UNRECOVERABLE&&d.err_recovery_count==2);
 assert(strstr(last_log,"existing-unrecoverable(policy-EIO)"));
 /* A truly new IRQ retains the original right to request another attempt. */
 inject_irq();assert(d.err_state==DWC3_ERR_RECOVERY&&d.err_event_seq==1);run_work();
 assert(d.err_state==DWC3_ERR_NONE&&d.err_recovery_count==3&&connects==2);
 done("new synchronous claim cannot revive old UNRECOVERABLE; real IRQ preserves original policy");
}
static void test_new_irq_during_connect(void)
{
 setup();irq_on_connect=2;assert(resume_failed()==-ETIMEDOUT);
 assert(d.err_event_seq==1&&d.err_state==DWC3_ERR_RECOVERY&&d.err_recovery_work.pending);
 assert(strstr(last_log,"recovery=0")&&strstr(last_log,"seq=0->1 pending_at_publish=1"));
 assert(d.err_recovery_work.coalesced>=1);run_work();
 assert(d.err_state==DWC3_ERR_NONE&&d.err_recovery_count==2&&!d.err_recovery_work.pending);
 done("new IRQ in actual soft_connect survives successful publication and coalesced queue");
}
static void test_publish_edges(void)
{
 setup();irq_before_publish=2;assert(resume_failed()==-ETIMEDOUT&&d.err_state==DWC3_ERR_RECOVERY);run_work();assert(d.err_state==DWC3_ERR_NONE);
 setup();irq_after_publish=1;assert(resume_failed()==-ETIMEDOUT&&d.err_event_seq==1&&d.err_state==DWC3_ERR_RECOVERY);
 /* The snapshot honestly says zero at its own publication; later IRQ owns
  * the newly queued state, not a fictitious earlier pending receipt. */
 assert(strstr(last_log,"pending_at_publish=0")&&d.err_recovery_work.pending);run_work();assert(d.err_state==DWC3_ERR_NONE);
 done("IRQ immediately before and after success publication has an execution opportunity");
}
static void test_new_irq_during_failure(void)
{
 setup();irq_on_disconnect=1;disconnect_ret[0]=-EIO;assert(resume_failed()==-ETIMEDOUT&&d.err_state==DWC3_ERR_RECOVERY&&!d.err_recovery_count);
 assert(strstr(last_log,"recovery=-5")&&strstr(last_log,"pending_at_publish=1"));run_work();assert(d.err_state==DWC3_ERR_NONE&&d.err_recovery_count==1);
 setup();irq_on_connect=2;connect_ret[1]=-EIO;assert(resume_failed()==-ETIMEDOUT&&d.err_state==DWC3_ERR_RECOVERY);run_work();assert(d.err_state==DWC3_ERR_NONE);
 done("failure publication also preserves true later IRQ instead of poisoning its queued work");
}
static void test_pending_old_worker(void)
{
 setup();inject_irq();assert(d.err_recovery_work.pending&&d.err_event_seq==1);
 assert(resume_failed()==-ETIMEDOUT&&d.err_state==DWC3_ERR_NONE);int old=disconnects;run_work();assert(disconnects==old&&!d.err_recovery_work.pending);
 setup();inject_irq();irq_on_connect=2;assert(resume_failed()==-ETIMEDOUT&&d.err_state==DWC3_ERR_RECOVERY&&d.err_event_seq==2);
 assert(d.err_recovery_work.coalesced>=2);run_work();assert(d.err_state==DWC3_ERR_NONE&&d.err_recovery_count==2);
 done("pending old worker skips only consumed generation; coalesced new generation still executes");
}
static pthread_mutex_t rendezvous=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition=PTHREAD_COND_INITIALIZER;
static bool worker_entered;
static void *blocked_worker(void *arg)
{
 begin_work(&d.err_recovery_work);
 pthread_mutex_lock(&rendezvous);worker_entered=true;pthread_cond_signal(&condition);pthread_mutex_unlock(&rendezvous);
 dwc3_err_recovery_work(&d.err_recovery_work);finish_work(&d.err_recovery_work);return NULL;
}
static void test_running_old_worker(void)
{
 setup();inject_irq();mutex_lock(&d.connect_mutex);
 pthread_t thread;worker_entered=false;assert(!pthread_create(&thread,NULL,blocked_worker,NULL));
 pthread_mutex_lock(&rendezvous);while(!worker_entered)pthread_cond_wait(&condition,&rendezvous);pthread_mutex_unlock(&rendezvous);
 /* Actual old worker is RUNNING and cannot enter the helper while this
  * thread holds connect_mutex; its PENDING bit has already been cleared. */
 assert(d.err_recovery_work.running&&!d.err_recovery_work.pending);
 struct dwc3_recovery_result result;irq_on_connect=1;
 assert(!dwc3_gadget_recover_locked(&d,true,&result)&&result.pending&&d.err_state==DWC3_ERR_RECOVERY);
 assert(d.err_recovery_work.pending);mutex_unlock(&d.connect_mutex);assert(!pthread_join(thread,NULL));
 assert(d.err_state==DWC3_ERR_NONE&&d.err_recovery_count==2);
 int old=disconnects;run_work();assert(disconnects==old); /* leftover queue is now stale */
 done("actual concurrently RUNNING old worker blocked on connect_mutex preserves and consumes new IRQ");
}
static void test_running_worker_requeue(void)
{
 setup();inject_irq();irq_on_connect=1;run_work();
 assert(d.err_state==DWC3_ERR_RECOVERY&&d.err_recovery_work.pending&&d.err_event_seq==2);
 run_work();assert(d.err_state==DWC3_ERR_NONE&&d.err_recovery_count==2);
 done("IRQ during actual running worker is requeued, not hidden by PENDING coalescing");
}
static void test_pm_tails(void)
{
 setup();powered=false;d.pending_events=true;irq_disabled=true;connect_ret[0]=-ETIMEDOUT;disconnect_needs_irq=true;
 assert(!dwc3_runtime_resume(&d));assert(powered&&core_inits==1&&d.err_state==DWC3_ERR_UNRECOVERABLE);
 assert(dev.pending_puts==1&&dev.irq_enables==1&&!d.pending_events&&!irq_disabled&&!susphy_restores);
 assert(strstr(last_log,"primary=-110 recovery=-110 stage=disconnect"));
 setup();powered=false;connect_ret[0]=-ETIMEDOUT;connect_ret[1]=-EIO;d.susphy_state=false;
 assert(!dwc3_pm_resume(&d)&&powered&&dev.rpm==1&&susphy_restores==1&&dev.pm_disabled==1&&dev.pm_enabled==1);
 assert(d.err_state==DWC3_ERR_UNRECOVERABLE&&!dev.pending_puts&&!dev.irq_enables);
 done("unchanged actual runtime/system callers retain powered success/SUSPHY/pending reference and IRQ tail");
}
int main(void)
{
 test_no_failure();test_primary_recovery();test_failure_and_cap();test_old_unrecoverable();test_new_irq_during_connect();
 test_publish_edges();test_new_irq_during_failure();test_pending_old_worker();test_running_old_worker();test_running_worker_requeue();test_pm_tails();
 assert(groups==11);printf("groups: %d\n",groups);return 0;
}
