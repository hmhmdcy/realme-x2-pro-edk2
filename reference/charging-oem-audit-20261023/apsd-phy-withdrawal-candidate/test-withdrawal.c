/* Actual driver functions; pthread lifetime, fake PM/MMIO/driver core. */
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
#define __iomem
#define __maybe_unused
#define BIT(n) (1U<<(n))
#define GENMASK(h,l) (((~0U)<<(l))&((~0U)>>(31-(h))))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define GFP_KERNEL 0
#define dev_warn(...) ((void)0)
#define dev_err(...) ((void)0)
#define dev_dbg(...) ((void)0)
#define dev_vdbg(...) ((void)0)
typedef uint64_t u64;typedef uint32_t u32;typedef uint8_t u8;typedef int32_t s32;
struct mutex {pthread_mutex_t native;};
#define DEFINE_MUTEX(n) struct mutex n={PTHREAD_MUTEX_INITIALIZER}
static _Thread_local struct mutex *held[16];static _Thread_local int depth;
static bool own(struct mutex *m){for(int i=0;i<depth;i++)if(held[i]==m)return true;return false;}
static void mutex_init(struct mutex*m){assert(!pthread_mutex_init(&m->native,NULL));}
static void mutex_lock(struct mutex*m){assert(!own(m));assert(!pthread_mutex_lock(&m->native));held[depth++]=m;}
static void mutex_unlock(struct mutex*m){assert(depth&&held[depth-1]==m);depth--;assert(!pthread_mutex_unlock(&m->native));}
static void mutex_destroy(struct mutex*m){assert(!own(m));assert(!pthread_mutex_destroy(&m->native));}
#define lockdep_assert_held(m) assert(own(m))
static pthread_mutex_t events=PTHREAD_MUTEX_INITIALIZER;static pthread_cond_t event=PTHREAD_COND_INITIALIZER;
static int waiters;
struct completion {pthread_mutex_t mutex;pthread_cond_t cond;bool done;};
static void init_completion(struct completion*c){assert(!pthread_mutex_init(&c->mutex,NULL));assert(!pthread_cond_init(&c->cond,NULL));c->done=false;}
static void complete_all(struct completion*c){pthread_mutex_lock(&c->mutex);c->done=true;pthread_cond_broadcast(&c->cond);pthread_mutex_unlock(&c->mutex);}
static void wait_for_completion(struct completion*c){assert(!depth);pthread_mutex_lock(&events);waiters++;pthread_cond_broadcast(&event);pthread_mutex_unlock(&events);pthread_mutex_lock(&c->mutex);while(!c->done)pthread_cond_wait(&c->cond,&c->mutex);pthread_mutex_unlock(&c->mutex);}
struct kref {atomic_uint count;};
static void kref_init(struct kref*r){atomic_init(&r->count,1);}
static void kref_get(struct kref*r){assert(atomic_fetch_add(&r->count,1)>0);}
static void kref_put(struct kref*r,void(*release)(struct kref*)){unsigned n=atomic_fetch_sub(&r->count,1);assert(n);if(n==1)release(r);}
struct list_head {struct list_head *next,*prev;};
#define LIST_HEAD(n) struct list_head n={&n,&n}
static void INIT_LIST_HEAD(struct list_head*n){n->next=n->prev=n;}
static void list_add_tail(struct list_head*n,struct list_head*h){n->prev=h->prev;n->next=h;h->prev->next=n;h->prev=n;}
static void list_del_init(struct list_head*n){n->prev->next=n->next;n->next->prev=n->prev;INIT_LIST_HEAD(n);}
#define list_for_each_entry(p,h,m) for(struct list_head*_n=(h)->next;_n!=(h)&&((p)=container_of(_n,__typeof__(*(p)),m),true);_n=_n->next)
static atomic_int allocations;
static void *kzalloc(size_t n,int flags){void*p=calloc(1,n);assert(p);atomic_fetch_add(&allocations,1);return p;}
static void kfree(void*p){assert(!depth);if(p)atomic_fetch_sub(&allocations,1);free(p);}
enum phy_mode {PHY_MODE_INVALID,PHY_MODE_USB_HOST,PHY_MODE_USB_DEVICE};
struct device {void*data;void(*cleanup)(void*);void*cleanup_data;};
struct platform_device {struct device dev;};struct phy;
struct phy_ops {int(*init)(struct phy*);int(*exit)(struct phy*);int(*set_mode)(struct phy*,enum phy_mode,int);};
struct phy {struct device dev;struct mutex mutex;const struct phy_ops*ops;int init_count;};
struct clk_bulk_data {int x;};struct reset_control {int x;};struct regulator_bulk_data {int x;};
struct phy_override_seq {bool need_update;u8 offset,value,mask;};
#include "actual-types.inc"
static struct qcom_snps_hsphy *current;static struct phy phy;static struct platform_device platform;
static int refs,reads,writes,drop_write,pm_result,devm_fail;static u32 regs[64];
static bool block_write,write_entered,allow_write;
static void*phy_get_drvdata(struct phy*p){return p->dev.data;}
static void*dev_get_drvdata(struct device*d){return d->data;}
static int pm_runtime_get_if_active(struct device*d){assert(!own(&current->phy->mutex));if(pm_result>0)refs++;return pm_result;}
static void pm_runtime_put_noidle(struct device*d){assert(!own(&current->phy->mutex));assert(refs>0);refs--;}
static void pm_runtime_mark_last_busy(struct device*d){assert(!own(&current->phy->mutex));}
static void pm_runtime_put_autosuspend(struct device*d){pm_runtime_put_noidle(d);}
static u32 readl_relaxed(void*p){size_t i=((uintptr_t)p-(uintptr_t)current->base)/4;assert(i<64);reads++;return regs[i];}
static void writel_relaxed(u32 v,void*p){size_t i=((uintptr_t)p-(uintptr_t)current->base)/4;assert(i<64);writes++;
 if(block_write){pthread_mutex_lock(&events);write_entered=true;pthread_cond_broadcast(&event);while(!allow_write)pthread_cond_wait(&event,&events);pthread_mutex_unlock(&events);block_write=false;}
 if(writes!=drop_write)regs[i]=v;}
