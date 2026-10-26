#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint64_t u64;
typedef uint32_t u32;
typedef uint8_t u8;
#define IS_ENABLED(x) 1
#define EXPORT_SYMBOL_GPL(x)
#define GFP_KERNEL 0
#define NOTIFY_OK 0
#define PSY_EVENT_PROP_CHANGED 1
#define DWC3_GCTL_PRTCAP_DEVICE 2
#define READ_ONCE(x) (x)
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define kzalloc(s,f) calloc(1,s)
#define kfree(p) free(p)
#define msecs_to_jiffies(n) (n)
#define dev_err(...) ((void)0)
struct device {bool optin;int refs;bool suspended;};
struct phy {int unused;};
struct dwc3;
struct mutex {int held;};
typedef int spinlock_t;
#define DEFINE_MUTEX(n) struct mutex n
static void mutex_lock(struct mutex *m) {assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m) {assert(m->held);m->held=0;}
#define spin_lock_irqsave(l,f) do {(void)(l);(f)=0;} while(0)
#define spin_unlock_irqrestore(l,f) do {(void)(l);(void)(f);} while(0)
static void spin_lock_init(spinlock_t *s) {*s=0;}
struct work_struct {void (*fn)(struct work_struct *);};
struct delayed_work {struct work_struct work;bool pending;};
#define to_delayed_work(w) container_of(w,struct delayed_work,work)
#define INIT_DELAYED_WORK(w,f) do {(w)->work.fn=(f);(w)->pending=false;} while(0)
static int queue_count, join_count;
static void (*join_hook)(void);
static int system_wq;
static void mod_delayed_work(int q,struct delayed_work *w,unsigned long delay)
{queue_count++;w->pending=true;}
static void cancel_delayed_work_sync(struct delayed_work *w)
{join_count++;if(join_hook)join_hook();w->pending=false;}
struct notifier_block {int (*notifier_call)(struct notifier_block *,unsigned long,void *);};
struct power_supply_desc {const char *name;};
struct power_supply {const struct power_supply_desc *desc;};
static int notifier_count;
static int power_supply_reg_notifier(struct notifier_block *n) {notifier_count++;return 0;}
static void power_supply_unreg_notifier(struct notifier_block *n) {notifier_count--;}
static int device_property_read_bool(struct device *d,const char *p) {return d->optin;}
static u64 fake_ms=100;
static u64 ktime_get_boottime(void) {return fake_ms;}
static u64 ktime_to_ms(u64 n) {return n;}
static int pm_runtime_get_if_active(struct device *d) {if(d->suspended)return 0;d->refs++;return 1;}
static void pm_runtime_put(struct device *d) {assert(d->refs>0);d->refs--;}
static bool pm_runtime_suspended(struct device *d) {return d->suspended;}
static bool dev_pinctrl(struct device *d) {return false;}
/* ACTUAL_HEADERS */
/* ACTUAL_WINDOWS */
struct dwc3 {
 struct device *dev,*sysdev;struct phy *usb2_generic_phy[1];
 void *gadget_driver,*sys_wakeup,*ev_buf,*reset;unsigned int irq_gadget,max_cfg_eps;
 spinlock_t lock;struct dwc3_gadget_window detect_window;
 bool detect_system_blocked,detect_pm_busy;int current_dr_role;
};
struct usb_gadget {struct dwc3 *dwc;};
static struct dwc3 *gadget_to_dwc(struct usb_gadget *g) {return g->dwc;}
static char events[128];static size_t event_count;
static void mark(char c) {assert(event_count+1<sizeof(events));events[event_count++]=c;events[event_count]=0;}
static int enter_fail,restore_fail,write_count,read_count;
static bool cancel_after_eud;
static void fixture_abort_owner(void);
static int eud_com_quiet_begin_fake(struct eud_com_window_result *r)
{mark('E');r->cookie=11;r->software_quiet=true;if(cancel_after_eud)fixture_abort_owner();return enter_fail==1?-EIO:0;}
int eud_com_quiet_begin(struct eud_com_window_result *r) {return eud_com_quiet_begin_fake(r);}
int eud_com_quiet_cancel(u64 c,struct eud_com_window_result *r) {mark('c');return 0;}
int eud_com_quiet_end(u64 c,struct eud_com_window_result *r)
{mark('e');if(restore_fail==3)return -EIO;r->restored=true;return 0;}
int dwc3_gadget_window_begin(struct dwc3 *d,struct dwc3_gadget_window_result *r)
{mark('D');r->cookie=22;r->halted=enter_fail!=2;return enter_fail==2?-EIO:0;}
int dwc3_gadget_window_cancel(struct dwc3 *d,u64 c,struct dwc3_gadget_window_result *r)
{mark('x');r->cancelled=true;return restore_fail==2?-EIO:0;}
int dwc3_gadget_window_end(struct dwc3 *d,u64 c,struct dwc3_gadget_window_result *r)
{mark('d');return restore_fail==2?-EIO:0;}
int qcom_snps_hsphy_window_begin(struct phy *p,struct qcom_snps_hsphy_window_result *r)
{mark('P');r->cookie=33;r->high_z=enter_fail!=3;return enter_fail==3?-EIO:0;}
int qcom_snps_hsphy_window_end(struct phy *p,u64 c,struct qcom_snps_hsphy_window_result *r)
{mark('p');if(restore_fail==1)return -EIO;r->restored=true;return 0;}
static bool dwc3_gadget_window_busy(struct dwc3 *d) {return false;}
static void dwc3_gadget_window_shutdown(struct dwc3 *d) {mark('S');}
static void device_wakeup_disable(struct device *d) {}
static void free_irq(unsigned int irq,void *data) {mark('I');}
static void dwc3_event_buffers_cleanup(struct dwc3 *d) {mark('B');}
static void dwc3_phy_power_off(struct dwc3 *d) {mark('O');}
static void dwc3_phy_exit(struct dwc3 *d) {mark('F');}
static void dwc3_clk_disable(struct dwc3 *d) {mark('C');}
static void reset_control_assert(void *r) {mark('R');}
/* ACTUAL_OWNER */
static void fixture_abort_owner(void) {assert(bound_owner);bound_owner->abort=true;}
/* ACTUAL_LIFECYCLE */
static struct device device,provider;
static struct phy phy;
static struct dwc3 dwc;
static struct usb_gadget gadget;
static struct samurai_apsd_bus_sample next_sample;
static int read_error;
static int read_sample(void *ctx,struct samurai_apsd_bus_sample *s)
{assert(ctx==&provider);read_count++;if(read_error)return read_error;*s=next_sample;next_sample.serial++;return 0;}
static int rerun_once(void *ctx,u64 epoch) {assert(ctx==&provider);write_count++;return 0;}
static const struct samurai_apsd_bus_ops backend={read_sample,rerun_once};
static void reset(void)
{
 assert(!bound_owner);assert(!bus_dev);
 memset(&protocol_history,0,sizeof(protocol_history));memset(&device,0,sizeof(device));
 memset(&provider,0,sizeof(provider));memset(&dwc,0,sizeof(dwc));
 dwc.dev=dwc.sysdev=&device;dwc.usb2_generic_phy[0]=&phy;dwc.gadget_driver=&gadget;
 dwc.current_dr_role=DWC3_GCTL_PRTCAP_DEVICE;gadget.dwc=&dwc;
 event_count=0;events[0]=0;queue_count=join_count=notifier_count=0;
 enter_fail=restore_fail=write_count=read_count=read_error=0;cancel_after_eud=false;join_hook=NULL;
 next_sample=(struct samurai_apsd_bus_sample){.serial=1,.raw={1,1},.present=true};
}
static void bind(void) {device.optin=true;dwc3_apsd_owner_bind(&dwc);assert(bound_owner);}
static void bus(void) {assert(!samurai_apsd_bus_register(&provider,&backend,&provider));}
static void run(void) {assert(bound_owner);bound_owner->work.pending=false;owner_work(&bound_owner->work.work);}
static void cleanup(void)
{
 if(bound_owner && bound_owner->dwc) {dwc3_apsd_owner_stop_pre(&dwc);dwc3_gadget_window_shutdown(&dwc);dwc3_apsd_owner_stop_post(&dwc);dwc3_apsd_owner_unbind(&dwc);}
 samurai_apsd_bus_unregister(&provider,&provider);assert(!bound_owner);assert(!bus_dev);assert(!device.refs);
}
static void notify_during_join(void)
{
 struct power_supply_desc desc={"samurai-usb-input"};struct power_supply p={&desc};int n=queue_count;
 owner_notify(&bound_owner->notifier,PSY_EVENT_PROP_CHANGED,&p);assert(queue_count==n);
}
int main(void)
{
 reset();dwc3_apsd_owner_bind(&dwc);dwc3_core_exit(&dwc);assert(!bound_owner && !notifier_count);assert(!strcmp(events,"BOFCR"));puts("1 default property absent: no owner/notifier/MMIO additions");
 reset();bind();bus();run();assert(bound_owner->primary_error==-EOPNOTSUPP);assert(!event_count&&!write_count&&!bound_owner->once.attempted);assert(bound_owner->once.phase==SAMURAI_APSD_READY);cleanup();puts("2 real notifier worker + backend: missing PD/route/lifetime gate gives zero begin/write");
 reset();bind();bus();read_error=-EAGAIN;run();assert(!bound_owner->once.epoch);read_error=0;run();assert(bound_owner->once.phase==SAMURAI_APSD_READY&&!write_count);cleanup();puts("3 transient stable-read failure neither invents sample nor consumes attempt");
 reset();bind();bus();join_hook=notify_during_join;assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_RUNTIME));assert(!bound_owner->work.pending);assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));dwc3_apsd_owner_resume(&dwc,DWC3_APSD_RUNTIME);assert(bound_owner->blocked==DWC3_APSD_SYSTEM);dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);assert(!bound_owner->blocked&&bound_owner->work.pending);join_hook=NULL;cleanup();puts("4 pause fences late notifier before join; independent PM fences balance");
 reset();bind();bus();assert(samurai_apsd_bus_register(&provider,&backend,&provider)==-EBUSY);samurai_apsd_bus_unregister(&device,&provider);assert(bus_dev==&provider);samurai_apsd_bus_unregister(&provider,&provider);assert(!bound_owner->bus&&!bound_owner->work.pending);run();assert(!read_count);cleanup();puts("5 unregister exact identity + synchronous join before provider invalidation");
 for(int stage=1;stage<=3;stage++) {reset();bind();enter_fail=stage;assert(owner_enter_windows(bound_owner)==-EIO);assert(!owner_restore(bound_owner,false));assert(!device.refs);assert(!strcmp(events,stage==1?"Ee":stage==2?"EDde":"EDPpde"));cleanup();}puts("6 direct component entry failure receipts unwind in inverse order, partial cookies included");
 reset();bind();cancel_after_eud=true;assert(owner_enter_windows(bound_owner)==-ECANCELED);assert(!strcmp(events,"E"));assert(!owner_restore(bound_owner,false));cleanup();puts("7 cancellation between component calls prevents next begin");
 reset();bind();assert(!owner_enter_windows(bound_owner));event_count=0;events[0]=0;dwc3_gadget_stop(&gadget);assert(!strcmp(events,"pxSIe"));assert(!device.refs);assert(!bound_owner->dwc_window.cookie&&!bound_owner->eud.cookie);cleanup();puts("8 actual UDC stop: PHY restore, DWC cancel/shutdown/free_irq, EUD restore; no DWC reconnect");
 reset();bind();assert(!owner_enter_windows(bound_owner));restore_fail=1;assert(dwc3_apsd_owner_pause(&dwc,DWC3_APSD_RUNTIME)==-EIO);assert(bound_owner->quarantined&&bound_owner->phy.cookie&&bound_owner->dwc_window.cookie&&bound_owner->eud.cookie);assert(!strchr(events,'d')&&!strchr(events,'e'));restore_fail=0;assert(!owner_restore(bound_owner,false));bound_owner->quarantined=false;cleanup();puts("9 failed PHY restoration retains downstream quiet and reports error independently");
 reset();bind();bus();run();u64 epoch=bound_owner->once.epoch;bound_owner->once.attempted=1;bound_owner->once.phase=SAMURAI_APSD_WAIT_CLEAR;dwc3_gadget_stop(&gadget);dwc.gadget_driver=&gadget;dwc3_apsd_owner_resume(&dwc,DWC3_APSD_UDC);assert(bound_owner->once.epoch==epoch&&bound_owner->once.attempted);dwc3_apsd_owner_unbind(&dwc);bind();run();assert(bound_owner->once.epoch==epoch&&bound_owner->once.attempted&&!write_count);next_sample.present=false;run();assert(bound_owner->once.phase==SAMURAI_APSD_DETACHED);next_sample.present=true;run();assert(bound_owner->once.epoch==epoch+1&&!bound_owner->once.attempted);cleanup();puts("10 UDC stop/rebind never rearms; only fresh physical off/on starts new epoch");
 reset();bind();join_hook=notify_during_join;dwc3_core_exit(&dwc);join_hook=NULL;assert(join_count&&bound_owner->blocked==DWC3_APSD_CORE);assert(!strcmp(events,"BOFCR"));assert(!bound_owner->work.pending);cleanup();puts("11 actual core_exit joins/fences before event/PHY/clocks/reset teardown");
 reset();bind();assert(!dwc3_pm_prepare(&dwc));assert(bound_owner->blocked==DWC3_APSD_SYSTEM&&dwc.detect_system_blocked);dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);cleanup();puts("12 actual system prepare joins before its original DWC PM gate");
 reset();bind();assert(!owner_enter_windows(bound_owner));restore_fail=1;dwc3_apsd_owner_stop_pre(&dwc);dwc3_gadget_window_shutdown(&dwc);dwc3_apsd_owner_stop_post(&dwc);dwc3_apsd_owner_unbind(&dwc);assert(bound_owner&&bound_owner->quarantined&&!bound_owner->dwc&&!notifier_count);samurai_apsd_bus_unregister(&provider,&provider);assert(!bus_dev);assert(bound_owner->phy.cookie&&bound_owner->eud.cookie);assert(!strchr(events,'e'));device.optin=true;dwc3_apsd_owner_bind(&dwc);assert(!bound_owner->dwc);/* fixture-only disposal of intentional retained tombstone */free(bound_owner);bound_owner=NULL;device.refs=0;puts("13 teardown failure remains orphaned, never restored, no stale MMIO retry or rebind");
 return 0;
}
