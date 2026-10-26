"""Run actual probe/remove and ownership helpers with a permission-enforcing SCM stub."""
from pathlib import Path
import hashlib
import json
import subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel186')
source = (k / 'drivers/misc/fastrpc.c').read_text()
def extract(signature):
    begin = source.index(signature)
    start = source.index('{', begin)
    pos, depth = start + 1, 1
    while depth:
        depth += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[begin:pos]
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
typedef uint64_t u64;
typedef uint32_t u32;
typedef uint64_t phys_addr_t;
#define BIT(n) (1ULL << (n))
#define DMA_BIT_MASK(n) ((1ULL << (n)) - 1)
#define ADSP_DOMAIN_ID 0
#define MDSP_DOMAIN_ID 1
#define SDSP_DOMAIN_ID 2
#define CDSP_DOMAIN_ID 3
#define GDSP_DOMAIN_ID 4
#define FASTRPC_MAX_VMIDS 16
#define QCOM_SCM_VMID_HLOS 3
#define QCOM_SCM_PERM_RWX 7
#define EPROBE_DEFER 517
struct qcom_scm_vmperm { int vmid, perm; };
struct list_head { int empty; };
struct idr { int dummy; };
typedef int spinlock_t;
typedef int atomic_t;
struct fastrpc_device { struct { int active; } miscdev; };
struct fastrpc_buf { int dummy; struct list_head node; };
struct fastrpc_user { int dummy; struct list_head user; };
struct device { void *of_node, *data; u64 *dma_mask; };
struct rpmsg_device { struct device dev; };
struct resource { uint64_t start, end; };
struct fastrpc_soc_data { bool poll_mode_supported; };
struct fastrpc_channel_ctx {
    int vmcount, domain_id, refcount; struct qcom_scm_vmperm vmperms[16];
    struct fastrpc_device *fdevice, *secure_fdevice; bool secure, poll_mode_supported, unsigned_support;
    const struct fastrpc_soc_data *soc_data; struct rpmsg_device *rpdev;
    u64 dma_mask, reserved_pool_perms; phys_addr_t reserved_pool_phys; size_t reserved_pool_size;
    atomic_t ctx_seq; struct list_head users, invoke_interrupted_mmaps;
    spinlock_t lock; struct idr ctx_idr; struct fastrpc_buf *remote_heap;
};
static const struct fastrpc_soc_data soc;
static const char *fastrpc_poll_supported_machines[] = {NULL};
static int domain, configured_vmcount=1, resource_error, alloc_error, scm_error_call, scm_error;
static int register_error, populate_error, scm_available=1;
static unsigned scm_calls, allocated, freed, active_misc, deregistered, depopulated, logged_errors, cases;
static u64 owner;
static const phys_addr_t pool_phys=0x100000;
static const size_t pool_size=0x4000;
static void *allocate(size_t n) { if (alloc_error) return NULL; allocated++; return calloc(1,n); }
static void kfree(void *p) { if (p) { freed++; free(p); } }
#define kzalloc_obj(x) allocate(sizeof(x))
#define spin_lock_irqsave(lock,flags) do { (void)(lock); (flags)=0; } while (0)
#define spin_unlock_irqrestore(lock,flags) do { (void)(lock); (void)(flags); } while (0)
#define spin_lock_init(lock) (*(lock)=0)
#define INIT_LIST_HEAD(head) ((head)->empty=1)
#define list_for_each_entry(pos,head,member) for ((void)(head), (pos)=NULL; (pos)!=NULL; )
#define list_for_each_entry_safe(pos,n,head,member) for ((void)(head), (pos)=NULL,(n)=NULL; (pos)!=NULL; (pos)=(n))
static void list_del(struct list_head *p) { (void)p; }
static void idr_init(struct idr *p) { p->dummy=0; }
static void kref_init(int *p) { *p=1; }
static void atomic_set(atomic_t *p,int n) { *p=n; }
static size_t resource_size(const struct resource *r) { return r->end-r->start+1; }
static int of_reserved_mem_region_to_resource(void *node,int i,struct resource *r)
{ (void)node; assert(i==0); if (resource_error) return resource_error;
  r->start=pool_phys; r->end=pool_phys+pool_size-1; return 0; }
