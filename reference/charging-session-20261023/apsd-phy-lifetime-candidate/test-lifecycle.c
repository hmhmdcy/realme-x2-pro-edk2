/* Actual candidate functions; pthread completion/mutex, fake devres/MMIO/PM.
 * Old owner_join is a declared boundary; new owner callbacks and krefs are real.
 */
#define _GNU_SOURCE
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
#include <time.h>
#include <unistd.h>
#define __iomem
#define __maybe_unused
#define BIT(n) (1U<<(n))
#define GENMASK(h,l) (((~0U)<<(l))&((~0U)>>(31-(h))))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define READ_ONCE(x) __atomic_load_n(&(x),__ATOMIC_RELAXED)
#define WRITE_ONCE(x,v) __atomic_store_n(&(x),(v),__ATOMIC_RELAXED)
#define U64_MAX UINT64_MAX
#define ERR_PTR(e) ((void*)(intptr_t)(e))
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p)>(uintptr_t)-4096)
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define dev_dbg(...) ((void)0)
#define dev_vdbg(...) ((void)0)
#define dev_warn(...) ((void)0)
#define dev_err(...) ((void)0)
#define dev_err_probe(d,r,...) (r)
#define GFP_KERNEL 0
#define DWC3_APSD_PHY 64
typedef uint64_t u64;typedef uint32_t u32;typedef uint8_t u8;typedef int32_t s32;
struct mutex {pthread_mutex_t p;};
#define DEFINE_MUTEX(n) struct mutex n={PTHREAD_MUTEX_INITIALIZER}
static void mutex_init(struct mutex*m){assert(!pthread_mutex_init(&m->p,NULL));}
static void mutex_lock(struct mutex*m){assert(!pthread_mutex_lock(&m->p));}
static void mutex_unlock(struct mutex*m){assert(!pthread_mutex_unlock(&m->p));}
#define lockdep_assert_held(m) ((void)0)
struct completion {pthread_mutex_t m;pthread_cond_t c;bool done;};
static void init_completion(struct completion*c){assert(!pthread_mutex_init(&c->m,NULL));assert(!pthread_cond_init(&c->c,NULL));c->done=false;}
static void complete_all(struct completion*c){pthread_mutex_lock(&c->m);c->done=true;pthread_cond_broadcast(&c->c);pthread_mutex_unlock(&c->m);}
static void reinit_completion(struct completion*c){pthread_mutex_lock(&c->m);c->done=false;pthread_mutex_unlock(&c->m);}
static void wait_for_completion(struct completion*c){pthread_mutex_lock(&c->m);while(!c->done)pthread_cond_wait(&c->c,&c->m);pthread_mutex_unlock(&c->m);}
static void completion_destroy(struct completion*c){assert(!pthread_mutex_destroy(&c->m));assert(!pthread_cond_destroy(&c->c));}
struct list_head {struct list_head*next,*prev;};
#define LIST_HEAD(n) struct list_head n={&n,&n}
static void INIT_LIST_HEAD(struct list_head*n){n->next=n->prev=n;}
static void list_add_tail(struct list_head*n,struct list_head*h){n->next=h;n->prev=h->prev;h->prev->next=n;h->prev=n;}
static void list_del_init(struct list_head*n){n->next->prev=n->prev;n->prev->next=n->next;INIT_LIST_HEAD(n);}
#define list_for_each_entry(p,h,m) for(p=container_of((h)->next,__typeof__(*p),m);&(p)->m!=(h);p=container_of((p)->m.next,__typeof__(*p),m))
struct gate {pthread_mutex_t m;pthread_cond_t c;bool reached,release;};
static void gate_init(struct gate*g){pthread_mutex_init(&g->m,NULL);pthread_cond_init(&g->c,NULL);g->reached=g->release=false;}
static void gate_signal(struct gate*g,bool block){if(!g)return;pthread_mutex_lock(&g->m);g->reached=true;pthread_cond_broadcast(&g->c);while(block&&!g->release)pthread_cond_wait(&g->c,&g->m);pthread_mutex_unlock(&g->m);}
static void gate_wait(struct gate*g){pthread_mutex_lock(&g->m);while(!g->reached)pthread_cond_wait(&g->c,&g->m);pthread_mutex_unlock(&g->m);}
static void gate_release(struct gate*g){pthread_mutex_lock(&g->m);g->release=true;pthread_cond_broadcast(&g->c);pthread_mutex_unlock(&g->m);}
static void gate_destroy(struct gate*g){pthread_mutex_destroy(&g->m);pthread_cond_destroy(&g->c);}
enum phy_mode{PHY_MODE_INVALID,PHY_MODE_USB_HOST,PHY_MODE_USB_DEVICE};
struct action {void(*fn)(void*);void*data;int kind;};
struct device {void*data;struct action actions[20];int count;};
struct phy;struct phy_ops {int(*init)(struct phy*);int(*exit)(struct phy*);int(*set_mode)(struct phy*,enum phy_mode,int);void*owner;};
struct phy {struct device dev;const struct phy_ops*ops;struct mutex mutex;int init_count;};
struct platform_device {struct device dev;};
struct clk_bulk_data{const char*id;void*clk;};struct reset_control{int dummy;};
struct regulator_bulk_data{const char*supply;};struct phy_override_seq{bool need_update;u8 offset,value,mask;};
struct phy_provider{int dummy;};
#include "tested-types.inc"
static struct qcom_snps_hsphy*active;
static struct phy*probe_phy;static u32 regs[64];
static atomic_int refs,reads,writes;static int pm_result=1,drop_write;
static bool mmio_released,fail_action,fail_provider;static int resource_releases,terminal_before_release,action_calls;
static atomic_int pm_disables;static struct completion*runtime_done;static struct gate*disable_gate;
static struct gate *get_gate;
static void*phy_get_drvdata(struct phy*p){return p->dev.data;}
static void*dev_get_drvdata(struct device*d){return d->data;}
static void dev_set_drvdata(struct device*d,void*p){d->data=p;}
static void phy_set_drvdata(struct phy*p,void*d){p->dev.data=d;}
static void*platform_get_drvdata(struct platform_device*p){return p->dev.data;}
static int pm_runtime_get_if_active(struct device*d){gate_signal(get_gate,true);if(pm_result>0)atomic_fetch_add(&refs,1);return pm_result;}
static void pm_runtime_put_noidle(struct device*d){assert(atomic_fetch_sub(&refs,1)>0);}
static void pm_runtime_mark_last_busy(struct device*d){}
static void pm_runtime_put_autosuspend(struct device*d){pm_runtime_put_noidle(d);}
static void pm_runtime_put(struct device*d){pm_runtime_put_noidle(d);}
static void pm_runtime_get_noresume(struct device*d){atomic_fetch_add(&refs,1);}
static void pm_runtime_set_active(struct device*d){}
static void pm_runtime_forbid(struct device*d){}
static void pm_runtime_enable(struct device*d){}
static void pm_runtime_disable(struct device*d){atomic_fetch_add(&pm_disables,1);gate_signal(disable_gate,false);if(runtime_done)wait_for_completion(runtime_done);}
static void pm_runtime_dont_use_autosuspend(struct device*d){}
static u32 readl_relaxed(void*p){assert(!mmio_released);size_t i=((uintptr_t)p-(uintptr_t)active->base)/4;assert(i<64);atomic_fetch_add(&reads,1);return regs[i];}
static void writel_relaxed(u32 v,void*p){assert(!mmio_released);size_t i=((uintptr_t)p-(uintptr_t)active->base)/4;assert(i<64);int n=atomic_fetch_add(&writes,1)+1;if(n!=drop_write)regs[i]=v;}
static int regulator_bulk_enable(int n,struct regulator_bulk_data*v){assert(!mmio_released);return 0;}
static int regulator_bulk_disable(int n,struct regulator_bulk_data*v){assert(!mmio_released);return 0;}
static int clk_bulk_prepare_enable(int n,struct clk_bulk_data*c){assert(!mmio_released);return 0;}
static void clk_bulk_disable_unprepare(int n,struct clk_bulk_data*c){assert(!mmio_released);}
static int reset_control_assert(struct reset_control*r){assert(!mmio_released);return 0;}
static int reset_control_deassert(struct reset_control*r){assert(!mmio_released);return 0;}
static void usleep_range(unsigned a,unsigned b){}
static void release_resource(void*p){struct qcom_snps_hsphy*h=p;resource_releases++;assert(h->window_dead&&!h->window_published);terminal_before_release++;mmio_released=true;}
static void push(struct device*d,void(*fn)(void*),void*p,int kind){assert(d->count<20);d->actions[d->count++]=(struct action){fn,p,kind};}
static void*devm_kzalloc(struct device*d,size_t n,int flags){void*p=calloc(1,n);assert(p);active=p;return p;}
static void*devm_platform_ioremap_resource(struct platform_device*p,int i){push(&p->dev,release_resource,active,1);return regs;}
static int qcom_snps_hsphy_clk_init(struct qcom_snps_hsphy*h){push(h->dev,release_resource,h,2);return 0;}
static struct reset_control*devm_reset_control_get_exclusive(struct device*d,void*n){static struct reset_control r;push(d,release_resource,active,3);return &r;}
static int devm_regulator_bulk_get(struct device*d,int n,struct regulator_bulk_data*v){push(d,release_resource,active,4);return 0;}
static struct phy*devm_phy_create(struct device*d,void*n,const struct phy_ops*ops){probe_phy=calloc(1,sizeof(*probe_phy));assert(probe_phy);probe_phy->ops=ops;mutex_init(&probe_phy->mutex);push(d,release_resource,active,6);return probe_phy;}
static void qcom_snps_hsphy_read_override_param_seq(struct device*d){}
static const char*const qcom_snps_hsphy_vreg_names[]={"a","b","c"};
#define of_phy_simple_xlate NULL
static struct phy_provider*devm_of_phy_provider_register(struct device*d,void*f){static struct phy_provider p;if(fail_provider)return ERR_PTR(-EIO);push(d,release_resource,active,7);return &p;}
static int devm_add_action_or_reset(struct device*d,void(*fn)(void*),void*p){action_calls++;if(fail_action&&action_calls==2){fn(p);return -ENOMEM;}push(d,fn,p,action_calls==1?5:8);return 0;}
#include "tested-functions.inc"
static const struct phy_ops qcom_snps_hsphy_gen_ops={.init=qcom_snps_hsphy_init,.exit=qcom_snps_hsphy_exit,.set_mode=qcom_snps_hsphy_set_mode};
static void free_completions(struct qcom_snps_hsphy*h){completion_destroy(&h->window_operations_done);completion_destroy(&h->window_callbacks_done);completion_destroy(&h->window_revoke_done);pthread_mutex_destroy(&h->window_pm_stop_lock.p);}
static void setup(struct qcom_snps_hsphy*h,struct phy*p,struct device*d){memset(h,0,sizeof(*h));memset(p,0,sizeof(*p));memset(d,0,sizeof(*d));mutex_init(&p->mutex);h->dev=d;d->data=h;h->phy=p;p->dev.data=h;p->ops=&qcom_snps_hsphy_gen_ops;p->init_count=1;h->phy_initialized=true;h->mode=PHY_MODE_USB_DEVICE;h->base=regs;active=h;memset(regs,0,sizeof(regs));regs[0x64/4]=0xa4;regs[0x3c/4]=0xf0;regs[0x94/4]=0xa2;atomic_store(&refs,0);atomic_store(&reads,0);atomic_store(&writes,0);atomic_store(&pm_disables,0);runtime_done=NULL;disable_gate=NULL;drop_write=0;pm_result=1;get_gate=NULL;mmio_released=fail_action=fail_provider=false;window_provider_init(h);assert(!window_provider_publish(h));}
struct client {atomic_int refs,cancels,completes;int error;bool retain;struct gate*complete_gate,*ref_gate;struct qcom_snps_hsphy_window_binding b;struct qcom_snps_hsphy_window_result r;};
static bool cget(void*p){struct client*c=p;int n=atomic_load(&c->refs);while(n&&!atomic_compare_exchange_weak(&c->refs,&n,n+1)){}gate_signal(c->ref_gate,false);return n!=0;}
static void cput(void*p){struct client*c=p;assert(atomic_fetch_sub(&c->refs,1)>0);}
static int ccancel(void*p,const struct qcom_snps_hsphy_window_binding*b,enum qcom_snps_hsphy_window_reason reason){struct client*c=p;atomic_fetch_add(&c->cancels,1);if(c->error)return c->error;if(c->r.cookie&&!c->retain){int ret=qcom_snps_hsphy_window_end(b,c->r.cookie,&c->r);if(ret)return ret;c->r.cookie=0;}return 0;}
static void ccomplete(void*p,const struct qcom_snps_hsphy_window_binding*b){struct client*c=p;gate_signal(c->complete_gate,true);atomic_fetch_add(&c->completes,1);}
static void attach(struct phy*p,struct client*c){memset(c,0,sizeof(*c));atomic_init(&c->refs,1);struct qcom_snps_hsphy_window_client x={c,cget,cput,ccancel,ccomplete};assert(!qcom_snps_hsphy_window_client_register(p,&x,&c->b));assert(atomic_load(&c->refs)==2);}
static void finish(struct qcom_snps_hsphy*h,struct phy*p,struct client*c){assert(!window_provider_quiesce(h,QCOM_HSPHY_WINDOW_REMOVE,true));assert(atomic_load(&c->refs)==1&&!atomic_load(&refs));free_completions(h);pthread_mutex_destroy(&p->mutex.p);}
static void ok(const char*n){printf("ok: %s\n",n);}
struct threadarg {struct qcom_snps_hsphy*h;struct client*c;int ret;atomic_bool done;};
static void*withdraw_thread(void*p){struct threadarg*a=p;a->ret=window_provider_quiesce(a->h,QCOM_HSPHY_WINDOW_REMOVE,true);atomic_store(&a->done,true);return NULL;}
static void*begin_thread(void*p){struct threadarg*a=p;a->ret=qcom_snps_hsphy_window_begin(&a->c->b,&a->c->r);return NULL;}
static void*complete_thread(void*p){struct threadarg*a=p;window_provider_complete(a->h,QCOM_HSPHY_WINDOW_SYSTEM);return NULL;}
static void test_registration(void){struct qcom_snps_hsphy h;struct phy p;struct device d;struct client c;setup(&h,&p,&d);attach(&p,&c);struct qcom_snps_hsphy_window_binding old=c.b,x;struct qcom_snps_hsphy_window_client client={&c,cget,cput,ccancel,ccomplete};assert(qcom_snps_hsphy_window_client_register(&p,&client,&x)==-EBUSY);assert(!qcom_snps_hsphy_window_client_unregister(&c.b));assert(atomic_load(&c.refs)==1);atomic_store(&c.refs,0);assert(qcom_snps_hsphy_window_client_register(&p,&client,&x)==-ESHUTDOWN);atomic_store(&c.refs,1);assert(!qcom_snps_hsphy_window_client_register(&p,&client,&c.b));assert(c.b.client_id>old.client_id);assert(qcom_snps_hsphy_window_begin(&old,&c.r)==-ESHUTDOWN&&!atomic_load(&writes));assert(!qcom_snps_hsphy_window_begin(&c.b,&c.r));finish(&h,&p,&c);ok("registration actual client refs, failed get, duplicate and stale registration refused");}
static void test_failure_and_reprobe(void){struct qcom_snps_hsphy*h=calloc(1,sizeof(*h));struct phy*p=calloc(1,sizeof(*p));struct device d;struct client c;setup(h,p,&d);attach(p,&c);assert(!qcom_snps_hsphy_window_begin(&c.b,&c.r));drop_write=4;assert(window_provider_quiesce(h,QCOM_HSPHY_WINDOW_REMOVE,true)==-EIO);assert(h->window.restore_error==-EIO&&h->window.lifecycle_error==-EIO&&h->window.provider_revoked&&!h->window.restored);assert(!atomic_load(&refs)&&atomic_load(&c.refs)==1);int w=atomic_load(&writes),r=atomic_load(&reads);struct qcom_snps_hsphy_window_binding old=c.b;free_completions(h);pthread_mutex_destroy(&p->mutex.p);free(p);free(h);mmio_released=true;assert(qcom_snps_hsphy_window_end(&old,c.r.cookie,&c.r)==-ESHUTDOWN);assert(c.r.restore_error==-EIO&&c.r.provider_revoked&&c.r.lifecycle_error==-ESHUTDOWN);assert(w==atomic_load(&writes)&&r==atomic_load(&reads));struct qcom_snps_hsphy newer;struct phy np;struct device nd;struct client nc;setup(&newer,&np,&nd);attach(&np,&nc);assert(nc.b.provider_id>old.provider_id);struct qcom_snps_hsphy_window_binding forged=old;forged.phy=&np;assert(qcom_snps_hsphy_window_begin(&forged,&c.r)==-ESHUTDOWN);finish(&newer,&np,&nc);ok("restore failure keeps errno; final revoke drains PM; freed/rebound old identity zero MMIO");}
static void test_pm_shutdown(void){struct qcom_snps_hsphy h;struct phy p;struct device d;struct client c;setup(&h,&p,&d);attach(&p,&c);assert(!qcom_snps_hsphy_window_begin(&c.b,&c.r));c.error=-EIO;assert(qcom_snps_hsphy_prepare(&d)==-EIO);assert(qcom_snps_hsphy_runtime_suspend(&d)==-EIO);qcom_snps_hsphy_complete(&d);assert(!atomic_load(&c.completes));c.error=0;assert(!qcom_snps_hsphy_prepare(&d));qcom_snps_hsphy_complete(&d);assert(!atomic_load(&c.completes));assert(!qcom_snps_hsphy_runtime_resume(&d));assert(atomic_load(&c.completes)==1);struct platform_device pd={.dev=d};qcom_snps_hsphy_shutdown(&pd);int w=atomic_load(&writes),r=atomic_load(&reads);qcom_snps_hsphy_complete(&d);assert(qcom_snps_hsphy_runtime_resume(&d)==-ESHUTDOWN);mutex_lock(&p.mutex);assert(qcom_snps_hsphy_set_mode(&p,PHY_MODE_USB_HOST,0)==-ESHUTDOWN);assert(qcom_snps_hsphy_init(&p)==-ESHUTDOWN);assert(qcom_snps_hsphy_exit(&p)==-ESHUTDOWN);mutex_unlock(&p.mutex);assert(w==atomic_load(&writes)&&r==atomic_load(&reads)&&atomic_load(&c.completes)==1);finish(&h,&p,&c);ok("real PM wrappers refuse failed join; shutdown cannot republish through complete/resume/generic ops");}
static void test_inflight(void){struct qcom_snps_hsphy h;struct phy p;struct device d;struct client c;setup(&h,&p,&d);attach(&p,&c);c.error=-EBUSY;struct gate g;gate_init(&g);get_gate=&g;struct threadarg a={.h=&h,.c=&c};pthread_t b,t;pthread_create(&b,NULL,begin_thread,&a);gate_wait(&g);struct threadarg z={.h=&h,.c=&c};pthread_create(&t,NULL,withdraw_thread,&z);while(!atomic_load(&c.cancels))sched_yield();assert(!atomic_load(&z.done));struct qcom_snps_hsphy_window_result x;assert(qcom_snps_hsphy_window_begin(&c.b,&x)<0);gate_release(&g);pthread_join(b,NULL);pthread_join(t,NULL);assert(a.ret==0&&z.ret==-EBUSY&&!atomic_load(&refs)&&h.window_dead);get_gate=NULL;assert(qcom_snps_hsphy_window_end(&c.b,c.r.cookie,&c.r)==-ESHUTDOWN);assert(atomic_load(&c.refs)==1);free_completions(&h);pthread_mutex_destroy(&p.mutex.p);gate_destroy(&g);ok("inflight begin drains before forced resource release; late token is revoked, never restored claim");}
static void test_complete_join(void){struct qcom_snps_hsphy h;struct phy p;struct device d;struct client c;setup(&h,&p,&d);attach(&p,&c);assert(!qcom_snps_hsphy_prepare(&d));struct gate g;gate_init(&g);c.complete_gate=&g;struct threadarg a={.h=&h,.c=&c};pthread_t t,w;pthread_create(&t,NULL,complete_thread,&a);gate_wait(&g);struct threadarg z={.h=&h,.c=&c};pthread_create(&w,NULL,withdraw_thread,&z);while(!READ_ONCE(h.window_revoking))sched_yield();assert(atomic_load(&c.cancels)==1&&!atomic_load(&z.done));gate_release(&g);pthread_join(t,NULL);pthread_join(w,NULL);assert(z.ret==0&&atomic_load(&c.completes)==1&&atomic_load(&c.cancels)==2&&atomic_load(&c.refs)==1);free_completions(&h);pthread_mutex_destroy(&p.mutex.p);gate_destroy(&g);ok("already dispatched complete callback finishes before cancel_join, no late producer after join");}
/* Actual owner ref/callback integration; no old join algorithm is copied. */
struct kref {atomic_int count;};
static bool kref_get_unless_zero(struct kref*k){int n=atomic_load(&k->count);while(n&&!atomic_compare_exchange_weak(&k->count,&n,n+1)){}return n!=0;}
static void kref_put(struct kref*k,void(*release)(struct kref*)){int n=atomic_fetch_sub(&k->count,1);assert(n>0);if(n==1)release(k);}
static atomic_int freed,joins;static bool last_retiring;static struct gate*owner_ref_gate;
static void kfree(void*p){atomic_fetch_add(&freed,1);free(p);}
static void put_device(struct device*d){}
struct dwc3 {struct phy*usb2_generic_phy[1];};
struct samurai_apsd_bus_ops {void*read_sample,*rerun_once;};
struct samurai_apsd_owner {struct kref ref;struct dwc3*dwc;struct device*typec;struct qcom_snps_hsphy_window_binding phy_binding;struct qcom_snps_hsphy_window_result phy;unsigned blocked;bool abort,retiring,quarantined;int lock,work;const struct samurai_apsd_bus_ops*bus;};
static DEFINE_MUTEX(owner_registry);
#define spin_lock_irqsave(l,f) ((f)=0)
#define spin_unlock_irqrestore(l,f) ((void)(f))
static void cancel_delayed_work_sync(int*w){}
static void owner_queue(struct samurai_apsd_owner*o,unsigned long d){}
static void owner_quarantine(struct samurai_apsd_owner*o){o->quarantined=true;}
static int owner_join(struct samurai_apsd_owner*o,unsigned r,bool retiring){last_retiring=retiring;atomic_fetch_add(&joins,1);o->blocked|=r;if(o->phy.cookie){int ret=qcom_snps_hsphy_window_end(&o->phy_binding,o->phy.cookie,&o->phy);if(ret)return ret;o->phy.cookie=0;}return 0;}
#include "tested-owner.inc"
static bool owner_get_signal(void*p){bool ret=owner_pd_get(p);gate_signal(owner_ref_gate,false);return ret;}
static void test_actual_owner_unregister(void){struct qcom_snps_hsphy h;struct phy p;struct device d;setup(&h,&p,&d);struct dwc3 dwc={.usb2_generic_phy={&p}};struct samurai_apsd_owner*o=calloc(1,sizeof(*o));atomic_init(&o->ref.count,1);o->dwc=&dwc;assert(!owner_phy_attach(o));assert(atomic_load(&o->ref.count)==2);assert(!qcom_snps_hsphy_window_begin(&o->phy_binding,&o->phy));assert(!window_provider_quiesce(&h,QCOM_HSPHY_WINDOW_SYSTEM,false)&&!last_retiring);window_provider_complete(&h,QCOM_HSPHY_WINDOW_SYSTEM);assert(!qcom_snps_hsphy_window_begin(&o->phy_binding,&o->phy));assert(!window_provider_quiesce(&h,QCOM_HSPHY_WINDOW_SHUTDOWN,true)&&last_retiring&&o->quarantined);owner_phy_detach(o);owner_pd_put(o);assert(atomic_load(&freed)==1);free_completions(&h);pthread_mutex_destroy(&p.mutex.p);
 setup(&h,&p,&d);o=calloc(1,sizeof(*o));atomic_init(&o->ref.count,1);o->dwc=&dwc;assert(!owner_phy_attach(o));struct gate g;gate_init(&g);owner_ref_gate=&g;h.window_client.get_unless_zero=owner_get_signal;mutex_lock(&owner_registry);struct threadarg z={.h=&h};pthread_t t;pthread_create(&t,NULL,withdraw_thread,&z);gate_wait(&g);owner_phy_detach(o);assert(!o->phy_binding.phy);o->dwc=NULL;owner_pd_put(o);assert(atomic_load(&freed)==1);mutex_unlock(&owner_registry);pthread_join(t,NULL);assert(z.ret==0&&atomic_load(&freed)==2);owner_ref_gate=NULL;free_completions(&h);pthread_mutex_destroy(&p.mutex.p);gate_destroy(&g);ok("actual DWC callbacks choose retirement; unregister racing callback retains real kref without reverse join");}
