/* Kernel API contract harness. The tested driver functions are extracted,
 * unmodified, from the locked baseline and candidate by test-fastrpc.py.
 * This models probe/open failures and endpoint draining, not DMA or SSR.
 */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint64_t u64;
typedef uint32_t u32;
typedef unsigned long dma_addr_t;
typedef struct { int value; } atomic_t;
#define ADSP_DOMAIN_ID 0
#define MDSP_DOMAIN_ID 1
#define SDSP_DOMAIN_ID 2
#define CDSP_DOMAIN_ID 3
#define GDSP_DOMAIN_ID 4
#define FASTRPC_MAX_SESSIONS 14
#define FASTRPC_MAX_VMIDS 16
#define FASTRPC_MAX_DSP_ATTRIBUTES 256
#define FASTRPC_DSP_PD_NOTIFY_CTX 0xABCDABCD
#define FASTRPC_CTXID_MASK 0xff00
#define FASTRPC_CTXID_SEQ_MASK 0xffffffffffff0000ULL
#define FIELD_GET(mask, value) (((value) & (mask)) >> __builtin_ctzll(mask))
#define QCOM_SCM_PERM_RWX 7
#define QCOM_SCM_VMID_HLOS 0
#define BIT(n) (1UL << (n))
#define DMA_BIT_MASK(n) ((1ULL << (n)) - 1)
#define MISC_DYNAMIC_MINOR 255
#define GFP_KERNEL 0
#define EPROBE_DEFER 517
#define container_of(p, t, m) ((t *)((char *)(p) - offsetof(t, m)))
#define dev_info(...) ((void)0)
#define dev_err(...) ((void)0)
#define dev_dbg(...) ((void)0)

struct kref { int count; };
struct list_head { struct list_head *next, *prev; };
typedef struct { pthread_mutex_t mutex; bool initialized, held; } spinlock_t;
struct mutex { bool initialized; };
struct idr { bool initialized; };
struct qcom_scm_vmperm { u32 vmid, perm; };
struct devres { void (*action)(void *); void *data; };
struct device {
	void *driver_data;
	void *of_node;
	u64 *dma_mask, coherent_dma_mask;
	struct devres res[16];
	int nres;
};
struct rpmsg_device { struct device dev; };
struct inode { int dummy; };
struct file { void *private_data; };
struct miscdevice { int minor; const void *fops; char *name; bool registered; };
struct resource { u64 start, size; };
struct fastrpc_buf;
struct fastrpc_map;
struct fastrpc_invoke_ctx { u64 ctxid; int retval; bool is_work_done; int work, put_work; };
struct fastrpc_invoke_rsp { u64 ctx; int retval; };

enum scenario { SINGLE, DUAL, FAIL_FIRST_MISC, FAIL_SECOND_MISC, PARTIAL_CHILD,
	NO_SESSION, FAIL_ACTION, FAIL_DMA, FAIL_SCM, HELD_CALLBACK, FAIL_ALLOC };
static enum scenario scenario;
static int allocated, registered_nodes, register_calls, early_opens, children;
static int owner_releases, callback_result;
static struct rpmsg_device rpdev;
static pthread_mutex_t gate_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t gate_cond = PTHREAD_COND_INITIALIZER;
static bool pause_callback, callback_captured, resume_callback;
static pthread_t callback_thread;
static void *captured_channel;
static int fastrpc_device_open(struct inode *, struct file *);
static int fastrpc_rpmsg_callback(struct rpmsg_device *, void *, int, void *, u32);

