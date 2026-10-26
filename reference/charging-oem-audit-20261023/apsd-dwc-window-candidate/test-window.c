/* Executes actual candidate functions with fake PM/MMIO/USB boundaries. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint64_t u64;
typedef uint32_t u32;
#define READ_ONCE(x) (x)
#define spin_lock_irqsave(l,f) do {(f)=0;assert(!*(l));++*(l);}while(0)
#define spin_unlock_irqrestore(l,f) do {(void)(f);assert(*(l)==1);--*(l);}while(0)
#define lockdep_assert_held(l) assert(*(l)==1)
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define DWC3_GCTL_PRTCAP_DEVICE 2
#define DWC3_GCTL_PRTCAP_HOST 1
#define DWC3_DSTS 0xc70
#define DWC3_DSTS_DEVCTRLHLT (1u<<22)
#define DWC3_GUCTL3 0xc60
#define DWC3_GUCTL3_SPLITDISABLE 1
#define DWC3_ERR_RECOVERY_MAX 3
#define DWC3_ERR_NONE 0
#define DWC3_ERR_UNRECOVERABLE 2
#define DWC3_BOUNCE_SIZE 64
#define IRQF_SHARED 1
#define dwc3_interrupt NULL
#define dwc3_thread_interrupt NULL
#define dev_err(...) ((void)0)
#define EXPORT_SYMBOL_GPL(x)
enum usb_dr_mode {USB_DR_MODE_UNKNOWN,USB_DR_MODE_HOST,USB_DR_MODE_PERIPHERAL,USB_DR_MODE_OTG};
#include "tested-types.inc"
struct work_struct {int value;};
struct usb_gadget;
struct fake_trb {u32 value;};
struct usb_gadget_driver {int value;};
struct dwc3 {struct dwc3_gadget_window detect_window;u64 detect_generation;
 bool detect_pm_busy,detect_system_blocked,detect_stopping;
 int lock,connect_mutex;unsigned int softconnect:1;bool pullups_connected;
 enum usb_dr_mode dr_mode;u32 current_dr_role;struct usb_gadget_driver *gadget_driver;
 void *dev,*sysdev,*ev_buf;int irq_gadget;bool sys_wakeup,dis_split_quirk;u32 max_cfg_eps;
 struct work_struct err_recovery_work;u32 err_recovery_count;int err_state;
 struct usb_gadget *gadget;void *bounce,*setup_buf;struct fake_trb *ep0_trb;uintptr_t bounce_addr,ep0_trb_addr;};
struct usb_gadget {struct dwc3 *owner;};
static struct dwc3 *gadget_to_dwc(struct usb_gadget *g){return g->owner;}
static struct dwc3 *current;
static int pm_refs,pm_get_result,pm_gets,pm_sync_gets,pm_put_idle,pm_put_auto,pm_puts,pm_barriers,irq_syncs;
static bool runtime_suspended,halted,lie_about_halt;
static int disconnects,connects,dis_error,connect_error,notifications,free_irqs;
static bool mutex_destroyed;
static int gadget_deletions;
static void (*get_hook)(void),(*connect_hook)(void),(*disconnect_hook)(void),(*mutex_hook)(void);
static void mutex_lock(int *m)
{assert(!mutex_destroyed);if(mutex_hook&&m==&current->connect_mutex){void(*h)(void)=mutex_hook;mutex_hook=NULL;h();}assert(!*m);++*m;}
static void mutex_unlock(int *m){assert(*m==1);--*m;}
static void mutex_destroy(int *m){assert(!*m&&gadget_deletions==1);mutex_destroyed=true;}
static int pm_runtime_get_if_active(void *dev)
{assert(!current->connect_mutex&&!current->lock);pm_gets++;if(get_hook){void(*h)(void)=get_hook;get_hook=NULL;h();}if(pm_get_result>0)pm_refs++;return pm_get_result;}
static int pm_runtime_get_sync(void *dev){assert(!current->connect_mutex&&!current->lock);pm_sync_gets++;pm_refs++;return 1;}
static void pm_runtime_put_noidle(void *dev){assert(pm_refs>0);pm_refs--;pm_put_idle++;}
static void pm_runtime_put_autosuspend(void *dev){assert(pm_refs>0&&!current->connect_mutex);pm_refs--;pm_put_auto++;}
static void pm_runtime_put(void *dev){assert(pm_refs>0);pm_refs--;pm_puts++;}
static void pm_runtime_mark_last_busy(void *dev){}
static bool pm_runtime_suspended(void *dev){return runtime_suspended;}
static void pm_runtime_set_suspended(void *dev){runtime_suspended=true;}
static void pm_runtime_barrier(void *dev){pm_barriers++;}
static bool dev_pinctrl(void *dev){return false;}
static void synchronize_irq(int irq){irq_syncs++;}
static u32 dwc3_readl(struct dwc3 *d,u32 reg){assert(pm_refs>0&&!runtime_suspended);return halted?DWC3_DSTS_DEVCTRLHLT:0;}
static void dwc3_writel(struct dwc3 *d,u32 reg,u32 value){assert(0&&"unexpected host PM MMIO");}
static int dwc3_gadget_soft_disconnect(struct dwc3 *d)
{assert(d->connect_mutex==1);disconnects++;if(!dis_error&&!lie_about_halt)halted=true;d->pullups_connected=false;if(disconnect_hook)disconnect_hook();return dis_error;}
static int dwc3_gadget_soft_connect(struct dwc3 *d)
{assert(d->connect_mutex==1);connects++;halted=false;d->pullups_connected=true;if(connect_hook)connect_hook();return connect_error;}
static void dwc3_disconnect_gadget_sleepable(struct dwc3 *d){notifications++;}
static int request_threaded_irq(int irq,void *a,void *b,int flags,const char *n,void *p){return 0;}
static void free_irq(int irq,void *p){assert(!pm_refs&&current->detect_stopping);free_irqs++;}
static void device_wakeup_enable(void *dev){}
static void device_wakeup_disable(void *dev){}
static void cancel_work_sync(struct work_struct *work){assert(current->detect_stopping&&gadget_deletions==1&&free_irqs==1);}
static void dwc3_enable_susphy(struct dwc3 *d,bool on){}
static void usb_del_gadget(struct usb_gadget *g);
static void dwc3_gadget_free_endpoints(struct dwc3 *d){}
static void usb_put_gadget(struct usb_gadget *g){}
static void dma_free_coherent(void *dev,size_t size,void *buffer,uintptr_t address){}
static void kfree(void *p){}
#include "tested-functions.inc"
static void usb_del_gadget(struct usb_gadget *g)
{assert(!mutex_destroyed);assert(dwc3_gadget_stop(g)==0);gadget_deletions++;}

static struct usb_gadget_driver driver;
static void setup(struct dwc3 *d)
{
 memset(d,0,sizeof(*d));current=d;d->dr_mode=USB_DR_MODE_PERIPHERAL;d->current_dr_role=DWC3_GCTL_PRTCAP_DEVICE;
 d->gadget_driver=&driver;d->softconnect=true;d->pullups_connected=true;
 pm_refs=pm_gets=pm_sync_gets=pm_put_idle=pm_put_auto=pm_puts=pm_barriers=irq_syncs=0;pm_get_result=1;
 runtime_suspended=halted=lie_about_halt=false;disconnects=connects=dis_error=connect_error=notifications=free_irqs=0;
 get_hook=connect_hook=disconnect_hook=mutex_hook=NULL;
 mutex_destroyed=false;gadget_deletions=0;
}
static struct dwc3_gadget_window_result begin(struct dwc3 *d)
{struct dwc3_gadget_window_result r;assert(dwc3_gadget_window_begin(d,&r)==0&&r.cookie&&r.halted&&pm_refs>=1);return r;}
static void done(const char *name){assert(!pm_refs&&!current->lock&&!current->connect_mutex);printf("ok: %s\n",name);}
static void test_no_resume_or_default_owner(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r;setup(&d);pm_get_result=0;
 assert(dwc3_gadget_window_begin(&d,&r)==-EAGAIN&&!r.cookie&&!disconnects&&!pm_sync_gets);
 pm_get_result=-EINVAL;assert(dwc3_gadget_window_begin(&d,&r)==-EINVAL&&!r.cookie);
 pm_get_result=1;d.gadget_driver=NULL;assert(dwc3_gadget_window_begin(&d,&r)==-ESHUTDOWN&&!pm_refs);
 d.gadget_driver=&driver;d.dr_mode=USB_DR_MODE_OTG;assert(dwc3_gadget_window_begin(&d,&r)==-EOPNOTSUPP&&!pm_refs);
 d.dr_mode=USB_DR_MODE_PERIPHERAL;d.err_state=DWC3_ERR_UNRECOVERABLE;
 assert(dwc3_gadget_window_begin(&d,&r)==-EIO&&!pm_refs&&!disconnects);
 done("active peripheral/bound owner only; no resume");
}
static void test_begin_end_and_cookie(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;setup(&d);r=begin(&d);
 assert(dwc3_gadget_window_begin(&d,&s)==-EBUSY&&pm_refs==1&&d.detect_window.cookie==r.cookie);
 assert(dwc3_gadget_window_end(&d,r.cookie+1,&s)==-ESTALE&&pm_refs==1);
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==0&&s.state==DWC3_WINDOW_IDLE&&!s.halted&&connects==1);
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==-ESTALE);
 done("claim, HALT, stale/duplicate and restore receipt");
}
static void test_halt_failure_retains_claim(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;setup(&d);dis_error=-ETIMEDOUT;
 assert(dwc3_gadget_window_begin(&d,&r)==-ETIMEDOUT&&r.cookie&&!r.halted&&r.halt_error==-ETIMEDOUT&&pm_refs==1);
 dis_error=0;assert(dwc3_gadget_window_cancel(&d,r.cookie,&s)==0&&s.cancelled&&s.halted&&pm_refs==1);
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==0);
 done("HALT error stays owned; explicit cancel/end");
}
static void test_no_false_halt_from_zero_disconnect(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r;setup(&d);lie_about_halt=true;
 assert(dwc3_gadget_window_begin(&d,&r)==-EIO&&r.cookie&&!r.halted&&pm_refs==1);
 lie_about_halt=false;dwc3_gadget_window_shutdown(&d);done("zero return without DEVCTRLHLT rejected");
}
static void test_intent_only_pullup_and_no_reconnect_cancel(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;struct usb_gadget g={&d};setup(&d);r=begin(&d);
 int old=disconnects;assert(dwc3_gadget_pullup(&g,0)==0&&!d.softconnect&&disconnects==old&&!pm_sync_gets);
 assert(dwc3_gadget_window_cancel(&d,r.cookie,&s)==0&&pm_refs==1&&!connects);
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==0&&s.halted&&!s.restore_wanted&&!connects);
 done("pullup defers latest intent; cancel never reconnects");
}
static void test_restore_failure_keeps_parked_and_retry(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;setup(&d);r=begin(&d);connect_error=-EIO;
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==-EIO&&s.restore_error==-EIO&&s.halted&&pm_refs==1&&halted);
 connect_error=0;assert(dwc3_gadget_window_end(&d,r.cookie,&s)==0&&!pm_refs);
 done("restore error parked; explicit retry keeps cookie");
}
static void test_restore_and_park_errors_independent(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;setup(&d);r=begin(&d);connect_error=-EIO;dis_error=-ETIMEDOUT;
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==-EIO&&s.restore_error==-EIO&&s.halt_error==-ETIMEDOUT&&!s.halted&&pm_refs==1);
 dis_error=0;dwc3_gadget_window_shutdown(&d);done("restore failure does not hide failed park");
}
static void to_off(void){struct usb_gadget g={current};connect_hook=NULL;assert(dwc3_gadget_pullup(&g,0)==0);}
static void toggle(void){struct usb_gadget g={current};assert(dwc3_gadget_pullup(&g,!current->softconnect)==0);}
static void test_restore_intent_race(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;setup(&d);r=begin(&d);connect_hook=to_off;
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==0&&s.halted&&!s.restore_wanted&&pm_refs==0);
 done("pullup during restore cannot take connect_mutex");
}
static void test_continuous_intent_race_is_bounded(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;setup(&d);r=begin(&d);connect_hook=toggle;disconnect_hook=toggle;
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==-EAGAIN&&s.restore_error==-EAGAIN&&s.halted&&pm_refs==1);
 connect_hook=disconnect_hook=NULL;dwc3_gadget_window_shutdown(&d);done("continuous pullup race parks after two attempts");
}
static void test_error_recovery_deferred(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;setup(&d);r=begin(&d);int old=disconnects;
 dwc3_err_recovery_work(&d.err_recovery_work);
 assert(d.detect_window.recovery_pending&&disconnects==old&&!connects);
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==0&&!d.detect_window.recovery_pending&&notifications==1&&d.err_recovery_count==1);
 done("error work defers and end reuses real recovery helper");
}
static void prepare_race(void){assert(dwc3_pm_prepare(current)==0);}
static void test_pm_prepare_and_transition_gates(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;setup(&d);
 assert(dwc3_gadget_window_pm_enter(&d)==0&&d.detect_pm_busy);
 assert(dwc3_gadget_window_begin(&d,&r)==-EBUSY&&!pm_refs);dwc3_gadget_window_pm_exit(&d);
 get_hook=prepare_race;assert(dwc3_gadget_window_begin(&d,&r)==-EBUSY&&!pm_refs&&d.detect_system_blocked);
 dwc3_pm_complete(&d);r=begin(&d);
 assert(dwc3_gadget_window_pm_enter(&d)==-EBUSY&&!d.detect_pm_busy);
 assert(dwc3_pm_prepare(&d)==-EBUSY&&!d.detect_system_blocked);
 assert(dwc3_gadget_suspend(&d)==-EBUSY&&dwc3_gadget_resume(&d)==-EBUSY);
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==0);done("runtime/system PM atomic gate excludes window");
}
static struct dwc3_gadget_window_result raced;
static void begin_race(void){raced=begin(current);}
static void shutdown_race(void){dwc3_gadget_window_shutdown(current);}
static void test_pullup_rechecks_after_pm(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result s;struct usb_gadget g={&d};setup(&d);
 d.softconnect=false;d.pullups_connected=false;mutex_hook=begin_race;
 assert(dwc3_gadget_pullup(&g,1)==0&&d.detect_window.state==DWC3_WINDOW_HALTED&&pm_refs==1&&!connects);
 assert(dwc3_gadget_window_end(&d,raced.cookie,&s)==0);done("claim between pullup PM and mutex is rechecked");
}
static void test_shutdown_unbind_rebind(void)
{
 struct dwc3 d;struct dwc3_gadget_window_result r,s;struct usb_gadget g={&d};setup(&d);r=begin(&d);
 assert(dwc3_gadget_stop(&g)==0&&!pm_refs&&free_irqs==1&&d.detect_window.state==DWC3_WINDOW_SHUTDOWN);
 assert(dwc3_gadget_window_end(&d,r.cookie,&s)==-ESTALE&&dwc3_gadget_pullup(&g,1)==-ESHUTDOWN);
 dwc3_err_recovery_work(&d.err_recovery_work);assert(dwc3_gadget_window_pm_enter(&d)==0);dwc3_gadget_window_pm_exit(&d);
 assert(dwc3_gadget_start(&g,&driver)==0&&!d.detect_stopping);d.softconnect=true;r=begin(&d);
 assert(r.cookie>1);dwc3_gadget_window_shutdown(&d);dwc3_gadget_window_shutdown(&d);
 setup(&d);mutex_hook=shutdown_race;
 assert(dwc3_gadget_window_begin(&d,&s)==-ESHUTDOWN&&s.state==DWC3_WINDOW_SHUTDOWN&&s.cancelled&&!pm_refs);
 assert(!dwc3_gadget_window_busy(&d)&&dwc3_gadget_window_end(&d,s.cookie,&r)==-ESTALE);
 setup(&d);d.gadget=&g;r=begin(&d);dwc3_gadget_exit(&d);
 assert(mutex_destroyed&&gadget_deletions==1&&!pm_refs&&free_irqs==1);
 done("UDC/remove shutdown wins claim race, joins stop before mutex destroy");
}
int main(void)
{
 setbuf(stdout,NULL);
 test_no_resume_or_default_owner();test_begin_end_and_cookie();test_halt_failure_retains_claim();
 test_no_false_halt_from_zero_disconnect();test_intent_only_pullup_and_no_reconnect_cancel();
 test_restore_failure_keeps_parked_and_retry();test_restore_and_park_errors_independent();
 test_restore_intent_race();test_continuous_intent_race_is_bounded();test_error_recovery_deferred();test_pm_prepare_and_transition_gates();
 test_pullup_rechecks_after_pm();test_shutdown_unbind_rebind();
 return 0;
}
