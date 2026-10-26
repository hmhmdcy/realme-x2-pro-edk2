"""Run exact sensor lifetime and V4L2 file/release C with finite API stubs."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('check462r3_storage449',HERE.parents[1]/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
storage.mount.mounted_build()
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462/r3')
text=(PRIVATE/'candidate/drivers/media/i2c/imx471.c').read_text()
old=(PRIVATE/'r2-imx471-private.c').read_text()
core=(PRIVATE/'source/drivers/media/v4l2-core/v4l2-device.c').read_text()
subdev=(PRIVATE/'source/drivers/media/v4l2-core/v4l2-subdev.c').read_text()
fixed=core.replace('\tif (sd->internal_ops && sd->internal_ops->release)\n\t\tsd->internal_ops->release(sd);\n\tsd->devnode = NULL;',
                   '\tsd->devnode = NULL;\n\tif (sd->internal_ops && sd->internal_ops->release)\n\t\tsd->internal_ops->release(sd);')
assert hashlib.sha256(fixed.encode()).hexdigest()==json.loads((HERE.parents[1]/'kernel456/source-validation.json').read_text())['actual_core_sha256']
def function(s,signature):
    start=s.index(signature);end=s.index('{',start)+1;depth=1
    while depth:
        depth+=(s[end]=='{')-(s[end]=='}');end+=1
    return s[start:end]
sensor_struct=text[text.index('struct imx471 {'):text.index('\n};',text.index('struct imx471 {'))+3]
start=text.index('/* The async registration and video node own')
lifetime=text[start:text.index('static int imx471_get_regulators(',start)]
detach=function(text,'static void imx471_detach(')
remove=function(text,'static void imx471_remove(')
internal=text[text.index('static const struct v4l2_subdev_internal_ops imx471_internal_ops'):text.index('\n};',text.index('static const struct v4l2_subdev_internal_ops imx471_internal_ops'))+3]
core_old=function(core,'static void v4l2_subdev_release(')
core_fixed=function(fixed,'static void v4l2_subdev_release(')
core_node=function(fixed,'static void v4l2_device_release_subdev_node(')
core_open=function(subdev,'static int subdev_open(')
core_close=function(subdev,'static int subdev_close(')
r2_remove=function(old,'static void imx471_remove(').replace('static void imx471_remove(', 'static void snapshot_r2_remove(',1)
preamble=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GFP_KERNEL 0
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
#define to_imx471(sd) container_of(sd,struct imx471,sd)
struct mutex { bool initialized, held; };
struct kref { unsigned int refs; };
typedef struct { int refs; } atomic_t;
struct list_head { struct list_head *next,*prev; };
struct module { unsigned int refs; bool going; };
struct driver { struct module *owner; };
struct device { unsigned int refs; bool active, pm_enabled; struct driver *driver; void *data; };
struct i2c_client { struct device dev; };
struct v4l2_ctrl { int unused; };
struct media_pad { int flags; };
struct media_device { struct device *dev; };
struct entity { struct { struct media_device *mdev; } graph_obj; };
struct v4l2_device { struct media_device *mdev; };
struct v4l2_ctrl_handler { struct mutex *lock; bool allocated; };
struct v4l2_subdev;
struct video_device;
struct v4l2_subdev_state { struct mutex *lock; };
struct v4l2_fh { struct video_device *vdev; struct v4l2_ctrl_handler *ctrl_handler; };
struct v4l2_subdev_fh { struct v4l2_fh vfh; struct v4l2_subdev_state *state; struct module *owner; };
struct v4l2_subdev_internal_ops {
 int (*init_state)(struct v4l2_subdev *,struct v4l2_subdev_state *);
 int (*registered)(struct v4l2_subdev *);
 void (*release)(struct v4l2_subdev *);
 int (*open)(struct v4l2_subdev *,struct v4l2_subdev_fh *);
 int (*close)(struct v4l2_subdev *,struct v4l2_subdev_fh *);
};
struct v4l2_subdev { const struct v4l2_subdev_internal_ops *internal_ops; struct v4l2_ctrl_handler *ctrl_handler;
 struct device *dev; struct entity entity; struct v4l2_subdev_state *active_state;
 struct v4l2_device *v4l2_dev; struct video_device *devnode; struct module *owner; bool owner_v4l2_dev; };
struct video_device { struct v4l2_subdev *data; struct v4l2_ctrl_handler *ctrl_handler; unsigned int refs; bool registered; };
struct file { struct video_device *vdev; struct v4l2_fh *private_data; };
struct imx471_shared { struct device *dev; bool quarantined; };
struct gpio_desc { int unused; }; struct reset_control { int unused; };
struct clk { int unused; }; struct regmap { int unused; };
struct regulator_bulk_data { int unused; };
static const char * const imx471_supply_name[] = { "vana","vdig","vif" };
#define LIST_HEAD(name) struct list_head name={&(name),&(name)}
#define DEFINE_MUTEX(name) struct mutex name={true,false}
#define list_for_each_entry(pos,head,member) \
 for(pos=container_of((head)->next,__typeof__(*pos),member); &(pos)->member!=(head); pos=container_of((pos)->member.next,__typeof__(*pos),member))
static struct module sensor_module, camss_module;
static struct driver camss_driver={&camss_module};
static struct device camss_device={.refs=1,.driver=&camss_driver};
static struct media_device media={&camss_device};
static struct v4l2_device bridge={&media};
static struct i2c_client clients[64];static unsigned int client_count;
static struct imx471_shared kept_holders[2];static unsigned int kept_count;
static unsigned int allocated,freed,ctrl_frees,entity_frees,state_frees,fh_states,fh_exits,pm_calls,power_offs,case_count;
static bool fail_alloc,fail_fh_state,fail_shared_off;
static void *last_alloc;
static void mutex_init(struct mutex *m) { m->initialized=true;m->held=false; }
static void mutex_lock(struct mutex *m) { assert(m->initialized&&!m->held);m->held=true; }
static void mutex_unlock(struct mutex *m) { assert(m->initialized&&m->held);m->held=false; }
static void mutex_destroy(struct mutex *m) { assert(m->initialized&&!m->held);m->initialized=false; }
static void INIT_LIST_HEAD(struct list_head *h) { h->next=h->prev=h; }
static bool list_empty(struct list_head *h) { return h->next==h; }
static void list_add_tail(struct list_head *e,struct list_head *h) { e->prev=h->prev;e->next=h;h->prev->next=e;h->prev=e; }
static void list_del(struct list_head *e) { e->prev->next=e->next;e->next->prev=e->prev; }
static void kref_init(struct kref *r) { r->refs=1; }
static void kref_get(struct kref *r) { assert(r->refs);r->refs++; }
static void kref_put(struct kref *r,void (*destroy)(struct kref *)) { assert(r->refs);if(!--r->refs)destroy(r); }
static void atomic_set(atomic_t *a,int n) { a->refs=n; }
static int atomic_read(atomic_t *a) { return a->refs; }
static int atomic_xchg(atomic_t *a,int n) { int old=a->refs;a->refs=n;return old; }
static void *kzalloc(size_t n,int flags) { if(fail_alloc)return NULL;void *p=calloc(1,n);assert(p);allocated++;last_alloc=p;return p; }
#define kzalloc_obj(v) kzalloc(sizeof(v),GFP_KERNEL)
static void kfree(void *p) { assert(p);freed++;free(p); }
static struct device *get_device(struct device *d) { assert(d->refs);d->refs++;return d; }
static void put_device(struct device *d) { assert(d->refs>1);d->refs--; }
static bool try_module_get(struct module *m) { if(!m)return true;if(m->going)return false;m->refs++;return true; }
static void module_put(struct module *m) { if(m){assert(m->refs);m->refs--;} }
static struct video_device *video_devdata(struct file *f) { return f->vdev; }
static struct v4l2_subdev *vdev_to_v4l2_subdev(struct video_device *v) { return v->data; }
static struct v4l2_subdev *video_get_drvdata(struct video_device *v) { return v->data; }
static struct v4l2_fh *file_to_v4l2_fh(struct file *f) { return f->private_data; }
static struct v4l2_subdev_fh *to_v4l2_subdev_fh(struct v4l2_fh *f) { return container_of(f,struct v4l2_subdev_fh,vfh); }
static void v4l2_device_release_subdev_node(struct video_device *v);
static void video_put(struct video_device *v) { assert(v->refs);if(!--v->refs)v4l2_device_release_subdev_node(v); }
static void video_unregister_device(struct video_device *v) { if(!v->registered)return;v->registered=false;video_put(v); }
static void v4l2_async_unregister_subdev(struct v4l2_subdev *sd) {
 if(!sd->v4l2_dev)return;
 sd->v4l2_dev=NULL;
 if(sd->devnode)video_unregister_device(sd->devnode);else {
  extern void dispatch_release(struct v4l2_subdev *);dispatch_release(sd);
 }
}
static void v4l2_subdev_cleanup(struct v4l2_subdev *sd) { state_frees++;free(sd->active_state);sd->active_state=NULL; }
static void media_entity_cleanup(struct entity *e) { entity_frees++; }
static void v4l2_ctrl_handler_free(struct v4l2_ctrl_handler *h) { assert(h->allocated&&h->lock->initialized);mutex_lock(h->lock);h->allocated=false;ctrl_frees++;mutex_unlock(h->lock); }
static void pm_runtime_disable(struct device *d) { assert(d->pm_enabled);pm_calls++;d->pm_enabled=false; }
static bool pm_runtime_status_suspended(struct device *d) { return !d->active; }
static void pm_runtime_set_suspended(struct device *d) { pm_calls++;d->active=false; }
static int imx471_shared_detach(struct imx471_shared *h) {
 assert(h->dev->refs>=2);if(fail_shared_off){h->quarantined=true;return -EIO;}h->dev->active=false;put_device(h->dev);return 0;
}
static int imx471_power_off(struct device *d) { assert(d->active);power_offs++;d->active=false;return 0; }
static void *i2c_get_clientdata(struct i2c_client *c) { return c->dev.data; }
static int subdev_fh_init(struct v4l2_subdev_fh *f,struct v4l2_subdev *sd) {
 if(fail_fh_state)return -ENOMEM;
 f->state=calloc(1,sizeof(*f->state));assert(f->state);fh_states++;return 0;
}
static void subdev_fh_free(struct v4l2_subdev_fh *f) { assert(f->state&&fh_states);free(f->state);f->state=NULL;fh_states--; }
static void v4l2_fh_init(struct v4l2_fh *f,struct video_device *v) { f->vdev=v;f->ctrl_handler=v->ctrl_handler;assert(f->ctrl_handler->allocated); }
static void v4l2_fh_add(struct v4l2_fh *f,struct file *file) { file->private_data=f; }
static void v4l2_fh_del(struct v4l2_fh *f,struct file *file) { assert(file->private_data==f);file->private_data=NULL; }
static void v4l2_fh_exit(struct v4l2_fh *f) { assert(f->ctrl_handler->allocated);fh_exits++;f->vdev=NULL; }
static int imx471_init_state(struct v4l2_subdev *sd,struct v4l2_subdev_state *state) { return 0; }
'''
fixtures=r'''
void dispatch_release(struct v4l2_subdev *sd) { v4l2_subdev_release(sd); }
static struct i2c_client *fresh(void) {
 assert(client_count<ARRAY_SIZE(clients));struct i2c_client *c=&clients[client_count++];c->dev.refs=1;
 fail_alloc=fail_fh_state=fail_shared_off=false;camss_module.going=false;return c;
}
static struct imx471 *setup(struct i2c_client *c,unsigned int stage) {
 struct imx471 *s=imx471_alloc(&c->dev);assert(!IS_ERR(s));
 if(stage>=1){s->sd_initialized=true;s->sd.dev=&c->dev;s->sd.internal_ops=&imx471_internal_ops;c->dev.data=&s->sd;}
 if(stage>=2){s->ctrls_initialized=true;s->ctrl_handler.lock=&s->lock;s->ctrl_handler.allocated=true;s->sd.ctrl_handler=&s->ctrl_handler;c->dev.active=true;}
 if(stage>=3)s->entity_initialized=true;
 if(stage>=4){s->sd.active_state=calloc(1,sizeof(*s->sd.active_state));assert(s->sd.active_state);}
 if(stage>=5){s->pm_enabled=true;c->dev.pm_enabled=true;c->dev.active=true;}
 return s;
}
static int register_sensor(struct imx471 *s,bool node) {
 assert(!s->sd.v4l2_dev);assert(try_module_get(&sensor_module));s->sd.owner=&sensor_module;s->sd.v4l2_dev=&bridge;
 int ret=imx471_registered(&s->sd);if(ret){module_put(&sensor_module);s->sd.v4l2_dev=NULL;return ret;}
 s->sd.entity.graph_obj.mdev=&media;
 if(node){struct video_device *v=kzalloc(sizeof(*v),0);assert(v);v->data=&s->sd;v->ctrl_handler=&s->ctrl_handler;v->refs=1;v->registered=true;s->sd.devnode=v;}
 return 0;
}
static int open_fd(struct imx471 *s,struct file *f) {
 struct video_device *v=s->sd.devnode;if(!v||!v->registered)return -ENODEV;f->vdev=v;v->refs++;
 int ret=subdev_open(f);if(ret){video_put(v);f->vdev=NULL;}return ret;
}
static void close_fd(struct file *f) { struct video_device *v=f->vdev;assert(v&&f->private_data);assert(!subdev_close(f));video_put(v);f->vdev=NULL; }
static void clean(struct i2c_client *c) { assert(c->dev.refs==1&&!c->dev.pm_enabled&&!c->dev.active);case_count++; }
static void check_retained(struct imx471 *s,unsigned int refs) {
 assert(s->ref.refs==refs&&s->ctrl_handler.allocated&&s->sd.active_state&&s->lock.initialized);
}
static void add_shared(struct imx471 *s) { assert(kept_count<2);struct imx471_shared *h=&kept_holders[kept_count++];h->dev=get_device(s->dev);s->shared=h; }
int main(int argc,char **argv) {
 if(argc>1&&!strcmp(argv[1],"r2-witness")) {
  struct i2c_client *c=fresh();struct imx471 *s=setup(c,5);assert(!register_sensor(s,true));struct file f={0};assert(!open_fd(s,&f));
  snapshot_r2_remove(c);kfree(s); /* driver's subsequent devres release */
  close_fd(&f);return 99;
 }
 if(argc>1&&!strcmp(argv[1],"old-core-witness")) {
  struct i2c_client *c=fresh();struct imx471 *s=setup(c,5);assert(!register_sensor(s,true));struct file f={0};assert(!open_fd(s,&f));
  imx471_remove(c);close_fd(&f);return 99;
 }
 /* Allocation failure and each partial-probe initialization boundary. */
 struct i2c_client *c=fresh();fail_alloc=true;assert(PTR_ERR(imx471_alloc(&c->dev))==-ENOMEM);clean(c);
 for(unsigned int stage=0;stage<=5;stage++) {
  c=fresh();struct imx471 *s=setup(c,stage);imx471_detach(s,stage>=2&&stage<5);clean(c);
 }
 /* A fully bound object has base+framework refs, with or without a node. */
 for(int node=0;node<2;node++) {
  c=fresh();struct imx471 *s=setup(c,5);assert(!register_sensor(s,node));check_retained(s,2);imx471_remove(c);clean(c);
 }
 /* Normal opens/closes add no sensor PM reference and leave base+framework. */
 c=fresh();struct imx471 *s=setup(c,5);assert(!register_sensor(s,true));struct file a={0},b={0};unsigned int pm=pm_calls;
 assert(!open_fd(s,&a)&&!open_fd(s,&b)&&pm_calls==pm);close_fd(&a);close_fd(&b);check_retained(s,2);imx471_remove(c);clean(c);
 /* Remove retains state/ctrl/entity until both late core closes have run. */
 c=fresh();s=setup(c,5);assert(!register_sensor(s,true));assert(!open_fd(s,&a)&&!open_fd(s,&b));
 unsigned int cf=ctrl_frees,ef=entity_frees,sf=state_frees;imx471_remove(c);check_retained(s,1);
 assert(s->removing&&c->dev.refs==2&&ctrl_frees==cf&&entity_frees==ef&&state_frees==sf);
 pm=pm_calls;assert(PTR_ERR(imx471_alloc(&c->dev))==-EBUSY);assert(!a.vdev->registered); /* ioctls are refused by core */
 close_fd(&a);check_retained(s,1);assert(pm_calls==pm);close_fd(&b);assert(pm_calls==pm&&ctrl_frees==cf+1&&entity_frees==ef+1&&state_frees==sf+1);
 clean(c);s=setup(c,5);imx471_remove(c);clean(c);
 /* Notifier-only unregister can re-register after its last old FD, while
  * the driver's base reference continues to own controls/state and device.
  */
 c=fresh();s=setup(c,5);assert(!register_sensor(s,true));assert(!open_fd(s,&a));v4l2_async_unregister_subdev(&s->sd);
 assert(register_sensor(s,true)==-EBUSY&&s->ref.refs==2);close_fd(&a);check_retained(s,1);
 for(unsigned int i=0;i<3;i++){assert(!register_sensor(s,true));v4l2_async_unregister_subdev(&s->sd);check_retained(s,1);}imx471_remove(c);clean(c);
 /* Registration failure before node creation releases its framework ref
  * synchronously. A callback rejected during removal cannot add a ref.
  */
 c=fresh();s=setup(c,5);assert(!register_sensor(s,false));v4l2_async_unregister_subdev(&s->sd);check_retained(s,1);
 mutex_lock(&s->lock);s->removing=true;mutex_unlock(&s->lock);assert(imx471_registered(&s->sd)==-EBUSY&&s->ref.refs==1);imx471_detach(s,false);clean(c);
 /* Node opened before a later registration/probe failure is still safe. */
 c=fresh();s=setup(c,5);assert(!register_sensor(s,true));assert(!open_fd(s,&a));v4l2_async_unregister_subdev(&s->sd);imx471_detach(s,true);check_retained(s,1);close_fd(&a);clean(c);
 /* Actual subdev-open error cleanup: state allocation and media-owner GOING. */
 c=fresh();s=setup(c,5);assert(!register_sensor(s,true));fail_fh_state=true;assert(open_fd(s,&a)==-ENOMEM);fail_fh_state=false;
 camss_module.going=true;assert(open_fd(s,&a)==-EBUSY&&!fh_states);camss_module.going=false;imx471_remove(c);clean(c);
 /* Independently quarantined r2 resources do not require a sensor base
  * reference after every old FD is gone. r2's actual holder C is unchanged.
  */
 for(int fd=0;fd<2;fd++) {
  c=fresh();s=setup(c,5);add_shared(s);assert(!register_sensor(s,true));if(fd)assert(!open_fd(s,&a));
  fail_shared_off=true;unsigned int old_frees=freed;imx471_remove(c);
  assert(kept_holders[kept_count-1].quarantined&&c->dev.refs==(unsigned int)(fd?3:2));
  if(fd){check_retained(s,1);assert(freed>=old_frees);close_fd(&a);}
  assert(c->dev.refs==2);case_count++;
 }
 assert(list_empty(&imx471_instances)&&!sensor_module.refs&&!camss_module.refs&&!fh_states);
 printf("SENSOR_LIFETIME_C_RESULT cases=%u retained_r2_resource_devices=2 all_sensor_instances_freed=1 no_open_pm_refs=1 result=0\n",case_count);
 return 0;
}
'''
attempt=1
while (PRIVATE/f'lifetime-c-r{attempt}-private.c').exists():attempt+=1
base=preamble+'\n'+sensor_struct+'\n'+lifetime+'\n'+internal+'\n'+detach+'\n'+remove+'\n'+r2_remove+'\n'
tail='\n'+core_node+'\n'+core_open+'\n'+core_close+'\n'+fixtures
flags=['gcc','-std=gnu11','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie',
       '-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function']
env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:abort_on_error=1:strict_string_checks=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
def compile_source(name,body):
    source=PRIVATE/name;source.write_text(body);binary=source.with_suffix('.asan')
    cc=subprocess.run(flags+[str(source),'-o',str(binary)],capture_output=True)
    source.with_suffix('.compile-private.log').write_bytes(cc.stdout+cc.stderr)
    if cc.returncode:print((cc.stdout+cc.stderr).decode());raise SystemExit(cc.returncode)
    return binary
binary=compile_source(f'lifetime-c-r{attempt}-private.c',base+'\n'+core_fixed+tail)
run=subprocess.run([str(binary)],capture_output=True,env=env,timeout=30)
(PRIVATE/f'lifetime-c-r{attempt}-run-private.log').write_bytes(run.stdout+run.stderr)
if run.returncode:print((run.stdout+run.stderr).decode());raise SystemExit(run.returncode)
assert b'result=0' in run.stdout
negative=subprocess.run([str(binary),'r2-witness'],capture_output=True,env=env,timeout=30)
(PRIVATE/f'lifetime-c-r{attempt}-r2-uaf-private.log').write_bytes(negative.stdout+negative.stderr)
assert negative.returncode and b'heap-use-after-free' in negative.stderr
old_binary=compile_source(f'lifetime-c-r{attempt}-old-core-private.c',base+'\n'+core_old+tail)
negative_core=subprocess.run([str(old_binary),'old-core-witness'],capture_output=True,env=env,timeout=30)
(PRIVATE/f'lifetime-c-r{attempt}-old-core-uaf-private.log').write_bytes(negative_core.stdout+negative_core.stderr)
assert negative_core.returncode and b'heap-use-after-free' in negative_core.stderr
report=dict(stage=462,revision='r3',passed=True,attempt=attempt,source_sha256=hashlib.sha256(text.encode()).hexdigest(),
    sensor_struct_and_lifetime_detach_remove_c_unmodified=True,
    exact_lifetime_section_sha256=hashlib.sha256(lifetime.encode()).hexdigest(),
    exact_detach_sha256=hashlib.sha256(detach.encode()).hexdigest(),
    actual_core_subdev_open_close_and_0064_release_executed=True,
    core0064_source_sha256=hashlib.sha256(fixed.encode()).hexdigest(),
    result=run.stdout.decode().strip(),r2_late_close_uaf_negative_witness=True,old_core_post_release_uaf_negative_witness=True,
    finite_partial_probe_cleanup_stages=6,registration_cycles_and_open_errors_checked=True,
    late_close_retains_state_controls_entity_and_device_until_final_release=True,
    old_fd_device_rebind_refused_until_final_release=True,open_close_adds_sensor_pm_reference=False,
    r2_resource_holder_interface_stubbed_and_unchanged_actual_proof_reused=True,
    full_probe_or_runtime_hardware_functions_executed=False,kernel_threads_lockdep_or_concurrent_open_unbind_tested=False,
    sdk_or_phone_accessed=False,deployable=False)
(HERE/'lifetime-c-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