static int regulator_bulk_enable(int n,struct regulator_bulk_data*v){return 0;}
static int regulator_bulk_disable(int n,struct regulator_bulk_data*v){return 0;}
static int clk_bulk_prepare_enable(int n,struct clk_bulk_data*c){return 0;}
static void clk_bulk_disable_unprepare(int n,struct clk_bulk_data*c){}
static int reset_control_assert(struct reset_control*r){return 0;}
static int reset_control_deassert(struct reset_control*r){return 0;}
static void usleep_range(int a,int b){}
static int devm_add_action_or_reset(struct device*d,void(*fn)(void*),void*data){if(devm_fail){fn(data);return -ENOMEM;}d->cleanup=fn;d->cleanup_data=data;return 0;}
#include "actual-functions.inc"
static const struct phy_ops qcom_snps_hsphy_gen_ops={.init=qcom_snps_hsphy_init,.exit=qcom_snps_hsphy_exit,.set_mode=qcom_snps_hsphy_set_mode};
struct owner {struct qcom_snps_hsphy_window_client*c;int refs,calls;bool accept,restore,unregister_inside,join_worker,block_callback,callback_entered,allow_callback;pthread_t worker;u64 cookie;};
static bool owner_get(void*data){struct owner*o=data;assert(!depth);if(!o->accept)return false;o->refs++;return true;}
static void owner_put(void*data){struct owner*o=data;assert(!depth&&o->refs>1);o->refs--;}
static int cancel_join(void*data){struct owner*o=data;assert(!depth&&o->refs==2);o->calls++;
 if(o->block_callback){pthread_mutex_lock(&events);o->callback_entered=true;pthread_cond_broadcast(&event);while(!o->allow_callback)pthread_cond_wait(&event,&events);pthread_mutex_unlock(&events);}
 if(o->join_worker)assert(!pthread_join(o->worker,NULL));
 struct qcom_snps_hsphy_window_result r;assert(qcom_snps_hsphy_window_begin(o->c,&r)==-ESHUTDOWN&&!r.cookie);
 assert(!qcom_snps_hsphy_window_status(o->c,&r)&&r.revoked);
 int ret=0;if(o->restore&&o->cookie)ret=qcom_snps_hsphy_window_end(o->c,o->cookie,&r);
 if(o->unregister_inside){assert(!ret&&!qcom_snps_hsphy_window_client_unregister(o->c));o->c=NULL;assert(o->refs==2);}
 return ret;}