static void test_probe_devres(void){for(int fail=0;fail<2;fail++){struct platform_device pd={0};fail_action=fail;fail_provider=false;mmio_released=false;resource_releases=terminal_before_release=action_calls=0;atomic_store(&refs,0);atomic_store(&pm_disables,0);int ret=qcom_snps_hsphy_probe(&pd);assert(ret==(fail?-ENOMEM:0));struct qcom_snps_hsphy*h=active;assert((!fail)==h->window_published);if(!fail){assert(pd.dev.actions[pd.dev.count-1].kind==8);qcom_snps_hsphy_remove(&pd);}while(pd.dev.count){struct action a=pd.dev.actions[--pd.dev.count];a.fn(a.data);}assert(resource_releases==6&&terminal_before_release==6&&!window_find(h->phy)&&!atomic_load(&refs)&&atomic_load(&pm_disables)==1);free_completions(h);pthread_mutex_destroy(&probe_phy->mutex.p);free(probe_phy);free(h);}fail_action=false;ok("actual probe: LAST revoke/PM barrier precedes protected devres; action-reset failure and one disable depth");}
static void*runtime_thread(void*p){struct threadarg*a=p;a->ret=qcom_snps_hsphy_runtime_resume(a->h->dev);complete_all(runtime_done);return NULL;}
static void*driver_remove_thread(void*p){struct threadarg*a=p;qcom_snps_hsphy_withdraw(a->h);atomic_store(&a->done,true);return NULL;}
static void test_runtime_devres_barrier(void){struct qcom_snps_hsphy h;struct phy p;struct device d;struct client c;setup(&h,&p,&d);attach(&p,&c);struct gate cg,dg;gate_init(&cg);gate_init(&dg);c.complete_gate=&cg;disable_gate=&dg;struct completion rd;init_completion(&rd);runtime_done=&rd;struct threadarg a={.h=&h},z={.h=&h};pthread_t t,w;pthread_create(&t,NULL,runtime_thread,&a);gate_wait(&cg);pthread_create(&w,NULL,driver_remove_thread,&z);gate_wait(&dg);assert(!atomic_load(&z.done)&&!h.window_dead&&!atomic_load(&c.cancels));gate_release(&cg);pthread_join(t,NULL);pthread_join(w,NULL);assert(!a.ret&&h.window_dead&&atomic_load(&c.cancels)==1&&atomic_load(&pm_disables)==1);window_provider_pm_cleanup(&h);assert(atomic_load(&pm_disables)==1);runtime_done=NULL;disable_gate=NULL;free_completions(&h);pthread_mutex_destroy(&p.mutex.p);completion_destroy(&rd);gate_destroy(&cg);gate_destroy(&dg);ok("actual runtime-resume and withdraw: disable barrier joins callback before terminal/devres, cleanup idempotent");}
int main(void){test_registration();test_failure_and_reprobe();test_pm_shutdown();test_inflight();test_complete_join();test_actual_owner_unregister();test_probe_devres();test_runtime_devres_barrier();struct samurai_apsd_owner o={0};assert(owner_entry_gate(&o)==-ENODEV);struct samurai_apsd_bus_ops b={(void*)1,(void*)1};o.bus=&b;assert(owner_entry_gate(&o)==-EOPNOTSUPP);assert(window_providers.next==&window_providers);ok("final actual owner gate remains EOPNOTSUPP with backend; no route or 1341 permission");return 0;}
