/* Compile exact extracted owner gate/join functions; run a real pthread join. */
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#define READ_ONCE(x) __atomic_load_n(&(x),__ATOMIC_ACQUIRE)
#define WRITE_ONCE(x,v) __atomic_store_n(&(x),(v),__ATOMIC_RELEASE)
#define EXPORT_SYMBOL_GPL(x)
#define DEFINE_MUTEX(n) pthread_mutex_t n=PTHREAD_MUTEX_INITIALIZER
#define mutex_lock(m) pthread_mutex_lock(m)
#define mutex_unlock(m) pthread_mutex_unlock(m)
#define spin_lock_irqsave(m,f) do {(f)=0;pthread_mutex_lock(m);}while(0)
#define spin_unlock_irqrestore(m,f) do {(void)(f);pthread_mutex_unlock(m);}while(0)
#define DWC3_APSD_PD 32
#define SAMURAI_APSD_DETACHED 0
#define system_wq NULL
#define dev_err(...) ((void)0)
struct regmap { int unused; };
struct device_node { struct device_node *phandle; bool typec; };
struct device { struct device *parent; struct device_node *of_node; struct regmap *map; int refs; };
struct dwc3 { struct device *dev; };
struct delayed_work { int unused; };
struct samurai_apsd_owner {
	pthread_mutex_t lock;
	bool abort,quarantined,registered,retiring;
	unsigned int blocked;
	struct delayed_work work;
	struct { int phase,attempted,epoch; } once;
	struct dwc3 *dwc;
};
static DEFINE_MUTEX(owner_registry);
static bool tcpm_fenced;
static struct device *tcpm_supplier,*bus_dev;
static struct samurai_apsd_owner *bound_owner;
static bool machine_ok=true;
static int restore_error, joins, restores, releases, queued, quarantines, node_puts;
static pthread_t worker;
static bool worker_live;
static atomic_int worker_started,worker_finished,worker_saw_fence;
static pthread_mutex_t input_lock=PTHREAD_MUTEX_INITIALIZER;
static struct regmap *dev_get_regmap(struct device *d,void *p) { return d ? d->map : NULL; }
static bool of_machine_is_compatible(const char *s) { return machine_ok; }
static bool of_device_is_compatible(struct device_node *n,const char *s) { return n && n->typec; }
static struct device_node *of_parse_phandle(struct device_node *n,const char *s,int index) { return n->phandle; }
static void of_node_put(struct device_node *n) { if(n)node_puts++; }
static struct device *get_device(struct device *d) { d->refs++;return d; }
static void put_device(struct device *d) { if(d)d->refs--; }
static void cancel_delayed_work_sync(struct delayed_work *w) {
	joins++;
	if(worker_live) {assert(!pthread_join(worker,NULL));worker_live=false;}
}
static void samurai_apsd_cancel(void *o,int epoch) {}
static int owner_restore(struct samurai_apsd_owner *o,bool retiring) { restores++;return restore_error; }
static void owner_pd_release(struct samurai_apsd_owner *o) { releases++; }
static void owner_quarantine(struct samurai_apsd_owner *o) { quarantines++;o->quarantined=true; }
static void mod_delayed_work(void *wq,struct delayed_work *w,unsigned long delay) { queued++; }
#include "owner-functions.inc"

static int cases;
#define CHECK(expr) do { cases++; if (!(expr)) { \
	fprintf(stderr, "line %d: %s\n", __LINE__, #expr); abort(); } } while (0)
static void *real_worker(void *arg)
{
	struct samurai_apsd_owner *o=arg;
	pthread_mutex_lock(&input_lock);
	atomic_store(&worker_started,1);
	while(!READ_ONCE(tcpm_fenced)) usleep(100);
	atomic_store(&worker_saw_fence,owner_aborted(o));
	usleep(1000);
	pthread_mutex_unlock(&input_lock);
	atomic_store(&worker_finished,1);
	return NULL;
}
int main(void)
{
	struct regmap map,other;
	struct device_node typec_node={.typec=true},dwc_node={.phandle=&typec_node},bad_node={.typec=true};
	struct device parent={.map=&map},bad_parent={.map=&map};
	struct device typec={.parent=&parent,.of_node=&typec_node,.refs=1};
	struct device source={.parent=&parent},dwcdev={.of_node=&dwc_node};
	struct dwc3 dwc={.dev=&dwcdev};
	struct samurai_apsd_owner owner={.lock=PTHREAD_MUTEX_INITIALIZER,.dwc=&dwc,.registered=true};

	CHECK(samurai_apsd_tcpm_quiesce(NULL,&map)==-EXDEV);
	machine_ok=false;
	CHECK(samurai_apsd_tcpm_quiesce(&typec,&map)==-EXDEV);machine_ok=true;
	CHECK(samurai_apsd_tcpm_quiesce(&typec,&other)==-EXDEV);
	bus_dev=&source;source.parent=&bad_parent;
	CHECK(samurai_apsd_tcpm_quiesce(&typec,&map)==-EXDEV);source.parent=&parent;
	bound_owner=&owner;dwc_node.phandle=&bad_node;
	CHECK(samurai_apsd_tcpm_quiesce(&typec,&map)==-EXDEV);dwc_node.phandle=NULL;
	CHECK(samurai_apsd_tcpm_quiesce(&typec,&map)==-EXDEV);dwc_node.phandle=&typec_node;
	CHECK(!tcpm_fenced && !joins && typec.refs==1);

	/* Simulate a live final-transfer worker holding input->lock. Joining
	 * under that same lock would deadlock this test and hit its timeout.
	 */
	CHECK(!pthread_create(&worker,NULL,real_worker,&owner));worker_live=true;
	while(!atomic_load(&worker_started))usleep(100);
	CHECK(samurai_apsd_tcpm_quiesce(&typec,&map)==0);
	CHECK(atomic_load(&worker_finished) && atomic_load(&worker_saw_fence));
	CHECK(tcpm_fenced && owner.blocked==DWC3_APSD_PD && owner.abort);
	CHECK(joins==1 && restores==1 && releases==1 && typec.refs==2);
	CHECK(samurai_apsd_tcpm_quiesce(&typec,&map)==-EBUSY && typec.refs==2);
	samurai_apsd_tcpm_release(&source);
	CHECK(typec.refs==2 && tcpm_supplier==&typec);
	samurai_apsd_tcpm_release(&typec);
	CHECK(typec.refs==1 && !tcpm_supplier && tcpm_fenced);
	/* Even unrelated resume paths clearing their local reason cannot
	 * queue or validate a new worker after the full-PD handoff.
	 */
	owner.blocked=0;owner.abort=false;
	owner_queue(&owner,0);
	CHECK(!queued && owner_aborted(&owner));
	bound_owner=NULL;bus_dev=NULL;
	CHECK(samurai_apsd_tcpm_quiesce(&typec,&map)==0 && typec.refs==2);
	samurai_apsd_tcpm_release(&typec);
	CHECK(typec.refs==1 && tcpm_fenced);
	bound_owner=&owner;restore_error=-EIO;
	CHECK(samurai_apsd_tcpm_quiesce(&typec,&map)==-EIO);
	CHECK(tcpm_fenced && !tcpm_supplier && typec.refs==1 && quarantines==1);
	CHECK(node_puts==3);
	printf("production owner: %d assertions; real worker/input-lock join passed\n",cases);
	return 0;
}
