/* Exact production functions; IRQ/work/PM/MMIO/UDC boundaries are fake.
 * One pthread case executes real fixture mutex/condition joins, not the Linux
 * workqueue implementation. No physical HALT or complete PM lifetime proof. */
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32;
typedef uint64_t u64;
#define DWC3_ERR_NONE 0
#define DWC3_ERR_RECOVERY 1
#define DWC3_ERR_UNRECOVERABLE 2
#define DWC3_ERR_RECOVERY_MAX 3
#define DWC3_BOUNCE_SIZE 64
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
struct fake_mutex { pthread_mutex_t real; bool alive; };
struct device { int refs; };
struct work_struct { bool pending; };
struct dwc3;
struct usb_gadget { struct dwc3 *dwc; };
struct dwc3 {
 struct device *dev,*sysdev;
 struct usb_gadget *gadget;
 void *gadget_driver,*ev_buf,*bounce,*setup_buf,*ep0_trb;
 unsigned long bounce_addr,ep0_trb_addr;
 pthread_mutex_t lock;
 struct fake_mutex connect_mutex;
 struct work_struct err_recovery_work;
 bool recovery_stopping,sys_wakeup,softconnect,pullups_connected;
 int irq_gadget,max_cfg_eps,err_state;
 u32 err_recovery_count;
 u64 err_event_seq;
};
struct fixture {
 atomic_int order,queues,cancels,joins,disconnects,connects,late_mutex,
  after_release,free_irqs,usb_del_calls,mutex_destroys,pm_gets,pm_puts;
 atomic_int free_irq_order,destroy_order,cancel_done_order,usb_del_order;
 bool resources_freed,irq_registered,run_worker,disconnect_blocked,
  allow_disconnect,exit_waiting,inject_at_susphy,inject_at_usb_del,
  inject_at_connect;
 int stop_error,connect_error;
 void (*schedule)(struct dwc3 *);
};
static struct fixture f;
static struct dwc3 d;
static struct device dev;
static struct usb_gadget gadget;
static pthread_mutex_t ctl = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed = PTHREAD_COND_INITIALIZER;
static _Thread_local int spin_depth,connect_depth;
static unsigned cases;
static void dwc3_schedule_err_recovery(struct dwc3 *p);
static int dwc3_gadget_stop(struct usb_gadget *g);
static int dwc3_gadget_pullup(struct usb_gadget *g,int on);
static void dwc3_err_recovery_work(struct work_struct *work);
static void previous_dwc3_err_recovery_work(struct work_struct *work);
static int stamp(void) { return atomic_fetch_add(&f.order,1)+1; }
static void take(pthread_mutex_t *p) {
 assert(!spin_depth);assert(!pthread_mutex_lock(p));spin_depth++;
}
static void drop(pthread_mutex_t *p) {
 assert(spin_depth==1);spin_depth--;assert(!pthread_mutex_unlock(p));
}
#define spin_lock_irqsave(p,flags) do { (flags)=0;take(p); } while(0)
#define spin_unlock_irqrestore(p,flags) do { (void)(flags);drop(p); } while(0)
static void mutex_lock(struct fake_mutex *p) {
 assert(!spin_depth&&!connect_depth);
 if (!p->alive) atomic_fetch_add(&f.late_mutex,1);
 else assert(!pthread_mutex_lock(&p->real));
 connect_depth++;
}
static void mutex_unlock(struct fake_mutex *p) {
 assert(connect_depth==1&&!spin_depth);connect_depth--;
 if (p->alive) assert(!pthread_mutex_unlock(&p->real));
}
static void mutex_destroy(struct fake_mutex *p) {
 assert(!spin_depth&&!connect_depth&&p->alive);
 assert(!pthread_mutex_destroy(&p->real));p->alive=false;
 atomic_fetch_add(&f.mutex_destroys,1);atomic_store(&f.destroy_order,stamp());
}
static void lockdep_assert_held(struct fake_mutex *p) {
 (void)p;assert(connect_depth==1);
}
static struct dwc3 *gadget_to_dwc(struct usb_gadget *g) { return g->dwc; }
static bool pm_runtime_suspended(struct device *p) { (void)p;return false; }
static void pm_runtime_barrier(struct device *p) { (void)p;assert(!connect_depth); }
static int pm_runtime_get_sync(struct device *p) {
 assert(!connect_depth);p->refs++;atomic_fetch_add(&f.pm_gets,1);return 1;
}
static void pm_runtime_put(struct device *p) {
 assert(p->refs>0);p->refs--;atomic_fetch_add(&f.pm_puts,1);
}
static void pm_runtime_set_suspended(struct device *p) { (void)p;abort(); }
static void dev_err(struct device *p,const char *fmt,...) { (void)p;(void)fmt; }
static void device_wakeup_disable(struct device *p) { (void)p; }
static void synchronize_irq(int irq) { (void)irq;atomic_fetch_add(&f.joins,1); }
static bool schedule_work(struct work_struct *work) {
 assert(spin_depth==1); /* Both candidate producers now linearize here. */
 assert(!pthread_mutex_lock(&ctl));work->pending=true;
 atomic_fetch_add(&f.queues,1);pthread_cond_broadcast(&changed);
 assert(!pthread_mutex_unlock(&ctl));return true;
}
static void inject_irq(void) {
 assert(f.irq_registered);take(&d.lock);f.schedule(&d);drop(&d.lock);
}
static int dwc3_gadget_soft_disconnect(struct dwc3 *p) {
 assert(connect_depth==1);atomic_fetch_add(&f.disconnects,1);
 if (f.resources_freed) atomic_fetch_add(&f.after_release,1);
 assert(!pthread_mutex_lock(&ctl));
 if (f.run_worker) {
  f.disconnect_blocked=true;pthread_cond_broadcast(&changed);
  while (!f.allow_disconnect) assert(!pthread_cond_wait(&changed,&ctl));
 }
 assert(!pthread_mutex_unlock(&ctl));
 p->pullups_connected=false;return f.stop_error;
}
static int dwc3_gadget_soft_connect(struct dwc3 *p) {
 assert(connect_depth==1);atomic_fetch_add(&f.connects,1);
 if (f.resources_freed) atomic_fetch_add(&f.after_release,1);
 if (f.inject_at_connect) { f.inject_at_connect=false;inject_irq(); }
 p->pullups_connected=!f.connect_error;return f.connect_error;
}
static void dwc3_disconnect_gadget_sleepable(struct dwc3 *p) { (void)p; }
static void cancel_work_sync(struct work_struct *work) {
 assert(!spin_depth&&!connect_depth);atomic_fetch_add(&f.cancels,1);
 assert(!pthread_mutex_lock(&ctl));work->pending=false;
 if (f.run_worker) {
  f.exit_waiting=true;pthread_cond_broadcast(&changed);
  while (f.run_worker) assert(!pthread_cond_wait(&changed,&ctl));
 }
 work->pending=false;assert(!pthread_mutex_unlock(&ctl));
 atomic_store(&f.cancel_done_order,stamp());
}
static void dwc3_enable_susphy(struct dwc3 *p,bool enable) {
 (void)p;(void)enable;
 if (f.inject_at_susphy) { f.inject_at_susphy=false;inject_irq(); }
}
static void free_irq(int irq,void *evt) {
 (void)irq;(void)evt;assert(f.irq_registered);
 f.irq_registered=false;atomic_fetch_add(&f.free_irqs,1);
 atomic_store(&f.free_irq_order,stamp());
}
static void usb_del_gadget(struct usb_gadget *g) {
 /* Mirrors actual UDC unbind's pullup(0) -> udc_stop/free_irq boundaries.
  * Driver unbind/UDC callbacks and MMIO are fake, not a UDC-core test. */
 atomic_fetch_add(&f.usb_del_calls,1);atomic_store(&f.usb_del_order,stamp());
 if (f.inject_at_usb_del) { f.inject_at_usb_del=false;inject_irq(); }
 assert(dwc3_gadget_pullup(g,0)==0);
 assert(dwc3_gadget_stop(g)==0);
}
static void dwc3_gadget_free_endpoints(struct dwc3 *p) {
 (void)p;assert(!f.irq_registered);f.resources_freed=true;
}
static void usb_put_gadget(struct usb_gadget *g) { (void)g; }
static void dma_free_coherent(struct device *p,size_t bytes,void *ptr,unsigned long dma) {
 (void)p;(void)bytes;(void)ptr;(void)dma;
}
static void kfree(void *p) { (void)p; }
#include "actual-functions.inc"
/* Only the original producer/worker/exit control is renamed. Its original
 * pending publication calls schedule_work without the spinlock: permit that
 * in the fake boundary while retaining candidate assertions elsewhere. */
