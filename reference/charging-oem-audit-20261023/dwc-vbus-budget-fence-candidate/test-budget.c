/* Actual fixed/candidate C functions. Hardware, PSY discovery and queue APIs fake;
 * the running work and its cancel/join use real pthreads and condition variables.
 */
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define DWC3_CURRENT_UNSPECIFIED UINT_MAX
#define DWC3_GCTL_PRTCAP_DEVICE 2
#define DWC3_GCTL_PRTCAP_HOST 1
#define PMSG_SUSPEND 1
#define PMSG_RESUME 2
#define NOTIFY_DONE 0
#define NOTIFY_OK 1
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
typedef unsigned int u32;
struct mutex { pthread_mutex_t native; };
struct spinlock { pthread_mutex_t native; };
struct device { void *data; };
struct work_struct { void (*callback)(struct work_struct *); bool initialized,pending; };
struct delayed_work { struct work_struct work; };
struct power_supply_desc { const char *name; };
struct power_supply { struct power_supply_desc *desc; void *drv_data; int refs; };
struct notifier_block { int (*notifier_call)(struct notifier_block *,unsigned long,void *); };
struct usb_gadget { struct dwc3 *dwc; };
struct dwc3 { struct device *dev; struct spinlock lock; struct power_supply *usb_psy;
 const char *usb_psy_name; struct notifier_block psy_nb; struct work_struct vbus_draw_work;
 unsigned int current_limit; bool vbus_draw_blocked; void *usb2_phy; int current_dr_role; };
