/* Actual driver bodies; OF, driver-core/devres, PSY and workqueue APIs are fake. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define EPROBE_DEFER 517
#define GFP_KERNEL 0
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define DL_FLAG_STATELESS 1U
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define ERR_PTR(n) ((void *)(intptr_t)(n))
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
typedef unsigned int u32;
struct device_node { bool available; const char *compatible,*psy; int refs; struct platform_device *pdev; };
struct device { struct device *parent; struct device_node *of_node; void *data; bool registered; int refs; };
struct platform_device { struct device dev; };
struct mutex { bool held; };
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; };
struct power_supply { void *drv_data; };
struct power_supply_config { void *drv_data,*fwnode; };
union power_supply_propval { int intval; };
enum power_supply_property { POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT, POWER_SUPPLY_PROP_OTHER };
struct samurai_usb_input { struct device *native_consumer,*native_supplier; void *map;
 struct power_supply *psy; struct mutex lock; struct delayed_work work; bool paused,udc_valid; int udc_current_ua; };
struct dwc3 { struct work_struct vbus_draw_work; struct power_supply *usb_psy; struct device *dev; int current_limit; };
static void *system_wq=(void *)1;
static int samurai_usb_desc;
static struct device_node *legacy,*flat;
static struct samurai_usb_input *allocated;
static struct power_supply supply;
static bool machine_ok, parent_ok, base_ok, map_ok, alloc_ok, link_ok, publish_ok;
static bool require_link, native_retained;
static int add_action_fail, action_calls, published, link_adds, link_removes, remove_noops;
static int link_refs, queued, changed, cancels, retains, dwc_errors, setter_ret;
static char order[128]; static size_t order_len;
static struct { void (*fn)(void *); void *data; } actions[8]; static int action_count;
static void event(char c) { assert(order_len+1<sizeof(order));order[order_len++]=c;order[order_len]=0; }
static void mutex_init(struct mutex *m) { m->held=false; }
static void mutex_lock(struct mutex *m) { assert(!m->held);m->held=true; }
static void mutex_unlock(struct mutex *m) { assert(m->held);m->held=false; }
static void *power_supply_get_drvdata(struct power_supply *p) { return p->drv_data; }
static void power_supply_changed(struct power_supply *p) { assert(p==&supply);changed++; }
static void *dev_get_drvdata(struct device *d) { return d->data; }
static void platform_set_drvdata(struct platform_device *p,void *data) { p->dev.data=data; }
static int mod_delayed_work(void *q,struct delayed_work *w,unsigned long delay)
{ assert(q==system_wq&&allocated&&w==&allocated->work&&delay==0);queued++;return 0; }
static void schedule_delayed_work(struct delayed_work *w,unsigned long delay)
{ assert(allocated&&w==&allocated->work&&delay==0);queued++; }
static void cancel_delayed_work_sync(struct delayed_work *w)
{ assert(allocated&&w==&allocated->work&&!allocated->lock.held);assert(allocated->paused&&!allocated->udc_valid);cancels++;event('S'); }
#include "actual-pm-and-setter.inc"
static int power_supply_set_property(struct power_supply *p,enum power_supply_property prop,const union power_supply_propval *v)
{ setter_ret=samurai_usb_set_property(p,prop,v);return setter_ret; }
#define dev_dbg(dev,format,ret,current) do { (void)(dev);(void)(format);assert((ret)<0);(void)(current);dwc_errors++; } while(0)
#include "actual-dwc-vbus-work.inc"
static struct device_node *of_find_node_by_path(const char *path)
{ struct device_node *n;
 if(!strcmp(path,"/soc@0/usb@a6f8800/usb@a600000"))n=legacy;
 else {assert(!strcmp(path,"/soc@0/usb@a600000"));n=flat;}
 if(n){n->refs++;}return n; }
static bool of_device_is_available(struct device_node *n) { return n->available; }
static bool of_device_is_compatible(struct device_node *n,const char *s)
{ if(!strcmp(s,"qcom,pm8150b"))return parent_ok;return n&&n->compatible&&!strcmp(n->compatible,s); }
static int of_property_read_string(struct device_node *n,const char *key,const char **value)
{ assert(!strcmp(key,"usb-psy-name"));if(!n->psy)return -EINVAL;*value=n->psy;return 0; }
static void of_node_put(struct device_node *n) { if(n){assert(n->refs>0);n->refs--;} }
static struct platform_device *of_find_device_by_node(struct device_node *n)
{ if(n->pdev)n->pdev->dev.refs++;return n->pdev; }
static bool device_is_registered(struct device *d) { return d->registered; }
static void put_device(struct device *d) { assert(d->refs>0);d->refs--;event('P'); }
static void *device_link_add(struct device *consumer,struct device *supplier,unsigned int flags)
{ assert(consumer!=supplier&&consumer->refs>0&&flags==DL_FLAG_STATELESS);assert(!published);link_adds++;event('L');
 if(!link_ok){return NULL;}link_refs++;return (void *)0x1234; }
static void device_link_remove(void *consumer,struct device *supplier)
{ assert(consumer!=supplier&&((struct device *)consumer)->refs>0);link_removes++;event('U');
 if(link_refs)link_refs--;else remove_noops++; }
static int devm_add_action_or_reset(struct device *d,void (*fn)(void *),void *data)
{ assert(d);action_calls++;if(action_calls==add_action_fail){fn(data);return -ENOMEM;}
 assert(action_count<8);actions[action_count].fn=fn;actions[action_count++].data=data;return 0; }
static bool of_machine_is_compatible(const char *name) { assert(!strcmp(name,"realme,samurai"));return machine_ok; }
static bool of_node_name_eq(struct device_node *n,const char *name) { (void)n;assert(!strcmp(name,"pmic"));return parent_ok; }
static int of_property_read_u32(struct device_node *n,const char *key,unsigned int *value)
{ (void)n;assert(!strcmp(key,"reg"));*value=2;return parent_ok?0:-EINVAL; }
static int device_property_read_u32(struct device *d,const char *key,unsigned int *value)
{ (void)d;assert(!strcmp(key,"reg"));*value=base_ok?0x1300:0x1400;return 0; }
static void *devm_kzalloc(struct device *d,size_t bytes,int flags)
{ assert(d&&flags==GFP_KERNEL&&bytes==sizeof(*allocated));if(!alloc_ok)return NULL;
 allocated=calloc(1,bytes);assert(allocated);return allocated; }
static void *dev_get_regmap(struct device *d,void *name) { assert(d&&!name);return map_ok?(void *)2:NULL; }
static void samurai_usb_poll(struct work_struct *work) { (void)work;assert(!"not exercised in this delta"); }
#define INIT_DELAYED_WORK(w,fn) do { (void)(w);(void)(fn); } while(0)
static void *dev_fwnode(struct device *d) { return d->of_node; }
static void release_psy(void *unused) { (void)unused;assert(published==1);published=0;event('X'); }
static struct power_supply *devm_power_supply_register(struct device *d,int *desc,struct power_supply_config *config)
{ assert(d&&desc==&samurai_usb_desc&&config->drv_data==allocated);event('Y');
 if(require_link){assert(link_refs>0&&action_count==3&&allocated->native_consumer);}
 if(!publish_ok){return ERR_PTR(-EIO);}published++;supply.drv_data=allocated;
 assert(action_count<8);actions[action_count].fn=release_psy;actions[action_count++].data=NULL;return &supply; }
static void samurai_usb_retain_for_native_consumer(struct device *dev) { assert(dev);retains++; }
#define dev_info(dev,msg) do { assert(dev);(void)(msg); } while(0)
#define IRQF_ONESHOT 0x2000UL
#define IRQ_HANDLED 1
typedef int irqreturn_t;
static int irq_requests,irq_failed_at,irqs_released;
static irqreturn_t samurai_usb_event(int irq,void *data);
static int platform_get_irq_byname_optional(struct platform_device *p,const char *name)
{ assert(p);return !strcmp(name,"usbin-plugin")?7:9; }
static void release_irq(void *data)
{ int irq=(int)(intptr_t)data;assert(allocated->paused&&!published);
  unsigned int before=queued;assert(samurai_usb_event(irq,allocated)==IRQ_HANDLED);assert(before==(unsigned int)queued);
  irqs_released++;event(irq==7?'i':'j'); }
static int devm_request_threaded_irq(struct device *d,int irq,void *primary,
 irqreturn_t (*thread)(int,void *),unsigned long flags,const char *name,void *data)
{ assert(d&&!primary&&flags==IRQF_ONESHOT&&thread==samurai_usb_event&&data==allocated);
  assert(allocated->paused&&!published&&link_refs>0&&allocated->native_consumer);
  assert(!strcmp(name,irq==7?"usbin-plugin":"usbin-src-change"));irq_requests++;
  unsigned int before=queued;assert(thread(irq,data)==IRQ_HANDLED);assert(before==(unsigned int)queued);
  if(irq_requests==irq_failed_at)return -EIO;
  actions[action_count].fn=release_irq;actions[action_count++].data=(void *)(intptr_t)irq;
  event(irq==7?'A':'B');return 0; }
static int dev_err_probe(struct device *dev,int error,const char *msg)
{ assert(dev&&!strcmp(msg,"USB input events\n"));return error; }

#include "actual-link-irq-probe.inc"
static void cleanup(void)
{ while(action_count){--action_count;actions[action_count].fn(actions[action_count].data);}
 if(allocated){free(allocated);allocated=NULL;} }
static void reset(void)
{ cleanup();legacy=flat=NULL;machine_ok=parent_ok=base_ok=map_ok=alloc_ok=link_ok=publish_ok=true;
 irq_requests=irq_failed_at=irqs_released=0;require_link=native_retained=false;add_action_fail=action_calls=published=link_adds=link_removes=remove_noops=0;
 link_refs=queued=changed=cancels=retains=dwc_errors=setter_ret=0;order_len=0;order[0]=0;supply.drv_data=NULL; }
static void check_refs(struct device_node *a,struct device_node *b,struct platform_device *c)
{ assert(!a->refs&&!b->refs&&!c->dev.refs); }
int main(void)
{
 struct device_node parent_node={0},a,b;
 struct device parent={.of_node=&parent_node};
 struct platform_device p={.dev={.parent=&parent,.registered=true}},c={.dev={.registered=true}};
 unsigned int cases=0;
 /* These old functions are included as exact dependencies, not re-tested. */
 (void)&dwc3_vbus_draw_work;(void)&samurai_usb_suspend;(void)&samurai_usb_resume;