static bool previous_schedule_work(struct work_struct *work) {
 assert(!pthread_mutex_lock(&ctl));work->pending=true;
 atomic_fetch_add(&f.queues,1);assert(!pthread_mutex_unlock(&ctl));return true;
}
#define schedule_work previous_schedule_work
#include "previous-functions.inc"
#undef schedule_work

static void setup(void) {
 f=(struct fixture){0};d=(struct dwc3){0};dev=(struct device){0};
 gadget=(struct usb_gadget){.dwc=&d};
 assert(!pthread_mutex_init(&d.lock,NULL));
 assert(!pthread_mutex_init(&d.connect_mutex.real,NULL));d.connect_mutex.alive=true;
 d.dev=&dev;d.sysdev=&dev;d.gadget=&gadget;d.gadget_driver=&gadget;
 d.irq_gadget=7;d.softconnect=true;d.pullups_connected=true;
 f.irq_registered=true;f.schedule=dwc3_schedule_err_recovery;
}
static void cleanup(void) {
 assert(!f.run_worker&&!spin_depth&&!connect_depth);
 if (d.connect_mutex.alive) assert(!pthread_mutex_destroy(&d.connect_mutex.real));
 assert(!pthread_mutex_destroy(&d.lock));
}
static void *worker_thread(void *arg) {
 (void)arg;dwc3_err_recovery_work(&d.err_recovery_work);
 assert(!pthread_mutex_lock(&ctl));f.run_worker=false;
 pthread_cond_broadcast(&changed);assert(!pthread_mutex_unlock(&ctl));return NULL;
}
static void *exit_thread(void *arg) { (void)arg;dwc3_gadget_exit(&d);return NULL; }
int main(void) {
 /* A source-control counterexample, not a safety pass or measured UAF. */
 setup();f.schedule=previous_dwc3_schedule_err_recovery;f.inject_at_susphy=true;
 previous_dwc3_gadget_exit(&d);
 assert(d.err_recovery_work.pending&&f.resources_freed&&atomic_load(&f.late_mutex)==1);
 previous_dwc3_err_recovery_work(&d.err_recovery_work);
 assert(atomic_load(&f.late_mutex)==2&&atomic_load(&f.after_release)>0);
 assert(atomic_load(&f.destroy_order)<atomic_load(&f.free_irq_order));cases++;cleanup();
 puts("old-control: late IRQ queues after cancel; unbind and old work use retired fixture mutex/resources");

 setup();f.inject_at_susphy=true;f.inject_at_usb_del=true;
 dwc3_gadget_exit(&d);
 assert(d.recovery_stopping&&d.err_event_seq==2&&atomic_load(&f.queues)==0);
 assert(!d.err_recovery_work.pending&&atomic_load(&f.late_mutex)==0);
 assert(atomic_load(&f.cancel_done_order)<atomic_load(&f.usb_del_order));
 assert(atomic_load(&f.free_irq_order)<atomic_load(&f.destroy_order));
 assert(atomic_load(&f.disconnects)==1&&atomic_load(&f.free_irqs)==1);
 assert(atomic_load(&f.pm_gets)==1&&atomic_load(&f.pm_puts)==1);cases++;cleanup();
 puts("exit: IRQ enqueue excluded through original pullup-off, free_irq, then mutex destroy");

 setup();inject_irq();assert(d.err_recovery_work.pending);
 dwc3_gadget_exit(&d);
 assert(!d.err_recovery_work.pending&&atomic_load(&f.queues)==1);
 assert(atomic_load(&f.late_mutex)==0&&atomic_load(&f.free_irqs)==1);cases++;cleanup();
 puts("exit: pre-existing queued work canceled before UDC unbind");

 setup();d.recovery_stopping=true;d.err_state=DWC3_ERR_RECOVERY;d.err_event_seq=9;
 struct dwc3_recovery_result r={0};mutex_lock(&d.connect_mutex);
 assert(dwc3_gadget_recover_locked(&d,false,&r)==-ESHUTDOWN);
 mutex_unlock(&d.connect_mutex);
 assert(!strcmp(r.stage,"gadget-exit")&&r.start_seq==9&&r.end_seq==9);
 assert(!r.pending&&!r.reconnected&&atomic_load(&f.disconnects)==0&&atomic_load(&f.connects)==0);
 dwc3_err_recovery_work(&d.err_recovery_work);
 assert(atomic_load(&f.disconnects)==0&&atomic_load(&f.queues)==0);cases++;cleanup();
 puts("closed entry: initialized ESHUTDOWN receipt and old worker performs no recovery I/O boundary");

 setup();f.run_worker=true;d.err_state=DWC3_ERR_RECOVERY;
 pthread_t worker,exiter;assert(!pthread_create(&worker,NULL,worker_thread,NULL));
 assert(!pthread_mutex_lock(&ctl));
 while (!f.disconnect_blocked) assert(!pthread_cond_wait(&changed,&ctl));
 assert(!pthread_mutex_unlock(&ctl));assert(!pthread_create(&exiter,NULL,exit_thread,NULL));
 assert(!pthread_mutex_lock(&ctl));
 while (!f.exit_waiting) assert(!pthread_cond_wait(&changed,&ctl));
 assert(!pthread_mutex_unlock(&ctl));
 assert(atomic_load(&f.usb_del_calls)==0&&atomic_load(&f.mutex_destroys)==0);
 take(&d.lock);assert(d.recovery_stopping);drop(&d.lock);
 inject_irq();assert(atomic_load(&f.queues)==0);
 assert(!pthread_mutex_lock(&ctl));f.allow_disconnect=true;
 pthread_cond_broadcast(&changed);assert(!pthread_mutex_unlock(&ctl));
 assert(!pthread_join(worker,NULL));assert(!pthread_join(exiter,NULL));
 assert(!d.err_recovery_work.pending&&atomic_load(&f.queues)==0);
 assert(atomic_load(&f.late_mutex)==0&&atomic_load(&f.after_release)==0);
 assert(atomic_load(&f.connects)==1&&d.err_event_seq==1&&d.err_state==DWC3_ERR_RECOVERY);
 assert(atomic_load(&f.free_irq_order)<atomic_load(&f.destroy_order));cases++;cleanup();
 puts("pthread join: running recovery completes before unbind; late generation retained, no pending requeue");

 setup();f.inject_at_connect=true;d.err_state=DWC3_ERR_RECOVERY;
 mutex_lock(&d.connect_mutex);assert(dwc3_gadget_recover_locked(&d,false,&r)==0);
 mutex_unlock(&d.connect_mutex);
 assert(r.reconnected&&r.pending&&r.end_seq==r.start_seq+1);
 assert(atomic_load(&f.queues)==2&&d.err_recovery_work.pending);
 assert(d.err_state==DWC3_ERR_RECOVERY);cases++;cleanup();
 puts("open gate: original IRQ and pending publication retain execution opportunity and outcome");

 setup();d.err_state=DWC3_ERR_UNRECOVERABLE;
 mutex_lock(&d.connect_mutex);assert(dwc3_gadget_recover_locked(&d,true,&r)==-EIO);
 mutex_unlock(&d.connect_mutex);
 assert(!strcmp(r.stage,"existing-unrecoverable(policy-EIO)")&&atomic_load(&f.disconnects)==0);
 assert(!r.pending&&!r.reconnected&&atomic_load(&f.queues)==0);cases++;cleanup();
 puts("open gate: old unrecoverable policy unchanged, no synthetic recovery");

 setup();d.gadget=NULL;dwc3_gadget_exit(&d);
 assert(!d.recovery_stopping&&atomic_load(&f.cancels)==0&&atomic_load(&f.mutex_destroys)==0);
 assert(atomic_load(&f.free_irqs)==0);cases++;cleanup();
 puts("null gadget: original no-op retained");
 printf("{\"passed\":true,\"cases\":%u,\"old_late_enqueue_reproduced\":true,"
        "\"running_worker_joined_before_unbind\":true,\"mutex_outlives_free_irq\":true,"
        "\"full_resume_abort_proved\":false}\n",cases);
 return 0;
}