struct samurai_usb_input { struct mutex lock; struct delayed_work work; bool udc_valid,paused; int udc_current_ua; };
enum power_supply_property { POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT };
union power_supply_propval { int intval; };
static struct samurai_usb_input input={.lock={PTHREAD_MUTEX_INITIALIZER}};
static struct power_supply_desc desc={"samurai-usb-input"};
static struct power_supply supply={.desc=&desc,.drv_data=&input};
static struct device provider_dev={.data=&input};
static struct dwc3 *active;
static struct usb_gadget gadget;
static void *system_wq=(void *)1;
static int queue_calls,cancel_calls,set_calls,revoke_errno,warn_errno,positive_calls;
static int suspend_ret,resume_ret,set_active_ret,suspend_calls,resume_calls;
static int runtime_disable_calls,runtime_enable_calls,set_suspended_calls,sleep_pin_calls,default_pin_calls;
static int property_ret,notifier_ret,phy_calls,phy_ret,put_calls,provider_changes;
static bool discovered,disconnect_on_suspend,draw_on_resume;
static bool spin_initialized;
static pthread_t worker_thread;
static bool worker_live;
static pthread_mutex_t block_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t block_cond=PTHREAD_COND_INITIALIZER;
static bool block_positive,setter_entered,setter_release;
static atomic_int join_entered,join_completed,pm_done;
static int pm_rc;
static void mutex_lock(struct mutex *m) { assert(!pthread_mutex_lock(&m->native)); }
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->native)); }
#define spin_lock_irqsave(lock,flags) do { (flags)=0;assert(!pthread_mutex_lock(&(lock)->native)); } while(0)
#define spin_unlock_irqrestore(lock,flags) do { (void)(flags);assert(!pthread_mutex_unlock(&(lock)->native)); } while(0)
static void *power_supply_get_drvdata(struct power_supply *p) { return p->drv_data; }
static void power_supply_changed(struct power_supply *p) { assert(p==&supply);provider_changes++; }
static void *dev_get_drvdata(struct device *d) { return d->data; }
static void cancel_delayed_work_sync(struct delayed_work *w)
{ assert(w==&input.work);assert(!pthread_mutex_trylock(&input.lock.native));pthread_mutex_unlock(&input.lock.native); }
static int mod_delayed_work(void *q,struct delayed_work *w,unsigned long delay)
{ assert(q==system_wq&&w==&input.work&&!delay);return 0; }
#include "actual-provider.inc"
static int power_supply_set_property(struct power_supply *p,enum power_supply_property prop,const union power_supply_propval *v)
{
 assert(p==&supply&&prop==POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT);
 assert(!pthread_mutex_trylock(&active->lock.native));pthread_mutex_unlock(&active->lock.native);
 if(v->intval==500000) {
  assert(!pthread_mutex_lock(&block_lock));
  if(block_positive) {
   setter_entered=true;pthread_cond_broadcast(&block_cond);
   while(!setter_release)assert(!pthread_cond_wait(&block_cond,&block_lock));
  }
  assert(!pthread_mutex_unlock(&block_lock));
 }
 set_calls++;if(v->intval>0)positive_calls++;
 if(!v->intval&&revoke_errno)return revoke_errno;
 return samurai_usb_set_property(p,prop,v);
}
#define dev_dbg(dev,...) do { (void)(dev); } while(0)
#define dev_warn(dev,format,ret) do { (void)(dev);(void)(format);warn_errno=(ret); } while(0)
static int schedule_work(struct work_struct *work)
{ assert(work->initialized);work->pending=true;queue_calls++;return 1; }
#define INIT_WORK(work,cb) do { (work)->callback=(cb);(work)->initialized=true; } while(0)
static void cancel_work_sync(struct work_struct *work)
{
 assert(work==&active->vbus_draw_work&&work->initialized);
 assert(!pthread_mutex_trylock(&active->lock.native));pthread_mutex_unlock(&active->lock.native);
 cancel_calls++;atomic_store(&join_entered,1);
 assert(!pthread_mutex_lock(&block_lock));pthread_cond_broadcast(&block_cond);pthread_mutex_unlock(&block_lock);
 if(worker_live){assert(!pthread_join(worker_thread,NULL));worker_live=false;}
 work->pending=false;atomic_store(&join_completed,1);
}
static int device_property_read_string(struct device *d,const char *key,const char **name)
{ assert(d==active->dev&&!strcmp(key,"usb-psy-name"));if(property_ret){return property_ret;}*name=desc.name;return 0; }
static int power_supply_reg_notifier(struct notifier_block *nb) { assert(nb==&active->psy_nb);return notifier_ret; }
static void power_supply_unreg_notifier(struct notifier_block *nb) { assert(nb==&active->psy_nb); }
static struct power_supply *power_supply_get_by_name(const char *name)
{ assert(!strcmp(name,desc.name));if(!discovered){return NULL;}supply.refs++;return &supply; }
static void power_supply_put(struct power_supply *p) { assert(p==&supply&&p->refs>0);p->refs--;put_calls++; }
#define dev_err(dev,...) do { (void)(dev); } while(0)
static int dwc3_gadget_vbus_draw(struct usb_gadget *,unsigned int);
static int dwc3_suspend_common(struct dwc3 *d,int msg)
{ assert(d==active&&msg==PMSG_SUSPEND);suspend_calls++;if(!suspend_ret&&disconnect_on_suspend)assert(!dwc3_gadget_vbus_draw(&gadget,0));return suspend_ret; }
static int dwc3_resume_common(struct dwc3 *d,int msg)
{ assert(d==active&&msg==PMSG_RESUME);resume_calls++;if(draw_on_resume){assert(!dwc3_gadget_vbus_draw(&gadget,500));d->vbus_draw_work.callback(&d->vbus_draw_work);}return resume_ret; }
static void pinctrl_pm_select_sleep_state(struct device *d) { assert(d==active->dev);sleep_pin_calls++; }
static void pinctrl_pm_select_default_state(struct device *d) { assert(d==active->dev);default_pin_calls++; }
static void pm_runtime_disable(struct device *d) { assert(d==active->dev);runtime_disable_calls++; }
static void pm_runtime_enable(struct device *d) { assert(d==active->dev);runtime_enable_calls++; }
static int pm_runtime_set_active(struct device *d) { assert(d==active->dev);return set_active_ret; }
static void pm_runtime_set_suspended(struct device *d) { assert(d==active->dev);set_suspended_calls++; }
#include "actual-budget-core.inc"
static struct dwc3 *gadget_to_dwc(struct usb_gadget *g) { return g->dwc; }
static int usb_phy_set_power(void *phy,unsigned int mA) { assert(phy==(void *)5&&mA<=500);phy_calls++;return phy_ret; }
#include "actual-budget-gadget.inc"
#include "actual-old-worker.inc"
#include "actual-old-pm.inc"
static void reset(struct dwc3 *d,struct device *dev)
{
 assert(!worker_live);
 if(spin_initialized)assert(!pthread_mutex_destroy(&d->lock.native));
 memset(d,0,sizeof(*d));assert(!pthread_mutex_init(&d->lock.native,NULL));spin_initialized=true;
 active=d;d->dev=dev;dev->data=d;gadget.dwc=d;d->current_dr_role=DWC3_GCTL_PRTCAP_DEVICE;
 queue_calls=cancel_calls=set_calls=revoke_errno=warn_errno=positive_calls=0;
 suspend_ret=resume_ret=set_active_ret=suspend_calls=resume_calls=0;
 runtime_disable_calls=runtime_enable_calls=set_suspended_calls=sleep_pin_calls=default_pin_calls=0;
 property_ret=notifier_ret=phy_calls=phy_ret=put_calls=provider_changes=0;
 discovered=true;disconnect_on_suspend=draw_on_resume=false;
 block_positive=setter_entered=setter_release=false;
 atomic_store(&join_entered,0);atomic_store(&join_completed,0);atomic_store(&pm_done,0);
 input.paused=input.udc_valid=false;input.udc_current_ua=0;supply.refs=0;
}
static void bound(struct dwc3 *d,struct device *dev) { reset(d,dev);dwc3_get_usb_power_supply(d);assert(d->usb_psy==&supply&&supply.refs==1&&d->vbus_draw_work.initialized); }
static void *worker_new(void *unused) { (void)unused;dwc3_vbus_draw_work(&active->vbus_draw_work);return NULL; }
static void *worker_old(void *unused) { (void)unused;old_dwc3_vbus_draw_work(&active->vbus_draw_work);return NULL; }
static void start_blocked(bool old)
{
 block_positive=true;assert(!pthread_create(&worker_thread,NULL,old?worker_old:worker_new,NULL));worker_live=true;
 assert(!pthread_mutex_lock(&block_lock));while(!setter_entered)assert(!pthread_cond_wait(&block_cond,&block_lock));pthread_mutex_unlock(&block_lock);
}
static void release_setter(void)
{ assert(!pthread_mutex_lock(&block_lock));setter_release=true;pthread_cond_broadcast(&block_cond);pthread_mutex_unlock(&block_lock); }
static void *suspend_thread(void *unused) { (void)unused;pm_rc=dwc3_pm_suspend(active);atomic_store(&pm_done,1);return NULL; }
int main(void)
{
 struct dwc3 d={0};struct device dev={0};pthread_t pm_thread;unsigned int cases=0;
#define CASE() (++cases)
 /* Old actual worker and PM: disconnect0 cannot revoke a captured local500. */
 bound(&d,&dev);assert(!dwc3_gadget_vbus_draw(&gadget,500));start_blocked(true);
 disconnect_on_suspend=true;assert(!old_dwc3_pm_suspend(&d));assert(d.current_limit==0&&!cancel_calls);
 assert(!samurai_usb_suspend(&provider_dev));assert(!samurai_usb_resume(&provider_dev));assert(!old_dwc3_pm_resume(&d));assert(!input.udc_valid);
 release_setter();assert(!pthread_join(worker_thread,NULL));worker_live=false;
 assert(input.udc_valid&&input.udc_current_ua==500000); /* No new positive native event. */
 dwc3_vbus_draw_work(&d.vbus_draw_work);assert(input.udc_current_ua==0);CASE();
 /* New actual suspend cannot return while captured500 is blocked in setter. */
 bound(&d,&dev);assert(!dwc3_gadget_vbus_draw(&gadget,500));start_blocked(false);
 disconnect_on_suspend=true;assert(!pthread_create(&pm_thread,NULL,suspend_thread,NULL));
 assert(!pthread_mutex_lock(&block_lock));while(!atomic_load(&join_entered))assert(!pthread_cond_wait(&block_cond,&block_lock));pthread_mutex_unlock(&block_lock);
 assert(!atomic_load(&join_completed)&&!atomic_load(&pm_done));
 assert(d.vbus_draw_blocked&&d.current_limit==DWC3_CURRENT_UNSPECIFIED);
 release_setter();assert(!pthread_join(pm_thread,NULL));assert(pm_rc==0&&atomic_load(&pm_done)&&atomic_load(&join_completed));
 assert(input.udc_valid&&input.udc_current_ua==0&&!worker_live);
 assert(!samurai_usb_suspend(&provider_dev));assert(!samurai_usb_resume(&provider_dev));assert(!dwc3_pm_resume(&d));
 assert(!input.udc_valid&&d.current_limit==DWC3_CURRENT_UNSPECIFIED&&!d.vbus_draw_blocked);CASE();
 bound(&d,&dev);d.current_limit=500;suspend_ret=-EAGAIN;assert(dwc3_pm_suspend(&d)==-EAGAIN);
 assert(!d.vbus_draw_blocked&&d.current_limit==500&&!cancel_calls&&!set_calls&&!sleep_pin_calls);CASE();
 bound(&d,&dev);d.current_limit=500;revoke_errno=-EIO;assert(!dwc3_pm_suspend(&d));
 assert(d.vbus_draw_blocked&&warn_errno==-EIO&&cancel_calls==1&&sleep_pin_calls==1);CASE();
 bound(&d,&dev);assert(!dwc3_pm_suspend(&d));int q=queue_calls;
 assert(dwc3_gadget_vbus_draw(&gadget,500)==-EBUSY&&queue_calls==q&&d.current_limit==DWC3_CURRENT_UNSPECIFIED);CASE();
 bound(&d,&dev);d.current_limit=DWC3_CURRENT_UNSPECIFIED;dwc3_vbus_draw_work(&d.vbus_draw_work);assert(!set_calls);CASE();
 bound(&d,&dev);d.current_limit=500;d.vbus_draw_blocked=true;dwc3_vbus_draw_work(&d.vbus_draw_work);assert(!set_calls);CASE();
 bound(&d,&dev);assert(!dwc3_pm_suspend(&d));int s=set_calls;q=queue_calls;assert(!dwc3_pm_resume(&d));
 assert(!d.vbus_draw_blocked&&d.current_limit==DWC3_CURRENT_UNSPECIFIED&&set_calls==s&&queue_calls==q);
 assert(runtime_disable_calls==1&&runtime_enable_calls==1&&!set_suspended_calls);CASE();
 assert(!dwc3_gadget_vbus_draw(&gadget,100));dwc3_vbus_draw_work(&d.vbus_draw_work);
 assert(input.udc_valid&&input.udc_current_ua==100000);CASE();
 bound(&d,&dev);assert(!dwc3_pm_suspend(&d));set_active_ret=-EINVAL;revoke_errno=-ENODATA;
 assert(dwc3_pm_resume(&d)==-EINVAL);assert(d.vbus_draw_blocked&&d.current_limit==DWC3_CURRENT_UNSPECIFIED);
 assert(!resume_calls&&runtime_enable_calls==1&&warn_errno==-ENODATA);CASE();
 bound(&d,&dev);assert(!dwc3_pm_suspend(&d));resume_ret=-ETIMEDOUT;draw_on_resume=true;
 assert(dwc3_pm_resume(&d)==-ETIMEDOUT);assert(positive_calls==1&&input.udc_current_ua==0);
 assert(d.vbus_draw_blocked&&d.current_limit==DWC3_CURRENT_UNSPECIFIED&&set_suspended_calls==1&&runtime_enable_calls==1);CASE();
 bound(&d,&dev);assert(!dwc3_pm_suspend(&d));resume_ret=-EIO;draw_on_resume=true;revoke_errno=-EBUSY;
 assert(dwc3_pm_resume(&d)==-EIO&&warn_errno==-EBUSY&&d.vbus_draw_blocked&&runtime_enable_calls==1);CASE();
 /* Late discovery while closed is not a replay; initial provider is invalid. */
 reset(&d,&dev);discovered=false;dwc3_get_usb_power_supply(&d);assert(!d.usb_psy&&d.psy_nb.notifier_call);
 assert(!dwc3_gadget_vbus_draw(&gadget,500));assert(d.current_limit==500&&!queue_calls);
 assert(!dwc3_pm_suspend(&d));discovered=true;
 assert(dwc3_psy_notifier(&d.psy_nb,0,&supply)==NOTIFY_OK);
 assert(d.usb_psy==&supply&&!queue_calls&&!set_calls&&!input.udc_valid);
 assert(!dwc3_pm_resume(&d));assert(!queue_calls&&!set_calls&&d.current_limit==DWC3_CURRENT_UNSPECIFIED);CASE();
 assert(!dwc3_gadget_vbus_draw(&gadget,500));dwc3_vbus_draw_work(&d.vbus_draw_work);
 assert(input.udc_valid&&input.udc_current_ua==500000);CASE();
 reset(&d,&dev);discovered=false;dwc3_get_usb_power_supply(&d);assert(!dwc3_pm_suspend(&d));
 assert(dwc3_gadget_vbus_draw(&gadget,500)==-EBUSY&&d.current_limit==DWC3_CURRENT_UNSPECIFIED&&!queue_calls);CASE();
 reset(&d,&dev);property_ret=-EINVAL;dwc3_get_usb_power_supply(&d);assert(!d.vbus_draw_work.initialized&&!d.usb_psy_name);
 assert(!dwc3_pm_suspend(&d)&&!dwc3_pm_resume(&d));assert(!cancel_calls&&!set_calls);CASE();
 reset(&d,&dev);notifier_ret=-EIO;dwc3_get_usb_power_supply(&d);assert(d.vbus_draw_work.initialized&&!d.usb_psy&&!d.psy_nb.notifier_call);
 assert(!dwc3_pm_suspend(&d));assert(cancel_calls==1&&!set_calls);
 assert(dwc3_gadget_vbus_draw(&gadget,100)==-EBUSY);assert(!dwc3_pm_resume(&d));assert(dwc3_gadget_vbus_draw(&gadget,100)==-EOPNOTSUPP);CASE();
 bound(&d,&dev);d.usb2_phy=(void *)5;d.vbus_draw_blocked=true;phy_ret=-ERANGE;
 assert(dwc3_gadget_vbus_draw(&gadget,100)==-ERANGE&&phy_calls==1&&!queue_calls);
 assert(!dwc3_pm_suspend(&d)&&!dwc3_pm_resume(&d));assert(!cancel_calls&&!set_calls);CASE();
 bound(&d,&dev);d.current_dr_role=DWC3_GCTL_PRTCAP_HOST;assert(!dwc3_pm_suspend(&d)&&!dwc3_pm_resume(&d));
 assert(!cancel_calls&&!set_calls&&!d.vbus_draw_blocked);CASE();
 /* The actual worker's debug report and retry policy preserve a setter error. */
 bound(&d,&dev);input.paused=true;assert(!dwc3_gadget_vbus_draw(&gadget,500));dwc3_vbus_draw_work(&d.vbus_draw_work);
 assert(!input.udc_valid&&set_calls==1&&queue_calls==1);CASE();
 assert(!worker_live);assert(!pthread_mutex_destroy(&d.lock.native));
 printf("{\"passed\":true,\"actual_function_cases\":%u,\"real_pthread_block_and_cancel_join\":true,\"old_transient_reauthorization_reproduced\":true,\"new_join_before_provider_resume\":true}\n",cases);
 return 0;
}
