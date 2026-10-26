/* Actual C callbacks; only device/IRQ/workqueue APIs are models. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define BIT(n) (1UL<<(n))
#define EPROBE_DEFER 517
#define IRQF_ONESHOT 1
#define IRQ_HANDLED 1
typedef int irqreturn_t;
struct device { void *data; bool wake; };
struct platform_device { struct device dev; };
struct mutex { bool held; };
struct delayed_work { int unused; };
struct power_supply { struct device dev; void *data; };
union power_supply_propval { int intval; };
enum power_supply_property { POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT, OTHER };
struct samurai_usb_input {
 struct device *event_dev;int event_irqs[2];unsigned long wake_armed;
 struct power_supply *psy;struct mutex lock;struct delayed_work work;
 bool paused,udc_valid,pm_prepared,notify_pending,last_valid;int udc_current_ua;
};
static struct samurai_usb_input input;
static struct platform_device pdev;
static struct power_supply supply;
static void *system_wq=(void *)1;
static int changed,queued,cancelled,warned,req_count,req_error_at,enable_error,disable_error;
static int irq_refs[224],ops[64][2],nops,mock_irqs[2];
static bool fire_probe_irq;
static irqreturn_t samurai_usb_event(int irq,void *data);
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=true;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=false;}
static void *dev_get_drvdata(struct device *dev){return dev->data;}
static void *platform_get_drvdata(struct platform_device *dev){return dev->dev.data;}
static void *power_supply_get_drvdata(struct power_supply *p){return p->data;}
static bool device_may_wakeup(struct device *dev){return dev->wake;}
static void power_supply_changed(struct power_supply *p){assert(p==&supply&&input.lock.held);changed++;}
static void cancel_delayed_work_sync(struct delayed_work *w){assert(w==&input.work&&input.paused&&!input.lock.held&&!input.udc_valid);cancelled++;}
static int mod_delayed_work(void *q,struct delayed_work *w,unsigned long delay){assert(q==system_wq&&w==&input.work&&delay==0&&!input.paused);queued++;return 0;}
static void dev_warn(struct device *dev,const char *fmt,...){assert(dev==&pdev.dev);warned++;}
static int enable_irq_wake(int irq){assert(irq==222||irq==223);assert(nops<64);ops[nops][0]=irq;ops[nops++][1]=1;if(irq==enable_error)return -EIO;assert(!irq_refs[irq]);irq_refs[irq]++;return 0;}
static int disable_irq_wake(int irq){assert(irq==222||irq==223);assert(nops<64);ops[nops][0]=irq;ops[nops++][1]=0;assert(irq_refs[irq]);if(irq==disable_error)return -EAGAIN;irq_refs[irq]--;return 0;}
static int platform_get_irq_byname_optional(struct platform_device *dev,const char *name){assert(dev==&pdev);if(!strcmp(name,"usbin-plugin"))return mock_irqs[0];assert(!strcmp(name,"usbin-src-change"));return mock_irqs[1];}
static int devm_request_threaded_irq(struct device *dev,int irq,void *top,irqreturn_t (*thread)(int,void *),unsigned long flags,const char *name,void *data){
 assert(dev==&pdev.dev&&top==NULL&&thread==samurai_usb_event&&flags==IRQF_ONESHOT&&data==&input);req_count++;
 if(req_count==req_error_at)return -EIO;
 if(fire_probe_irq)assert(thread(irq,data)==IRQ_HANDLED);
 return 0;
}
#include "actual-functions.inc"
static void reset(void){memset(&input,0,sizeof(input));memset(irq_refs,0,sizeof(irq_refs));memset(ops,0,sizeof(ops));supply.data=&input;supply.dev.wake=true;input.psy=&supply;input.event_dev=&pdev.dev;input.event_irqs[0]=222;input.event_irqs[1]=223;input.udc_valid=true;input.udc_current_ua=500000;pdev.dev.data=&input;changed=queued=cancelled=warned=req_count=req_error_at=enable_error=disable_error=nops=0;fire_probe_irq=false;mock_irqs[0]=222;mock_irqs[1]=223;}
static void cleared(void){assert(!input.wake_armed&&!irq_refs[222]&&!irq_refs[223]);}
int main(void){
 int groups=0;
 /* Native IRQ identities persist only after each successful request; probe
  * interrupts still cannot publish an absent supply or queue paused work. */
 reset();input.event_irqs[0]=input.event_irqs[1]=0;input.psy=NULL;input.paused=true;input.pm_prepared=true;fire_probe_irq=true;
 assert(samurai_usb_request_events(&pdev,&input)==0&&req_count==2&&input.event_irqs[0]==222&&input.event_irqs[1]==223&&!changed&&!queued);cleared();
 reset();input.event_irqs[0]=input.event_irqs[1]=0;input.psy=NULL;input.paused=true;req_error_at=2;
 assert(samurai_usb_request_events(&pdev,&input)==-EIO&&input.event_irqs[0]==222&&input.event_irqs[1]==0);samurai_usb_cleanup_wake(&input);cleared();groups++;
 /* Legacy no-resource platform never calls wake APIs. */
 reset();input.event_irqs[0]=input.event_irqs[1]=0;mock_irqs[0]=-ENXIO;mock_irqs[1]=-ENODEV;
 assert(samurai_usb_request_events(&pdev,&input)==0&&req_count==0);assert(samurai_usb_suspend(&pdev.dev)==0&&samurai_usb_resume(&pdev.dev)==0&&nops==0);cleared();groups++;
 /* Respect the existing PSY wake switch; ordinary polling restarts. */
 reset();supply.dev.wake=false;assert(samurai_usb_suspend(&pdev.dev)==0&&input.paused&&cancelled==1&&nops==0);assert(samurai_usb_resume(&pdev.dev)==0&&!input.paused&&queued==1);cleared();groups++;
 /* Two owned references balance in reverse order. */
 reset();assert(samurai_usb_suspend(&pdev.dev)==0&&input.paused&&input.wake_armed==3&&irq_refs[222]==1&&irq_refs[223]==1);
 assert(samurai_usb_resume(&pdev.dev)==0&&!input.paused&&!input.udc_valid&&queued==1);cleared();
 assert(nops==4&&ops[0][0]==222&&ops[0][1]==1&&ops[1][0]==223&&ops[1][1]==1&&ops[2][0]==223&&ops[2][1]==0&&ops[3][0]==222&&ops[3][1]==0);groups++;
 /* A failed first arm restarts the device: PM need not call its resume. */
 reset();enable_error=222;assert(samurai_usb_suspend(&pdev.dev)==-EIO&&!input.paused&&queued==1&&cancelled==1&&nops==1);cleared();groups++;
 /* A failed second arm unwinds the first, never the unowned second. */
 reset();enable_error=223;assert(samurai_usb_suspend(&pdev.dev)==-EIO&&!input.paused&&queued==1&&nops==3&&ops[2][0]==222&&ops[2][1]==0);cleared();groups++;
 /* Failed unwind keeps ownership, warns, and prevents a double arm. */
 reset();enable_error=223;disable_error=222;assert(samurai_usb_suspend(&pdev.dev)==-EIO&&input.wake_armed==1&&warned==1&&!input.paused);
 int count=nops;input.udc_valid=true;assert(samurai_usb_suspend(&pdev.dev)==-EAGAIN&&cancelled==1&&input.udc_valid&&nops==count+1&&ops[nops-1][1]==0);
 disable_error=0;samurai_usb_cleanup_wake(&input);cleared();groups++;
 /* Resume attempts all disarms even on failure, and restores runtime work.
  * The next suspend can arm only after the residual reference clears. */
 reset();assert(samurai_usb_suspend(&pdev.dev)==0);disable_error=223;
 assert(samurai_usb_resume(&pdev.dev)==-EAGAIN&&!input.paused&&queued==1&&input.wake_armed==2&&!irq_refs[222]&&irq_refs[223]==1);
 input.udc_valid=true;count=nops;assert(samurai_usb_suspend(&pdev.dev)==-EAGAIN&&nops==count+1&&cancelled==1&&input.udc_valid);
 disable_error=0;assert(samurai_usb_suspend(&pdev.dev)==0&&input.wake_armed==3&&cancelled==2);assert(samurai_usb_resume(&pdev.dev)==0);cleared();groups++;
 /* Existing notification deferral, real IRQ wake and fresh native500mA
  * coexist across the new PM callbacks; complete does not erase allowance. */
 reset();assert(samurai_usb_prepare(&pdev.dev)==0);samurai_usb_changed(&input);assert(input.notify_pending&&!changed);
 assert(samurai_usb_suspend(&pdev.dev)==0);assert(samurai_usb_event(222,&input)==IRQ_HANDLED&&changed==1&&!queued);
 assert(samurai_usb_resume(&pdev.dev)==0);union power_supply_propval value={500000};assert(samurai_usb_set_property(&supply,POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT,&value)==0&&input.udc_valid&&changed==1);
 samurai_usb_complete(&pdev.dev);assert(changed==2&&!input.pm_prepared&&!input.notify_pending&&input.udc_valid&&input.udc_current_ua==500000);cleared();groups++;
 /* Cleanup is independent of PSY lifetime; shutdown stops work and drops
  * only owned references, including a wake switch changed while asleep. */
 reset();assert(samurai_usb_suspend(&pdev.dev)==0);supply.dev.wake=false;input.psy=NULL;samurai_usb_shutdown(&pdev);assert(input.paused&&cancelled==2&&!warned);cleared();groups++;
 assert(groups==10);puts("10 IRQ-wake lifecycle groups passed (actual functions; modeled APIs)");return 0;
}
