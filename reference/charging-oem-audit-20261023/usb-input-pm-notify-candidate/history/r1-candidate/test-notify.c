/* Actual driver functions; only OS/PSY/workqueue/I2C boundaries are models. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define to_delayed_work(w) container_of(w,struct delayed_work,work)
struct device { void *data; };
struct mutex { bool held; };
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; };
struct power_supply { struct device dev; void *data; };
union power_supply_propval { int intval; };
enum power_supply_property { POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT, OTHER };
enum samurai_usb_kind { SAMURAI_USB_UNKNOWN, SAMURAI_USB_SDP };
struct samurai_usb_budget { int online; enum samurai_usb_kind kind; int current_ua; };
struct samurai_usb_input {
 struct power_supply *psy; struct mutex lock; struct delayed_work work;
 struct samurai_usb_budget last; int last_error; bool last_valid,udc_valid,paused,pm_prepared,notify_pending;
 int udc_current_ua;
};
static struct samurai_usb_input input;
static struct power_supply supply;
static struct device dev;
static int changed,wakes,queued,cancelled,get_error;
static struct samurai_usb_budget observed_budget;
static void *system_wq=(void *)1;
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=true;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=false;}
static void *power_supply_get_drvdata(struct power_supply *p){return p->data;}
static void *dev_get_drvdata(struct device *p){return p->data;}
static void power_supply_changed(struct power_supply *p){assert(p==&supply&&input.lock.held);changed++;}
static void pm_wakeup_event(struct device *p,unsigned int ms){assert(p==&supply.dev&&ms==0&&input.lock.held);wakes++;}
static int mod_delayed_work(void *q,struct delayed_work *w,unsigned long delay){assert(q==system_wq&&w==&input.work&&delay==0);queued++;return 0;}
static int msecs_to_jiffies(int value){return value;}
static void schedule_delayed_work(struct delayed_work *w,int delay){assert(w==&input.work&&delay==1000);queued++;}
static void cancel_delayed_work_sync(struct delayed_work *w){assert(w==&input.work&&!input.lock.held&&input.paused&&!input.udc_valid);cancelled++;}
static int samurai_usb_get_budget(struct samurai_usb_input *p,struct samurai_usb_budget *budget){assert(p==&input);*budget=observed_budget;return get_error;}
typedef int irqreturn_t;
#define IRQ_HANDLED 1
#include "actual-functions.inc"

static void reset(void){memset(&input,0,sizeof(input));supply.data=&input;input.psy=&supply;dev.data=&input;changed=wakes=queued=cancelled=get_error=0;observed_budget=(struct samurai_usb_budget){1,SAMURAI_USB_SDP,500000};}
static int set(int value){union power_supply_propval v={value};return samurai_usb_set_property(&supply,POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT,&v);}
int main(void){
 /* 1: Existing runtime limits/validity and notification are preserved. */
 reset();assert(set(500000)==0&&input.udc_valid&&input.udc_current_ua==500000&&changed==1);
 assert(set(500001)==-ERANGE&&!input.udc_valid&&changed==2);
 assert(set(-1)==-ERANGE&&!input.udc_valid&&changed==3);
 union power_supply_propval v={0};assert(samurai_usb_set_property(&supply,OTHER,&v)==-EINVAL&&changed==3);
 /* 2: Actual PM budget revoke and poll publication defer, without fake power. */
 reset();assert(set(500000)==0);assert(samurai_usb_prepare(&dev)==0);assert(set(0)==0&&input.udc_current_ua==0&&input.udc_valid);
 assert(changed==1&&input.notify_pending&&wakes==0);
 observed_budget.current_ua=0;samurai_usb_poll(&input.work.work);assert(changed==1&&input.notify_pending&&wakes==0);
 /* 3: Existing suspend/paused errors and resume preserve fresh allowance. */
 assert(samurai_usb_suspend(&dev)==0&&cancelled==1&&input.paused&&!input.udc_valid);
 assert(set(500000)==-EBUSY&&changed==1&&wakes==0);
 assert(samurai_usb_resume(&dev)==0&&!input.paused&&!input.udc_valid);
 assert(set(500000)==0&&changed==1&&input.udc_valid);
 samurai_usb_complete(&dev);assert(!input.pm_prepared&&!input.notify_pending&&changed==2&&input.udc_valid&&input.udc_current_ua==500000);
 samurai_usb_complete(&dev);assert(changed==2);
 /* 4: Prepare-only abort changes no source budget or enable state. */
 reset();assert(set(500000)==0);assert(samurai_usb_prepare(&dev)==0);samurai_usb_complete(&dev);
 assert(changed==1&&input.udc_valid&&input.udc_current_ua==500000&&!input.paused);
 /* 5: Abort after revoke never resurrects the previous 500mA allowance. */
 reset();assert(set(500000)==0);assert(samurai_usb_prepare(&dev)==0);assert(set(0)==0);samurai_usb_complete(&dev);
 assert(input.udc_current_ua==0&&input.udc_valid&&changed==2);
 /* 6: Physical IRQ wake reporting remains independent of deferred software. */
 reset();assert(samurai_usb_prepare(&dev)==0);assert(samurai_usb_event(220,&input)==IRQ_HANDLED);
 assert(wakes==1&&queued==1&&changed==0);input.paused=true;
 assert(samurai_usb_event(221,&input)==IRQ_HANDLED&&wakes==2&&queued==1);
 samurai_usb_complete(&dev);input.paused=false;samurai_usb_event(220,&input);assert(wakes==2&&queued==2);
 /* 7: Probe-time unpublished paused supply is never dereferenced or queued. */
 reset();input.psy=NULL;input.paused=true;input.pm_prepared=true;
 samurai_usb_event(220,&input);assert(wakes==0&&queued==0);
 /* 8: Poll error defers, then complete publishes once; polling still reschedules. */
 reset();assert(samurai_usb_prepare(&dev)==0);get_error=-EAGAIN;samurai_usb_poll(&input.work.work);
 assert(changed==0&&input.notify_pending&&queued==1);samurai_usb_complete(&dev);assert(changed==1&&!input.pm_prepared);
 puts("8 notification/PM groups passed (actual functions, modeled OS boundaries)");return 0;
}
