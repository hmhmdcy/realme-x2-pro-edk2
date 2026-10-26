"""Exercise exact candidate holder C with explicit sequential resource stubs."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('holder_check_storage449', HERE.parents[1] / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
SHARED = storage.mount.mounted_build()
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel462/r2')
text = (PRIVATE / 'candidate/drivers/media/i2c/imx471.c').read_text()
start = text.index('/* Routed resources outlive'); end = text.index('static int imx471_power_off(', start)
body = text[start:end]
preamble = r'''
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
#define IMX471_EXT_CLK 19200000
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define BIT(n) (1UL<<(n))
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
enum imx471_supply { IMX471_VANA, IMX471_VDIG, IMX471_VIF };
static const char * const imx471_supply_name[] = { "vana", "vdig", "vif" };
struct mutex { bool initialized, held; };
struct list_head { struct list_head *next, *prev; };
struct module { unsigned int refs; bool going; };
struct mux_state { unsigned int handles; bool selected; };
struct reset_control { unsigned int handles; bool acquired; };
struct clk { unsigned int handles, enabled; };
struct regulator { unsigned int handles, enabled; };
struct device { unsigned int refs; struct reset_control reset; struct clk clock; struct regulator rails[3]; };
#define LIST_HEAD(name) struct list_head name={&(name),&(name)}
#define DEFINE_MUTEX(name) struct mutex name={true,false}
#define list_for_each_entry(pos,head,member) \
 for(pos=container_of((head)->next,__typeof__(*pos),member); &(pos)->member!=(head); pos=container_of((pos)->member.next,__typeof__(*pos),member))
static struct module module_state;
static struct mux_state mux;
#define THIS_MODULE (&module_state)
#define dev_err(...) ((void)0)
static unsigned int handles_put, allocations, frees, live_allocations, operations, test_cases;
static int acquisition_at, acquisition_step, power_at, power_step, off_at, off_step;
static bool fail_alloc;
static struct device devices[128];
static unsigned int device_count;
static void INIT_LIST_HEAD(struct list_head *h) { h->next=h->prev=h; }
static bool list_empty(const struct list_head *h) { return h->next==h; }
static void list_add_tail(struct list_head *e,struct list_head *h) { e->prev=h->prev;e->next=h;h->prev->next=e;h->prev=e; }
static void list_del(struct list_head *e) { e->prev->next=e->next;e->next->prev=e->prev;e->next=e->prev=NULL; }
static void mutex_init(struct mutex *m) { m->initialized=true;m->held=false; }
static void mutex_lock(struct mutex *m) { assert(m->initialized&&!m->held);m->held=true; }
static void mutex_unlock(struct mutex *m) { assert(m->initialized&&m->held);m->held=false; }
static void mutex_destroy(struct mutex *m) { assert(m->initialized&&!m->held);m->initialized=false; }
static struct device *get_device(struct device *d) { assert(d->refs);d->refs++;return d; }
static void put_device(struct device *d) { assert(d->refs>1);d->refs--; }
static bool try_module_get(struct module *m) { if(m->going)return false;m->refs++;return true; }
static void module_put(struct module *m) { assert(m->refs);m->refs--; }
static void *kzalloc(size_t n,int flags) { if(fail_alloc)return NULL;void *p=calloc(1,n);assert(p);allocations++;live_allocations++;return p; }
static void kfree(void *p) { assert(p&&live_allocations);frees++;live_allocations--;free(p); }
static bool get_fail(void) { return ++acquisition_step==acquisition_at; }
static bool power_fail(void) { operations++;return ++power_step==power_at; }
static bool off_fail(void) { operations++;return ++off_step==off_at; }
static struct mux_state *mux_state_get(struct device *d,const char *name) {
 assert(!strcmp(name,"csi-route"));if(get_fail())return ERR_PTR(-EIO);mux.handles++;return &mux;
}
static void mux_state_put(struct mux_state *m) { assert(m==&mux&&m->handles);handles_put++;m->handles--; }
static int mux_state_try_select(struct mux_state *m) {
 assert(m==&mux&&m->handles&&module_state.refs);if(m->selected)return -EBUSY;if(power_fail())return -EIO;m->selected=true;return 0;
}
static int mux_state_deselect(struct mux_state *m) { assert(m==&mux&&m->selected);operations++;m->selected=false;return 0; }
static struct reset_control *reset_control_get_exclusive_released(struct device *d,const char *name) {
 assert(!name&&mux.selected);if(get_fail())return ERR_PTR(-EPROBE_DEFER);assert(!d->reset.handles);d->reset.handles++;return &d->reset;
}
static void reset_control_put(struct reset_control *r) { assert(r->handles==1&&!r->acquired);handles_put++;r->handles--; }
static int reset_control_acquire(struct reset_control *r) {
 assert(r->handles==1&&!r->acquired&&mux.selected&&module_state.refs);if(power_fail())return -EIO;r->acquired=true;return 0;
}
static int reset_control_assert(struct reset_control *r) { assert(r->handles&&r->acquired&&mux.selected);return off_at ? (off_fail()?-EIO:0) : (power_fail()?-EIO:0); }
static int reset_control_deassert(struct reset_control *r) { assert(r->handles&&r->acquired&&mux.selected);return power_fail()?-EIO:0; }
static void reset_control_release(struct reset_control *r) { assert(r->handles&&r->acquired);operations++;r->acquired=false; }
static struct clk *clk_get(struct device *d,const char *name) {
 assert(!name&&mux.selected);if(get_fail())return ERR_PTR(-EPROBE_DEFER);assert(!d->clock.handles);d->clock.handles++;return &d->clock;
}
static void clk_put(struct clk *c) { assert(c->handles==1&&!c->enabled);handles_put++;c->handles--; }
static int clk_set_rate(struct clk *c,unsigned long rate) { assert(c->handles==1&&mux.selected&&rate==IMX471_EXT_CLK);return power_fail()?-EIO:0; }
static int clk_prepare_enable(struct clk *c) { assert(c->handles==1&&!c->enabled&&mux.selected&&module_state.refs);if(power_fail())return -EIO;c->enabled++;return 0; }
static void clk_disable_unprepare(struct clk *c) { assert(c->handles==1&&c->enabled==1&&mux.selected);operations++;c->enabled--; }
static struct regulator *regulator_get(struct device *d,const char *name) {
 unsigned int i;for(i=0;i<3;i++)if(!strcmp(name,imx471_supply_name[i]))break;assert(i<3&&mux.selected);
 if(get_fail())return ERR_PTR(-EPROBE_DEFER);
 assert(!d->rails[i].handles);d->rails[i].handles++;return &d->rails[i];
}
static void regulator_put(struct regulator *r) { assert(r->handles==1&&!r->enabled);handles_put++;r->handles--; }
static int regulator_enable(struct regulator *r) {
 assert(r->handles==1&&!r->enabled&&mux.selected&&module_state.refs);if(power_fail())return -EIO;r->enabled++;return 0;
}
static int regulator_disable(struct regulator *r) { assert(r->handles==1&&r->enabled==1&&mux.selected);if(off_fail())return -EIO;r->enabled--;return 0; }
static void usleep_range(unsigned int a,unsigned int b) { assert(a<=b); }
'''
main = r'''
static struct device *fresh(void) {
 assert(device_count<ARRAY_SIZE(devices));struct device *d=&devices[device_count++];d->refs=1;
 acquisition_at=acquisition_step=power_at=power_step=off_at=off_step=0;fail_alloc=false;module_state.going=false;return d;
}
static void clean(struct device *d) {
 assert(d->refs==1&&!d->reset.handles&&!d->reset.acquired&&!d->clock.handles&&!d->clock.enabled);
 for(unsigned int i=0;i<3;i++)assert(!d->rails[i].handles&&!d->rails[i].enabled);
 test_cases++;
}
static void reset_faults(void) { acquisition_at=acquisition_step=power_at=power_step=off_at=off_step=0; }
int main(void) {
 struct device *d=fresh();struct imx471_shared *h=imx471_shared_create(d);assert(!IS_ERR(h)&&d->refs==2&&mux.selected&&module_state.refs==1);
 assert(!imx471_shared_power_on(h)&&h->supply_mask==7&&h->clock_enabled&&h->reset_acquired);
 assert(!imx471_shared_power_off(h)&&!mux.selected&&!module_state.refs);
 assert(!imx471_shared_power_on(h)&&!imx471_shared_detach(h));clean(d);
 d=fresh();h=imx471_shared_create(d);assert(!IS_ERR(h));assert(!imx471_shared_detach(h));clean(d);
 /* The second device cannot touch reset/clock/rails while its peer owns route. */
 d=fresh();h=imx471_shared_create(d);assert(!IS_ERR(h));struct device *peer=fresh();
 assert(PTR_ERR(imx471_shared_create(peer))==-EPROBE_DEFER);clean(peer);
 assert(!imx471_shared_detach(h));clean(d);h=imx471_shared_create(peer);assert(!IS_ERR(h));assert(!imx471_shared_detach(h));clean(peer);
 /* Every allocation/acquisition fault cleans only handles actually acquired. */
 d=fresh();fail_alloc=true;assert(PTR_ERR(imx471_shared_create(d))==-ENOMEM);clean(d);
 for(int at=1;at<=6;at++) {
  d=fresh();acquisition_at=at;assert(IS_ERR(imx471_shared_create(d)));assert(!mux.selected&&!module_state.refs&&!live_allocations);clean(d);
 }
 d=fresh();module_state.going=true;assert(PTR_ERR(imx471_shared_create(d))==-ENODEV);assert(!mux.selected&&!module_state.refs);clean(d);
 d=fresh();power_at=1;assert(PTR_ERR(imx471_shared_create(d))==-EIO);assert(!mux.selected&&!module_state.refs);clean(d);
 /* Nine resumed power-on steps, retaining existing handles but no successful enables. */
 for(int at=1;at<=9;at++) {
  d=fresh();h=imx471_shared_create(d);assert(!IS_ERR(h));assert(!imx471_shared_power_off(h));reset_faults();power_at=at;
  assert(imx471_shared_power_on(h)==-EIO);assert(!h->supply_mask&&!h->clock_enabled&&!h->reset_acquired&&!h->route_selected&&!h->power_module_ref);
  reset_faults();assert(!imx471_shared_detach(h));clean(d);
 }
 /* Every shutdown failure blocks a second power-on; bound runtime retry can recover. */
 for(int at=1;at<=4;at++) {
  d=fresh();h=imx471_shared_create(d);assert(!IS_ERR(h));assert(!imx471_shared_power_on(h));reset_faults();off_at=at;
  assert(imx471_shared_power_off(h)==-EIO&&h->route_selected&&h->power_module_ref);unsigned int ops=operations;
  assert(imx471_shared_power_on(h)==-EIO&&operations==ops);reset_faults();assert(!imx471_shared_power_off(h));assert(!imx471_shared_detach(h));clean(d);
 }
 assert(!live_allocations&&!module_state.refs&&!mux.handles&&!mux.selected&&list_empty(&imx471_shared_holders));
 /* Real retained holders survive a simulated sensor devres free. They remain
  * reachable through the independent list at process exit (as until reboot).
  * A separate logical mux per case models four independent boot scenarios.
  */
 struct mux_state *kept_routes[4];
 for(int at=1;at<=4;at++) {
  d=fresh();h=imx471_shared_create(d);assert(!IS_ERR(h));assert(!imx471_shared_power_on(h));reset_faults();off_at=at;
  unsigned int puts=handles_put;assert(imx471_shared_detach(h)==-EIO);
  assert(h->quarantined&&h->removing&&h->route_selected&&h->power_module_ref&&d->refs==2);
  assert(handles_put==puts&&d->reset.handles==1&&d->clock.handles==1&&mux.selected);
  for(unsigned int i=0;i<3;i++)assert(d->rails[i].handles==1);
  unsigned int ops=operations;assert(PTR_ERR(imx471_shared_create(d))==-EBUSY&&operations==ops&&handles_put==puts);
  assert(imx471_shared_power_on(h)==-ENODEV&&imx471_shared_power_off(h)==-ENODEV&&operations==ops);
  peer=fresh();assert(PTR_ERR(imx471_shared_create(peer))==-EPROBE_DEFER);assert(!peer->reset.handles&&!peer->clock.handles);clean(peer);
  assert(h->quarantined&&d->refs==2&&handles_put==puts+1);
  /* Preserve this selected mux object and give the next independent scenario a fresh one. */
  kept_routes[at-1]=malloc(sizeof(mux));assert(kept_routes[at-1]);*kept_routes[at-1]=mux;h->route=kept_routes[at-1];mux=(struct mux_state){0};test_cases++;
 }
 assert(live_allocations==4&&module_state.refs==4);
 for(unsigned int i=0;i<4;i++)assert(kept_routes[i]->selected&&kept_routes[i]->handles==1);
 printf("HOLDER_C_RESULT cases=%u acquisition_faults=9 resumed_power_on_faults=9 runtime_off_faults=4 detached_quarantines=4 device_module_real_handles_retained=1 result=0\n",test_cases);
 return 0;
}
'''
# Keep the test fault model precise: a failure at the Nth power step occurs once;
# cleanup assertion is later than that step and can succeed independently.
code = preamble + '\n' + body + '\n' + main
attempt = 1
while (PRIVATE / f'holder-c-r{attempt}-compile-private.log').exists(): attempt += 1
source = PRIVATE / f'holder-c-r{attempt}-private.c'; binary = PRIVATE / f'holder-c-r{attempt}-asan'
source.write_text(code)
cc = subprocess.run(['gcc','-std=gnu11','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer',
                     '-fno-pie','-no-pie','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(source),'-o',str(binary)],capture_output=True)
(PRIVATE / f'holder-c-r{attempt}-compile-private.log').write_bytes(cc.stdout+cc.stderr)
if cc.returncode:
    print((cc.stdout+cc.stderr).decode()); raise SystemExit(cc.returncode)
run = subprocess.run([str(binary)],capture_output=True,timeout=30,env=dict(os.environ,
    ASAN_OPTIONS='detect_leaks=1:abort_on_error=1:strict_string_checks=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
(PRIVATE / f'holder-c-r{attempt}-run-private.log').write_bytes(run.stdout+run.stderr)
if run.returncode:
    print((run.stdout+run.stderr).decode()); raise SystemExit(run.returncode)
assert b'result=0' in run.stdout
report = dict(stage=462,revision='r2',attempt=attempt,passed=True,
              source_sha256=hashlib.sha256(text.encode()).hexdigest(),
              exact_extracted_holder_sha256=hashlib.sha256(body.encode()).hexdigest(),
              candidate_c_bodies_unmodified=True,compile_exit=cc.returncode,run_exit=run.returncode,
              result=run.stdout.decode().strip(),runtime_reference_failures_and_real_handles_checked=True,
              probe_remove_resource_retention_modeled=True,detached_quarantine_cases=4,
              retained_memory_device_module_and_all_resource_handles=4,
              late_power_calls_refused_and_same_device_rebind_blocked=True,
              provider_unbind_or_module_unload_tested=False,kernel_pm_concurrency_or_open_fd_lifetime_tested=False,
              phone_or_sdk_accessed=False,deployable=False)
(HERE / 'holder-c-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