#define SETUP() do { reset();a=(struct device_node){true,"snps,dwc3","samurai-usb-input",0,&c};b=(struct device_node){0};legacy=&a;require_link=true;}while(0)
#define DONE() do { cleanup();check_refs(&a,&b,&c);assert(!link_refs);++cases;}while(0)
 SETUP();assert(!samurai_usb_probe(&p));assert(irq_requests==2&&published&&queued==1);
 assert(allocated->native_consumer==&c.dev&&c.dev.refs==1);DONE();
 assert(!strcmp(order,"LABYSXjiUP")&&irqs_released==2&&link_removes==1);
 SETUP();link_ok=false;assert(samurai_usb_probe(&p)==-EINVAL);assert(!irq_requests&&!published);DONE();
 assert(link_adds==1&&!link_removes);
 SETUP();add_action_fail=1;assert(samurai_usb_probe(&p)==-ENOMEM);assert(!irq_requests&&!published);DONE();
 assert(link_removes==1);
 SETUP();a.pdev=NULL;assert(samurai_usb_probe(&p)==-EPROBE_DEFER);assert(!irq_requests&&!published&&!link_adds);DONE();
 SETUP();irq_failed_at=1;assert(samurai_usb_probe(&p)==-EIO);assert(irq_requests==1&&!published&&!queued);DONE();
 assert(!irqs_released&&!strcmp(order,"LUP"));
 SETUP();irq_failed_at=2;assert(samurai_usb_probe(&p)==-EIO);assert(irq_requests==2&&!published&&!queued);DONE();
 assert(irqs_released==1&&!strcmp(order,"LAiUP"));
 SETUP();publish_ok=false;assert(samurai_usb_probe(&p)==-EIO);assert(irq_requests==2&&!published&&!queued);DONE();
 assert(irqs_released==2&&!strcmp(order,"LABYjiUP"));
 /* This preserves and labels the existing post-publication failure boundary. */
 SETUP();add_action_fail=2;assert(samurai_usb_probe(&p)==-ENOMEM);assert(published&&cancels==1&&!queued);
 DONE();assert(!strcmp(order,"LABYSXjiUP"));
 printf("{\"passed\":true,\"actual_function_cases\":%u,\"actual_merged_probe_and_irq_bodies\":true,\"OF_driver_core_devres_PSY_workqueue_faked\":true}\n",cases);
 return 0;
}