static const struct qcom_snps_hsphy_window_client_ops ops={owner_get,owner_put,cancel_join};
static void setup(struct qcom_snps_hsphy*h,struct owner*o){memset(h,0,sizeof(*h));memset(o,0,sizeof(*o));memset(&phy,0,sizeof(phy));memset(&platform,0,sizeof(platform));memset(regs,0,sizeof(regs));mutex_init(&phy.mutex);
 current=h;h->dev=&platform.dev;h->phy=&phy;h->base=regs;h->phy_initialized=true;h->mode=PHY_MODE_USB_DEVICE;phy.dev.data=h;platform.dev.data=h;phy.ops=&qcom_snps_hsphy_gen_ops;phy.init_count=1;
 refs=reads=writes=drop_write=devm_fail=0;pm_result=1;block_write=write_entered=allow_write=false;waiters=0;o->refs=1;o->accept=true;o->restore=true;
 regs[0x64/4]=0xa4;regs[0x3c/4]=0xf0;regs[0x94/4]=0xa2;}
static void publish(struct qcom_snps_hsphy*h,struct owner*o){assert(!qcom_hsphy_window_publish(h));assert(!qcom_snps_hsphy_window_client_register(&phy,&ops,o,&o->c)&&o->refs==2);}
static void begin(struct owner*o){struct qcom_snps_hsphy_window_result r;assert(!qcom_snps_hsphy_window_begin(o->c,&r)&&r.high_z&&r.cookie);o->cookie=r.cookie;}
static void release_provider(void){assert(platform.dev.cleanup);void(*f)(void*)=platform.dev.cleanup;platform.dev.cleanup=NULL;f(platform.dev.cleanup_data);}
static void finish(struct owner*o,const char*name){if(o->c){assert(!qcom_snps_hsphy_window_client_unregister(o->c));o->c=NULL;}assert(o->refs==1&&!refs&&!depth&&!atomic_load(&allocations));mutex_destroy(&phy.mutex);printf("ok: %s\n",name);}
static void*remove_thread(void*data){qcom_snps_hsphy_remove(&platform);return NULL;}
static void*release_thread(void*data){release_provider();return NULL;}
static void*begin_thread(void*data){begin(data);return NULL;}
int main(void){
 struct qcom_snps_hsphy h;struct owner o;struct qcom_snps_hsphy_window_result r;struct qcom_snps_hsphy_window_client*x;struct phy wrong={0};
 setup(&h,&o);assert(!qcom_hsphy_window_publish(&h));assert(qcom_snps_hsphy_window_client_register(&wrong,&ops,&o,&x)==-ENODEV&&o.refs==1);
 o.accept=false;assert(qcom_snps_hsphy_window_client_register(&phy,&ops,&o,&x)==-ESHUTDOWN);o.accept=true;
 assert(!qcom_snps_hsphy_window_client_register(&phy,&ops,&o,&o.c));assert(qcom_snps_hsphy_window_client_register(&phy,&ops,&o,&x)==-EBUSY&&o.refs==2);
 assert(!qcom_snps_hsphy_window_client_unregister(o.c));o.c=NULL;release_provider();assert(!writes&&!reads&&!o.calls);finish(&o,"publication is zero I/O; exact instance, owner lifetime and single client");
 setup(&h,&o);publish(&h,&o);begin(&o);assert(refs==1&&writes==3);assert(qcom_snps_hsphy_window_client_unregister(o.c)==-EBUSY);
 assert(qcom_snps_hsphy_window_end(o.c,o.cookie+1,&r)==-ESTALE);assert(!qcom_snps_hsphy_window_end(o.c,o.cookie,&r)&&r.restored&&r.restored_mask==7);
 assert(regs[0x64/4]==0xa4&&regs[0x3c/4]==0xf0&&regs[0x94/4]==0xa2&&!refs);o.cookie=0;release_provider();finish(&o,"original OEM masked sequence and exact restore; busy unregister preserves owner");
 setup(&h,&o);publish(&h,&o);begin(&o);qcom_snps_hsphy_remove(&platform);assert(o.calls==1&&!refs&&writes==6);
 assert(!qcom_snps_hsphy_window_status(o.c,&r)&&r.revoked&&r.restored&&!r.withdraw_error);release_provider();assert(o.calls==1);
 int old=writes;memset(&h,0xa5,sizeof(h));assert(qcom_snps_hsphy_window_begin(o.c,&r)==-ESHUTDOWN);assert(qcom_snps_hsphy_window_end(o.c,o.cookie,&r)==-ESHUTDOWN&&r.revoked&&writes==old);finish(&o,"remove joins and restores before devres; old handle is readable tombstone only");
 setup(&h,&o);publish(&h,&o);begin(&o);drop_write=4;release_provider();assert(o.calls==1&&!refs&&writes==4);
 assert(!qcom_snps_hsphy_window_status(o.c,&r)&&r.revoked&&!r.restored&&!r.high_z&&r.restore_error==-EIO&&r.withdraw_error==-EIO);
 assert(qcom_snps_hsphy_window_end(o.c,o.cookie,&r)==-ESHUTDOWN&&writes==4);finish(&o,"failed restore retains independent error; forced withdrawal balances PM without retry");
 setup(&h,&o);publish(&h,&o);drop_write=1;assert(qcom_snps_hsphy_window_begin(o.c,&r)==-EIO);o.cookie=r.cookie;o.restore=false;release_provider();
 assert(!refs&&writes==1&&!qcom_snps_hsphy_window_status(o.c,&r)&&r.enter_error==-EIO&&r.withdraw_error==-ESHUTDOWN&&!r.restored);finish(&o,"unfinished failed entry is revoked, never reported restored or retried");
 setup(&h,&o);publish(&h,&o);begin(&o);o.unregister_inside=true;release_provider();assert(!o.c&&o.calls==1);finish(&o,"callback may unregister; its context lives until callback return");
 setup(&h,&o);publish(&h,&o);block_write=true;o.join_worker=true;assert(!pthread_create(&o.worker,NULL,begin_thread,&o));
 pthread_mutex_lock(&events);while(!write_entered)pthread_cond_wait(&event,&events);pthread_mutex_unlock(&events);
 pthread_t remover;assert(!pthread_create(&remover,NULL,remove_thread,NULL));pthread_mutex_lock(&events);allow_write=true;pthread_cond_broadcast(&event);pthread_mutex_unlock(&events);
 assert(!pthread_join(remover,NULL)&&o.calls==1&&!refs&&writes==6);release_provider();finish(&o,"real concurrent in-flight begin drains; provider callback joins original worker");
 setup(&h,&o);publish(&h,&o);o.block_callback=true;o.unregister_inside=true;pthread_t second;assert(!pthread_create(&remover,NULL,remove_thread,NULL));
 pthread_mutex_lock(&events);while(!o.callback_entered)pthread_cond_wait(&event,&events);pthread_mutex_unlock(&events);assert(!pthread_create(&second,NULL,release_thread,NULL));
 pthread_mutex_lock(&events);while(!waiters)pthread_cond_wait(&event,&events);o.allow_callback=true;pthread_cond_broadcast(&event);pthread_mutex_unlock(&events);
 assert(!pthread_join(remover,NULL)&&!pthread_join(second,NULL)&&o.calls==1);assert(!platform.dev.cleanup&&!o.c);finish(&o,"concurrent devres withdrawal waits once; final context/publication release cannot free its waiter");
 setup(&h,&o);publish(&h,&o);qcom_snps_hsphy_shutdown(&platform);int prior=reads+writes;
 assert(qcom_snps_hsphy_init(&phy)==-ESHUTDOWN&&qcom_snps_hsphy_exit(&phy)==-ESHUTDOWN&&qcom_snps_hsphy_set_mode(&phy,PHY_MODE_USB_HOST,0)==-ESHUTDOWN);
 assert(qcom_snps_hsphy_runtime_suspend(&platform.dev)==-ESHUTDOWN&&qcom_snps_hsphy_runtime_resume(&platform.dev)==-ESHUTDOWN&&reads+writes==prior);
 release_provider();finish(&o,"shutdown revokes ordinary lifecycle entry as well as detection calls");
 setup(&h,&o);devm_fail=1;assert(qcom_hsphy_window_publish(&h)==-ENOMEM&&!atomic_load(&allocations)&&!refs&&!writes&&!reads);finish(&o,"probe action failure synchronously withdraws publication and frees state");
 return 0;
}