static int qcom_scm_assign_mem(phys_addr_t phys,size_t size,u64 *src,
    const struct qcom_scm_vmperm *dest,int count)
{ scm_calls++; assert(phys==pool_phys && size==pool_size && count>0);
  if (scm_error_call==(int)scm_calls) return scm_error;
  if (*src!=owner) return -EINVAL;
  u64 mask=0; for(int i=0;i<count;i++) { assert(dest[i].perm==7); mask|=BIT(dest[i].vmid); }
  owner=mask; *src=mask; return 0; }
static void dev_err(struct device *dev,const char *fmt,int n) { (void)dev;(void)fmt;assert(n<0);logged_errors++; }
static void dev_info(struct device *dev,const char *fmt,...) { (void)dev;(void)fmt; }
static const struct fastrpc_soc_data *device_get_match_data(struct device *dev) { (void)dev;return &soc; }
static int of_property_read_string(void *node,const char *key,const char **value)
{ (void)node;assert(!strcmp(key,"label")); *value="test-domain";return 0; }
static int fastrpc_get_domain_id(const char *label) { (void)label;return domain; }
static int of_reserved_mem_device_init_by_idx(struct device *dev,void *node,int index)
{ (void)dev;(void)node;assert(index==0);return resource_error; }
static int of_property_read_variable_u32_array(void *node,const char *key,unsigned *p,int min,int max)
{ (void)node;assert(!strcmp(key,"qcom,vmids") && min==0 && max==16);
  for(int i=0;i<configured_vmcount;i++) { p[i]=(unsigned)(5+i); }
  return configured_vmcount; }
static int qcom_scm_is_available(void) { return scm_available; }
static bool of_property_read_bool(void *node,const char *key) { (void)node;(void)key;return false; }
static bool of_machine_get_match(const char **names) { (void)names;return false; }
static int fastrpc_device_register(struct device *dev,struct fastrpc_channel_ctx *ctx,bool secure,const char *label)
{ (void)dev;(void)label; if(register_error) return register_error;
  struct fastrpc_device *p=allocate(sizeof(*p)); assert(p); p->miscdev.active=1;active_misc++;
  if(secure) ctx->secure_fdevice=p; else ctx->fdevice=p;return 0; }
static void misc_deregister(void *misc) { struct fastrpc_device *p=misc;assert(p->miscdev.active);
  p->miscdev.active=0;active_misc--;deregistered++;kfree(p); }