static void *allocate(size_t size)
{
	void *p = calloc(1, size);
	assert(p);
	allocated++;
	return p;
}
static void *kzalloc_test(size_t size)
{
	if (scenario == FAIL_ALLOC && allocated == 0)
		return NULL;
	return allocate(size);
}
#define kzalloc_obj(obj) kzalloc_test(sizeof(obj))
static void kfree(void *p) { if (p) { assert(allocated > 0); allocated--; free(p); } }
static void kref_init(struct kref *ref) { ref->count = 1; }
static void kref_get(struct kref *ref)
{
	if (ref->count <= 0) {
		fputs("CONTRACT: get of uninitialized channel kref\n", stderr);
		exit(86);
	}
	ref->count++;
}
static void kref_put(struct kref *ref, void (*release)(struct kref *))
{
	assert(ref->count > 0);
	if (!--ref->count)
		release(ref);
}
static void atomic_set(atomic_t *v, int n) { v->value = n; }
static void spin_lock_init(spinlock_t *lock)
{
	assert(!lock->initialized);
	assert(pthread_mutex_init(&lock->mutex, NULL) == 0);
	lock->initialized = true;
}
static void lock_spin(spinlock_t *lock)
{
	assert(lock->initialized);
	assert(pthread_mutex_lock(&lock->mutex) == 0);
	assert(!lock->held);
	lock->held = true;
}
static void unlock_spin(spinlock_t *lock)
{
	assert(lock->initialized && lock->held);
	lock->held = false;
	assert(pthread_mutex_unlock(&lock->mutex) == 0);
}
#define spin_lock_irqsave(lock, flags) do { (flags) = 0; lock_spin(lock); } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(flags); unlock_spin(lock); } while (0)
#define lockdep_assert_held(lock) assert((lock)->held)
static void mutex_init(struct mutex *m) { assert(!m->initialized); m->initialized = true; }
static void mutex_destroy(struct mutex *m) { assert(m->initialized); m->initialized = false; }
static void INIT_LIST_HEAD(struct list_head *h) { h->next = h->prev = h; }
static void list_add_tail(struct list_head *n, struct list_head *h)
{
	assert(h->next && h->prev);
	n->prev = h->prev; n->next = h; h->prev->next = n; h->prev = n;
}
static void list_del(struct list_head *n) { n->prev->next = n->next; n->next->prev = n->prev; }
static void idr_init(struct idr *i) { i->initialized = true; }
static void idr_destroy(struct idr *i) { assert(i->initialized); i->initialized = false; owner_releases++; }
static void *idr_find(struct idr *i, unsigned long n) { assert(i->initialized); return NULL; }
static void complete(int *p) { *p = 1; }
static void schedule_work(int *p) { *p = 1; }
#define smp_store_release(p, value) __atomic_store_n(p, value, __ATOMIC_RELEASE)
static void *load_channel(void **p)
{
	void *v = __atomic_load_n(p, __ATOMIC_ACQUIRE);
	if (pause_callback) {
		pthread_mutex_lock(&gate_mutex);
		captured_channel = v;
		callback_captured = true;
		pthread_cond_broadcast(&gate_cond);
		while (!resume_callback)
			pthread_cond_wait(&gate_cond, &gate_mutex);
		pthread_mutex_unlock(&gate_mutex);
	}
	return v;
}
#define smp_load_acquire(p) load_channel(p)
static void dev_set_drvdata(struct device *d, void *v) { d->driver_data = v; }
static void *dev_get_drvdata(struct device *d) { return d->driver_data; }
static int devm_add_action_or_reset(struct device *d, void (*action)(void *), void *data)
{
	if (scenario == FAIL_ACTION) { action(data); return -ENOMEM; }
	assert(d->nres < 16);
	d->res[d->nres++] = (struct devres){ action, data };
	return 0;
}
static void *devm_kzalloc(struct device *d, size_t n, int flags)
{
	void *p = allocate(n);
	assert(d->nres < 16);
	d->res[d->nres++] = (struct devres){ kfree, p };
	return p;
}
static char *devm_kasprintf(struct device *d, int flags, const char *fmt,
			 const char *domain, const char *suffix)
{
	char *p = devm_kzalloc(d, 64, flags);
	assert(snprintf(p, 64, fmt, domain, suffix) < 64);
	return p;
}
static void devres_release_all(struct device *d)
{
	assert(!registered_nodes && !children);
	while (d->nres) {
		struct devres *r = &d->res[--d->nres];
		r->action(r->data);
	}
}

/* @DRIVER_STRUCTS@ */

