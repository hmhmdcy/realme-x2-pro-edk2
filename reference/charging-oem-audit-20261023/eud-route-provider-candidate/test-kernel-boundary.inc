#include <pthread.h>
#include <stdatomic.h>
#include <ctype.h>
#define __init
#define __initdata
#define __ro_after_init
#define READ_ONCE(x) __atomic_load_n(&(x),__ATOMIC_SEQ_CST)
#define WRITE_ONCE(x,v) __atomic_store_n(&(x),(v),__ATOMIC_SEQ_CST)
#define GFP_KERNEL 0
#define IORESOURCE_MEM 0x200
#define EXPORT_SYMBOL_GPL(x)
#define MODULE_LICENSE(x)
#define pm_sleep_ptr(x) (x)
#define subsys_initcall(fn) static int (*used_init)(void) __attribute__((used)) = fn
#define WARN_ON(x) ({bool v=!!(x);assert(!v);v;})
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
typedef uint64_t u64;
typedef uint64_t phys_addr_t;
struct mutex {pthread_mutex_t native;};
#define DEFINE_MUTEX(n) struct mutex n={PTHREAD_MUTEX_INITIALIZER}
static _Thread_local struct mutex *locks[16];
static _Thread_local int depth;
static bool own(struct mutex *m){for(int i=0;i<depth;i++)if(locks[i]==m)return true;return false;}
static void mutex_init(struct mutex*m){assert(!pthread_mutex_init(&m->native,NULL));}
static void mutex_lock(struct mutex*m){assert(!own(m));assert(!pthread_mutex_lock(&m->native));locks[depth++]=m;}
static void mutex_unlock(struct mutex*m){assert(depth&&locks[depth-1]==m);depth--;assert(!pthread_mutex_unlock(&m->native));}
static void mutex_destroy(struct mutex*m){assert(!own(m));assert(!pthread_mutex_destroy(&m->native));}
struct completion {pthread_mutex_t mutex;pthread_cond_t cond;bool done;};
static pthread_mutex_t event_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t event_changed=PTHREAD_COND_INITIALIZER;
static int completion_wait_entries;
static void init_completion(struct completion*c){assert(!pthread_mutex_init(&c->mutex,NULL));assert(!pthread_cond_init(&c->cond,NULL));c->done=false;}
static void complete_all(struct completion*c){pthread_mutex_lock(&c->mutex);c->done=true;pthread_cond_broadcast(&c->cond);pthread_mutex_unlock(&c->mutex);}
static void wait_for_completion(struct completion*c){assert(!depth);pthread_mutex_lock(&event_lock);completion_wait_entries++;pthread_cond_broadcast(&event_changed);pthread_mutex_unlock(&event_lock);pthread_mutex_lock(&c->mutex);while(!c->done)pthread_cond_wait(&c->cond,&c->mutex);pthread_mutex_unlock(&c->mutex);}
struct kref {atomic_uint refs;};
static void kref_init(struct kref*r){atomic_init(&r->refs,1);}
static void kref_get(struct kref*r){assert(atomic_fetch_add(&r->refs,1)>0);}
static void kref_put(struct kref*r,void(*release)(struct kref*)){unsigned n=atomic_fetch_sub(&r->refs,1);assert(n);if(n==1)release(r);}
typedef atomic_int atomic_t;
#define ATOMIC_INIT(n) ATOMIC_VAR_INIT(n)
#define atomic_read(p) atomic_load(p)
#define atomic_set(p,v) atomic_store(p,v)
#define smp_mb() atomic_thread_fence(memory_order_seq_cst)
static atomic_int kernel_allocations;
static void *kzalloc(size_t n,int flags){(void)flags;void*p=calloc(1,n);assert(p);atomic_fetch_add(&kernel_allocations,1);return p;}
static void kfree(void*p){assert(!depth);if(p)atomic_fetch_sub(&kernel_allocations,1);free(p);}
static char *kstrdup(const char*s,int flags){(void)flags;char*p=strdup(s);assert(p);atomic_fetch_add(&kernel_allocations,1);return p;}
struct device_node {const char *compatible;bool available;int refs;unsigned long long start,bytes;bool stdout,linux_stdout;};
struct device {struct device_node *of_node;void *data;int refs;bool registered;};
struct resource {unsigned long long start,end;unsigned long flags;};
struct platform_device {struct device dev;struct resource resource;bool has_resource;};
static struct device_node route_node,hardware_node,consumer_node,chosen_node,*of_chosen=&chosen_node;
static int acpi_disabled=1;
static char *saved_command_line;
static struct resource *platform_get_resource(struct platform_device*p,unsigned long type,unsigned int i)
{assert(type==IORESOURCE_MEM&&i==0);return p->has_resource?&p->resource:NULL;}
static unsigned long long resource_size(const struct resource*r){return r->end-r->start+1;}
static struct device *get_device(struct device*d){assert(d);d->refs++;return d;}
static void put_device(struct device*d){assert(d&&d->refs>0);d->refs--;}
static bool device_is_registered(struct device*d){return d->registered;}
static void platform_set_drvdata(struct platform_device*p,void*d){p->dev.data=d;}
static void *platform_get_drvdata(struct platform_device*p){return p->dev.data;}
static void *dev_get_drvdata(struct device*d){return d->data;}
static struct device_node *of_parse_phandle(struct device_node*n,const char*key,int i)
{assert(n==&route_node&&i==0);struct device_node*r=!strcmp(key,"realme,eud-hardware")?&hardware_node:&consumer_node;r->refs++;return r;}
static void of_node_put(struct device_node*n){if(n){assert(n->refs>0);n->refs--;}}
static bool of_device_is_available(struct device_node*n){return n->available;}
static bool of_device_is_compatible(struct device_node*n,const char*name){return !strcmp(n->compatible,name);}
static int of_address_to_resource(struct device_node*n,int i,struct resource*r)
{assert(i==0);*r=(struct resource){n->start,n->start+n->bytes-1,IORESOURCE_MEM};return 0;}
static bool of_property_present(struct device_node*n,const char*key)
{assert(n==&chosen_node);return !strcmp(key,"stdout-path")?n->stdout:n->linux_stdout;}
static void dev_warn(struct device*d,const char*format,...){(void)d;(void)format;}
struct dev_pm_ops {int(*prepare)(struct device*);};
struct of_device_id {const char*compatible;};
struct platform_driver {int(*probe)(struct platform_device*);void(*remove)(struct platform_device*);void(*shutdown)(struct platform_device*);
 struct {const char*name;const struct of_device_id *of_match_table;const struct dev_pm_ops *pm;bool suppress_bind_attrs;} driver;};
static int platform_driver_register(struct platform_driver*d){assert(d->driver.suppress_bind_attrs);return 0;}
static char *skip_spaces(const char*s){while(isspace((unsigned char)*s))s++;return (char*)s;}
/* ACTUAL_NEXT_ARG */
/* ACTUAL_ROUTE_API */
/* ACTUAL_ROUTE_PROVIDER */