static void dma_set_mask_and_coherent(struct device *dev,u64 mask) { (void)dev;assert(mask==0xffffffff); }
static void dev_set_drvdata(struct device *dev,void *data) { dev->data=data; }
static void *dev_get_drvdata(struct device *dev) { return dev->data; }
static int of_platform_populate(void *node,void *a,void *b,struct device *dev)
{ (void)node;(void)a;(void)b;(void)dev;return populate_error; }
static void of_platform_depopulate(struct device *dev) { (void)dev;depopulated++; }
static void fastrpc_notify_users(struct fastrpc_user *user) { (void)user; }
static void fastrpc_buf_free(struct fastrpc_buf *buf) { (void)buf;assert(false); }
static void fastrpc_channel_ctx_put(struct fastrpc_channel_ctx *ctx) { kfree(ctx); }
'''
functions = '\n\n'.join(extract(x) for x in ['static int fastrpc_assign_reserved_pool(',
    'static int fastrpc_unassign_reserved_pool(', 'static int fastrpc_rpmsg_probe(', 'static void fastrpc_rpmsg_remove('])
tests = r'''
static void reset(void) {
    assert(allocated==freed && active_misc==0);
    owner=BIT(QCOM_SCM_VMID_HLOS);domain=SDSP_DOMAIN_ID;configured_vmcount=1;
    resource_error=alloc_error=scm_error_call=scm_error=register_error=populate_error=0;
    scm_available=1;scm_calls=deregistered=depopulated=logged_errors=0;
}
static void roundtrip(void) {
    struct rpmsg_device dev={0};assert(fastrpc_rpmsg_probe(&dev)==0);
    struct fastrpc_channel_ctx *ctx=dev.dev.data;
    assert(ctx->reserved_pool_size==pool_size && ctx->reserved_pool_perms==owner && owner==BIT(5));
    fastrpc_rpmsg_remove(&dev);assert(owner==BIT(3) && active_misc==0);cases++;
}
int main(void) {
    reset();for(int i=0;i<256;i++) roundtrip();assert(scm_calls==512);
    for(int n=1;n<=8;n++) { reset();configured_vmcount=n;struct rpmsg_device dev={0};
        assert(fastrpc_rpmsg_probe(&dev)==0);u64 expected=0;
        for(int i=0;i<n;i++) { expected|=BIT(5+i); }
        assert(owner==expected);
        fastrpc_rpmsg_remove(&dev);assert(owner==BIT(3));cases++; }
    for(int error=-1;error>=-16;error--) {
        reset();register_error=error;struct rpmsg_device dev={0};
        assert(fastrpc_rpmsg_probe(&dev)==error && owner==BIT(3) && scm_calls==2);cases++;
        reset();populate_error=error;dev=(struct rpmsg_device){0};
        assert(fastrpc_rpmsg_probe(&dev)==error && owner==BIT(3) && scm_calls==2 && active_misc==0);cases++;
        reset();scm_error_call=1;scm_error=error;dev=(struct rpmsg_device){0};
        assert(fastrpc_rpmsg_probe(&dev)==error && owner==BIT(3) && scm_calls==1);cases++;
        reset();struct fastrpc_channel_ctx ctx={.vmcount=1,.vmperms={{5,7}}};struct device d={0};
        assert(fastrpc_assign_reserved_pool(&d,&ctx)==0);scm_error_call=2;scm_error=error;
        assert(fastrpc_unassign_reserved_pool(&d,&ctx)==error);
        assert(owner==BIT(5) && ctx.reserved_pool_size==pool_size && ctx.reserved_pool_perms==BIT(5) && logged_errors==1);
        scm_error_call=0;assert(fastrpc_unassign_reserved_pool(&d,&ctx)==0 && owner==BIT(3));
        assert(fastrpc_unassign_reserved_pool(&d,&ctx)==0 && scm_calls==3);cases++;
    }
    reset();configured_vmcount=0;struct rpmsg_device dev={0};
    assert(fastrpc_rpmsg_probe(&dev)==0 && scm_calls==0);fastrpc_rpmsg_remove(&dev);assert(scm_calls==0);cases++;
    reset();resource_error=-ENOENT;dev=(struct rpmsg_device){0};
    assert(fastrpc_rpmsg_probe(&dev)==0 && scm_calls==0);fastrpc_rpmsg_remove(&dev);cases++;
    for(int d=0;d<=4;d++) if(d!=SDSP_DOMAIN_ID) { reset();domain=d;dev=(struct rpmsg_device){0};
        assert(fastrpc_rpmsg_probe(&dev)==0 && scm_calls==0);fastrpc_rpmsg_remove(&dev);assert(owner==BIT(3));cases++; }
    reset();scm_available=0;dev=(struct rpmsg_device){0};assert(fastrpc_rpmsg_probe(&dev)==-EPROBE_DEFER && scm_calls==0);cases++;
    reset();alloc_error=1;dev=(struct rpmsg_device){0};assert(fastrpc_rpmsg_probe(&dev)==-ENOMEM && scm_calls==0);cases++;
    reset();domain=-1;dev=(struct rpmsg_device){0};assert(fastrpc_rpmsg_probe(&dev)==-EINVAL && scm_calls==0);cases++;
    reset();printf("PASS cases=%u allocations=%u frees=%u\n",cases,allocated,freed);return 0;
}
'''
path = private / 'actual-fastrpc-pool-test-private.c'
path.write_text(prefix + '\n' + functions + '\n' + tests)
binary = private / 'actual-fastrpc-pool-test-private'
compile_args = ['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
    '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
p = subprocess.run([*compile_args, str(path), '-o', str(binary)], capture_output=True)
(private / 'fastrpc-host-build-r2-private.log').write_bytes(p.stdout + p.stderr)
if p.returncode:
    print(p.stderr.decode())
    raise SystemExit(p.returncode)
p = subprocess.run([str(binary)], capture_output=True)
(private / 'fastrpc-host-test-private.log').write_bytes(p.stdout + p.stderr)
assert p.returncode == 0, p.stderr.decode(errors='replace')
report = dict(actual_probe_remove_and_helpers_extracted=True, permission_enforcing_scm_stub=True,
    asan_ubsan_passed=True, scenarios=p.stdout.decode().strip(), source_sha256=hashlib.sha256(source.encode()).hexdigest(),
    repeated_probe_remove_and_probe_unwind_checked=True, reclaim_failure_preserves_metadata=True,
    unrelated_domains_and_missing_vmids_checked=True, hardware_verified=False)
(ref / 'fastrpc-host-tests-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