static const int fastrpc_fops;
static const int fastrpc_poll_supported_machines[] = { 0 };
static const struct fastrpc_soc_data default_soc_data = {
	.sid_pos = 32, .dma_addr_bits_cdsp = 32, .dma_addr_bits_default = 32,
};
static void *miscdev_to_fdevice(struct miscdevice *m)
{
	return container_of(m, struct fastrpc_device, miscdev);
}
static const struct fastrpc_soc_data *device_get_match_data(struct device *d) { return &default_soc_data; }
static int of_property_read_string(void *node, const char *name, const char **v)
{
	*v = scenario == DUAL || scenario == FAIL_SECOND_MISC ? "cdsp" :
		scenario == FAIL_SCM ? "sdsp" : "adsp";
	return 0;
}
static int of_reserved_mem_device_init_by_idx(struct device *d, void *n, int i) { return 0; }
static int of_property_read_variable_u32_array(void *n, const char *s, unsigned int *v, int min, int max)
{
	*v = 3;
	return scenario == FAIL_SCM ? 1 : 0;
}
static bool qcom_scm_is_available(void) { return true; }
static int of_reserved_mem_region_to_resource(void *n, int i, struct resource *r)
{
	r->start = 0; r->size = 4096; return 0;
}
static u64 resource_size(struct resource *r) { return r->size; }
static int qcom_scm_assign_mem(u64 start, u64 size, u64 *src, struct qcom_scm_vmperm *p, int n) { return -EIO; }
static bool of_property_read_bool(void *node, const char *name) { return false; }
static bool of_machine_get_match(const void *table) { return false; }
static int dma_set_mask_and_coherent(struct device *d, u64 mask)
{
	*d->dma_mask = mask; d->coherent_dma_mask = mask;
	return scenario == FAIL_DMA ? -EIO : 0;
}
static int misc_register(struct miscdevice *m)
{
	register_calls++;
	if (scenario == FAIL_FIRST_MISC || (scenario == FAIL_SECOND_MISC && register_calls == 2))
		return -EIO;
	m->registered = true;
	registered_nodes++;
	struct file f = { .private_data = m };
	int err = fastrpc_device_open(NULL, &f);
	assert(err == -ENODEV);
	assert(f.private_data == m);
	early_opens++;
	return 0;
}
static void misc_deregister(struct miscdevice *m)
{
	assert(m->registered);
	m->registered = false;
	registered_nodes--;
}
static void *callback_worker(void *unused)
{
	struct fastrpc_invoke_rsp rsp = { .ctx = 0x100 };
	callback_result = fastrpc_rpmsg_callback(&rpdev, &rsp, sizeof(rsp), NULL, 0);
	return NULL;
}
static int of_platform_populate(void *node, void *a, void *b, struct device *d)
{
	struct fastrpc_channel_ctx *c = dev_get_drvdata(d);
	assert(c && c->lock.initialized && c->ctx_idr.initialized && c->refcount.count == 1);
	assert(c->soc_data && c->rpdev && c->domain_id >= 0);
	children++;
	if (scenario != NO_SESSION) {
		c->sesscount = scenario == DUAL ? 2 : 1;
		for (int i = 0; i < c->sesscount; i++) c->session[i].valid = true;
	}
	if (scenario == HELD_CALLBACK) {
		pause_callback = true;
		assert(pthread_create(&callback_thread, NULL, callback_worker, NULL) == 0);
		pthread_mutex_lock(&gate_mutex);
		while (!callback_captured) pthread_cond_wait(&gate_cond, &gate_mutex);
		pthread_mutex_unlock(&gate_mutex);
		return -EIO;
	}
	return scenario == PARTIAL_CHILD ? -EIO : 0;
}
static void of_platform_depopulate(struct device *d)
{
	assert(dev_get_drvdata(d));
	assert(children == 1);
	children = 0;
}

/* @DRIVER_FUNCTIONS@ */

