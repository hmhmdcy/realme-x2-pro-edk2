/* Actual newly added driver functions; OS/IRQ/workqueue boundary only is fake. */
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdatomic.h>
#define EPROBE_DEFER 517
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define IRQF_ONESHOT 0x2000UL
#define IRQ_HANDLED 1
typedef int irqreturn_t;
struct device { int dummy; };
struct platform_device { struct device dev; void *driver_data; };
struct delayed_work { int dummy; };
struct mutex { pthread_mutex_t actual; };
struct samurai_usb_input { struct mutex lock; struct delayed_work work; bool paused, udc_valid; };
static void *system_wq=(void *)1;
static int gets[2], get_count, request_count, fail_at, fail_errno;
static unsigned int queues, cancels;
static unsigned long delay_seen;
static struct samurai_usb_input *expected;
static const char *names[] = {"usbin-plugin","usbin-src-change"};
static bool invoke_requested_irq, join_active_worker;
static pthread_t active_worker;
static pthread_mutex_t worker_gate=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t worker_cond=PTHREAD_COND_INITIALIZER;
static bool worker_go;
static atomic_int worker_ready, worker_finished;

static void mutex_lock(struct mutex *m) { assert(pthread_mutex_lock(&m->actual)==0); }
static void mutex_unlock(struct mutex *m) { assert(pthread_mutex_unlock(&m->actual)==0); }
static void *platform_get_drvdata(struct platform_device *p) { return p->driver_data; }
static int platform_get_irq_byname_optional(struct platform_device *p, const char *name)
{ assert(p); assert(get_count<2); assert(!strcmp(name,names[get_count])); return gets[get_count++]; }
static int mod_delayed_work(void *wq, struct delayed_work *w, unsigned long delay)
{ assert(wq==system_wq && w==&expected->work); queues++;delay_seen=delay;return 0; }
static irqreturn_t samurai_usb_event(int irq, void *data);
static int devm_request_threaded_irq(struct device *d,int irq,void *primary,
                                    irqreturn_t (*thread)(int,void *),unsigned long flags,
                                    const char *name,void *data)
{
    int index=request_count++;
    assert(d && index<2 && irq==gets[index] && !primary);
    assert(thread==samurai_usb_event && flags==IRQF_ONESHOT);
    assert(!strcmp(name,names[index]) && data==expected);
    if(invoke_requested_irq) assert(thread(irq,data)==IRQ_HANDLED);
    return fail_at==index+1?fail_errno:0;
}
static void cancel_delayed_work_sync(struct delayed_work *work)
{
    assert(work==&expected->work);
    /* The real stop must unlock before cancel/join of a worker needing lock. */
    assert(pthread_mutex_trylock(&expected->lock.actual)==0);
    assert(expected->paused && !expected->udc_valid);
    pthread_mutex_unlock(&expected->lock.actual);
    cancels++;
    if(join_active_worker) {
        pthread_mutex_lock(&worker_gate);worker_go=true;
        pthread_cond_signal(&worker_cond);pthread_mutex_unlock(&worker_gate);
        assert(pthread_join(active_worker,NULL)==0);
        assert(atomic_load(&worker_finished)==1);
    }
    /* A real late threaded IRQ sees paused and cannot requeue after stop. */
    unsigned int before=queues;
    assert(samurai_usb_event(41,expected)==IRQ_HANDLED);
    assert(queues==before);
}

#include "actual-events-and-stop.inc"

static void reset(struct samurai_usb_input *input)
{
    gets[0]=41;gets[1]=43;get_count=request_count=fail_at=0;fail_errno=-EBUSY;
    queues=cancels=0;delay_seen=999;expected=input;
    invoke_requested_irq=true;join_active_worker=false;
    input->paused=true;input->udc_valid=true;
}
static void *blocked_worker(void *unused)
{
    (void)unused;
    pthread_mutex_lock(&worker_gate);atomic_store(&worker_ready,1);
    while(!worker_go)pthread_cond_wait(&worker_cond,&worker_gate);
    pthread_mutex_unlock(&worker_gate);
    mutex_lock(&expected->lock);
    assert(expected->paused && !expected->udc_valid);
    mutex_unlock(&expected->lock);atomic_store(&worker_finished,1);
    return NULL;
}

int main(void)
{
    struct platform_device p={0};struct samurai_usb_input input={0};
    assert(pthread_mutex_init(&input.lock.actual,NULL)==0);
    unsigned int cases=0;
#define CASE() (++cases)
    reset(&input);gets[0]=gets[1]=-ENXIO;
    assert(!samurai_usb_request_events(&p,&input) && !request_count);CASE();
    reset(&input);gets[0]=-ENODEV;gets[1]=-ENXIO;
    assert(!samurai_usb_request_events(&p,&input) && !request_count);CASE();
    reset(&input);assert(!samurai_usb_request_events(&p,&input));
    assert(get_count==2 && request_count==2 && queues==0);CASE();
    reset(&input);gets[1]=-ENXIO;
    assert(samurai_usb_request_events(&p,&input)==-ENXIO && request_count==0);CASE();
    reset(&input);gets[1]=gets[0];
    assert(samurai_usb_request_events(&p,&input)==-EINVAL && request_count==0);CASE();
    reset(&input);gets[0]=-EPROBE_DEFER;
    assert(samurai_usb_request_events(&p,&input)==-EPROBE_DEFER && get_count==1 && request_count==0);CASE();
    reset(&input);gets[1]=-EPROBE_DEFER;
    assert(samurai_usb_request_events(&p,&input)==-EPROBE_DEFER && get_count==2 && request_count==0);CASE();
    reset(&input);fail_at=1;
    assert(samurai_usb_request_events(&p,&input)==-EBUSY && request_count==1 && !queues);CASE();
    reset(&input);fail_at=2;fail_errno=-EIO;
    assert(samurai_usb_request_events(&p,&input)==-EIO && request_count==2 && !queues);CASE();
    reset(&input);gets[0]=0;
    assert(samurai_usb_request_events(&p,&input)==-EINVAL && !request_count);CASE();
    reset(&input);gets[0]=-EINVAL;
    assert(samurai_usb_request_events(&p,&input)==-EINVAL && !request_count);CASE();
    reset(&input);input.paused=false;
    assert(samurai_usb_event(41,&input)==IRQ_HANDLED && queues==1 && !delay_seen);CASE();
    reset(&input);assert(samurai_usb_event(43,&input)==IRQ_HANDLED && !queues);CASE();
    reset(&input);input.paused=false;samurai_usb_stop(&input);
    assert(input.paused && !input.udc_valid && cancels==1 && !queues);
    samurai_usb_event(43,&input);assert(!queues);CASE();
    reset(&input);input.paused=false;worker_go=false;
    atomic_store(&worker_ready,0);atomic_store(&worker_finished,0);
    assert(!pthread_create(&active_worker,NULL,blocked_worker,NULL));
    while(!atomic_load(&worker_ready)) { }
    join_active_worker=true;samurai_usb_stop(&input);
    assert(cancels==1 && !queues && atomic_load(&worker_finished)==1);CASE();
    reset(&input);input.paused=false;p.driver_data=&input;
    samurai_usb_shutdown(&p);
    assert(input.paused && !input.udc_valid && cancels==1 && !queues);CASE();
    assert(!pthread_mutex_destroy(&input.lock.actual));
    printf("{\"passed\":true,\"actual_function_cases\":%u,\"pthread_lock_outside_cancel_and_join\":true}\n",cases);
    return 0;
}