static void close_user(struct file *file)
{
	struct fastrpc_user *fl = file->private_data;
	struct fastrpc_channel_ctx *cctx = fl->cctx;
	unsigned long flags;
	assert(fl->refcount.count == 1 && cctx->refcount.count >= 2);
	spin_lock_irqsave(&cctx->lock, flags);
	list_del(&fl->user);
	spin_unlock_irqrestore(&cctx->lock, flags);
	fastrpc_session_free(cctx, fl->sctx);
	mutex_destroy(&fl->mutex);
	kfree(fl);
	fastrpc_channel_ctx_put(cctx);
	file->private_data = NULL;
}
#ifdef BASELINE
int main(int argc, char **argv)
{
	scenario = SINGLE;
	u64 mask = 0xa5a5;
	rpdev.dev.dma_mask = &mask;
	/* The first published node invokes the actual original open function. */
	fastrpc_rpmsg_probe(&rpdev);
	fputs("negative control unexpectedly survived early open\n", stderr);
	return 87;
}
#else
int main(int argc, char **argv)
{
	assert(argc == 2);
	scenario = atoi(argv[1]);
	u64 original_mask = 0xa5a5;
	rpdev.dev.dma_mask = &original_mask;
	rpdev.dev.coherent_dma_mask = 0x1234;
	/* Endpoint exists before probe, but no channel has been published. */
	struct fastrpc_invoke_rsp rsp = { .ctx = 0x100 };
	assert(fastrpc_rpmsg_callback(&rpdev, &rsp, sizeof(rsp), NULL, 0) == -ENODEV);
	int err = fastrpc_rpmsg_probe(&rpdev);
	if (scenario == SINGLE || scenario == DUAL || scenario == NO_SESSION) {
		assert(!err && children == 1 && registered_nodes == (scenario == DUAL ? 2 : 1));
		struct fastrpc_channel_ctx *c = dev_get_drvdata(&rpdev.dev);
		assert(c && c->refcount.count == 1);
		struct miscdevice *m = c->secure_fdevice ? &c->secure_fdevice->miscdev : &c->fdevice->miscdev;
		struct file a = { .private_data = m }, b = { .private_data = m }, extra = { .private_data = m };
		if (scenario == NO_SESSION) {
			assert(fastrpc_device_open(NULL, &a) == -EBUSY && a.private_data == m);
			assert(c->refcount.count == 1);
		} else {
			assert(!fastrpc_device_open(NULL, &a));
			assert(c->refcount.count == 2 && c->session[0].used);
			if (scenario == DUAL) {
				b.private_data = &c->fdevice->miscdev;
				assert(!fastrpc_device_open(NULL, &b));
				assert(c->refcount.count == 3 && c->session[1].used);
			}
			assert(fastrpc_device_open(NULL, &extra) == -EBUSY && extra.private_data == m);
			close_user(&a);
			if (scenario == DUAL) close_user(&b);
			assert(c->refcount.count == 1 && c->users.next == &c->users);
		}
		assert(fastrpc_rpmsg_callback(&rpdev, &rsp, sizeof(rsp), NULL, 0) == -ENOENT);
		/* Admission after teardown starts: independent of remaining sessions. */
		unsigned long flags;
		spin_lock_irqsave(&c->lock, flags);
		c->ready = false; c->rpdev = NULL;
		spin_unlock_irqrestore(&c->lock, flags);
		extra.private_data = m;
		assert(fastrpc_device_open(NULL, &extra) == -ENODEV && extra.private_data == m);
		assert(fastrpc_rpmsg_callback(&rpdev, &rsp, sizeof(rsp), NULL, 0) == -ENODEV);
		if (c->fdevice) misc_deregister(&c->fdevice->miscdev);
		if (c->secure_fdevice) misc_deregister(&c->secure_fdevice->miscdev);
		of_platform_depopulate(&rpdev.dev);
		smp_store_release(&rpdev.dev.driver_data, NULL);
	} else {
		assert(err < 0 && !registered_nodes && !children);
		assert(!rpdev.dev.driver_data);
		if (scenario == HELD_CALLBACK) {
			struct fastrpc_channel_ctx *c = captured_channel;
			assert(c && c->refcount.count == 1 && owner_releases == 0);
			/* RPMsg endpoint destruction waits for the already entered callback. */
			pthread_mutex_lock(&gate_mutex);
			resume_callback = true;
			pthread_cond_broadcast(&gate_cond);
			pthread_mutex_unlock(&gate_mutex);
			assert(pthread_join(callback_thread, NULL) == 0);
			pause_callback = false;
			assert(callback_result == -ENODEV && owner_releases == 0);
		}
	}
	/* Driver core releases parent devres only after endpoint destruction. */
	devres_release_all(&rpdev.dev);
	assert(rpdev.dev.dma_mask == &original_mask && original_mask == 0xa5a5);
	assert(rpdev.dev.coherent_dma_mask == 0x1234 && !rpdev.dev.driver_data);
	assert(!allocated && owner_releases == (scenario == FAIL_ALLOC ? 0 : 1));
	assert(register_calls <= 2);
	printf("case=%d PASS early_opens=%d owner_releases=%d\n", scenario, early_opens, owner_releases);
	return 0;
}
#endif
