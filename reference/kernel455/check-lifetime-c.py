"""Run unchanged candidate C bodies with explicit sequential lifetime/PM stubs."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel455')
text = (HERE / 'bu64253.c').read_text()
begin = text.index('#define BU64253_MAX_FOCUS')
end = text.index('static const struct of_device_id')
body = text[begin:end]
core = Path('/mnt/e/edk2-samurai-out/kernel453/schema/v4l2-device-release-order-candidate-private.c').read_text()
core_start = core.index('static void v4l2_subdev_release(')
brace = core.index('{', core_start); core_end = brace + 1; depth = 1
while depth:
    depth += (core[core_end] == '{') - (core[core_end] == '}'); core_end += 1
core_release = core[core_start:core_end]

preamble = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef struct { int value; } atomic_t;
struct mutex { bool initialized, held; };
struct kref { int refs; };
struct list_head { struct list_head *next, *prev; };
struct module { unsigned int refs; bool going; };
struct regulator { int handles, enabled; };
struct v4l2_subdev;
struct binding { struct v4l2_subdev *sd; bool registered; unsigned int users; };
struct device { void *data; unsigned int refs, usage; bool active, pm_enabled; struct regulator regulator; struct binding binding; };
struct i2c_client { struct device dev; void *adapter; };
struct firmware { size_t size; const u8 *data; };
struct v4l2_subdev_fh { int unused; };
struct entity { int function; };
struct v4l2_ctrl_handler { int error; struct mutex *lock; };
struct v4l2_ctrl { struct v4l2_ctrl_handler *handler; unsigned int id, flags; int val; };
struct v4l2_ctrl_ops { int (*s_ctrl)(struct v4l2_ctrl *); };
struct v4l2_subdev_internal_ops {
 int (*registered)(struct v4l2_subdev *);
 void (*release)(struct v4l2_subdev *);
 int (*open)(struct v4l2_subdev *,struct v4l2_subdev_fh *);
 int (*close)(struct v4l2_subdev *,struct v4l2_subdev_fh *);
};
struct v4l2_subdev_ops { int unused; };
struct v4l2_subdev { struct device *dev; void *client; struct module *owner; bool owner_v4l2_dev; void *devnode;
 const struct v4l2_subdev_internal_ops *internal_ops; int flags; struct entity entity; struct v4l2_ctrl_handler *ctrl_handler; };
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
#define LIST_HEAD(name) struct list_head name={&(name),&(name)}
#define DEFINE_MUTEX(name) struct mutex name={true,false}
#define list_for_each_entry(pos,head,member) \
 for(pos=container_of((head)->next,__typeof__(*pos),member); &(pos)->member!=(head); pos=container_of((pos)->member.next,__typeof__(*pos),member))
#define I2C_FUNC_I2C 1
#define GFP_KERNEL 0
#define V4L2_SUBDEV_FL_HAS_DEVNODE 1
#define MEDIA_ENT_F_LENS 2
#define V4L2_CID_FOCUS_ABSOLUTE 3
#define V4L2_CTRL_FLAG_EXECUTE_ON_WRITE 4
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
static struct module module_state;
#define THIS_MODULE (&module_state)
static int warnings;
#define WARN_ON(condition) ((condition) ? (++warnings,1) : 0)
#define dev_err(...) ((void)0)
static struct firmware input;
static struct i2c_client clients[128];
static unsigned int client_count;
static struct v4l2_ctrl focus;
static unsigned int live_allocations, allocations, frees, lookups, regulator_put_calls, enables, disables, writes;
static unsigned int ctrl_frees, entity_frees, pm_gets, pm_puts, pm_puts_noidle, property_calls, requests, releases;
static int property_error, request_error, lookup_error, enable_error, disable_error, ctrl_error, entity_error, async_error;
static unsigned int fail_write_at;
static int fail_write_result;
static void *last_allocation;
static unsigned int completed_cases;
static u8 written_bytes[64][2];
static int bu64253_runtime_resume(struct device *dev);
static int bu64253_runtime_suspend(struct device *dev);
static void v4l2_subdev_release(struct v4l2_subdev *sd);
static void INIT_LIST_HEAD(struct list_head *h) { h->next=h->prev=h; }
static bool list_empty(const struct list_head *h) { return h->next==h; }
static void list_add_tail(struct list_head *e,struct list_head *h) { e->prev=h->prev;e->next=h;h->prev->next=e;h->prev=e; }
static void list_del(struct list_head *e) { e->prev->next=e->next;e->next->prev=e->prev;e->next=e->prev=NULL; }
static void atomic_set(atomic_t *a,int n) { a->value=n; }
static int atomic_read(const atomic_t *a) { return a->value; }
static int atomic_xchg(atomic_t *a,int n) { int old=a->value;a->value=n;return old; }
static void kref_init(struct kref *r) { r->refs=1; }
static void kref_get(struct kref *r) { assert(r->refs>0);r->refs++; }
static void kref_put(struct kref *r,void (*release)(struct kref *)) { assert(r->refs>0);if(!--r->refs)release(r); }
static void mutex_init(struct mutex *m) { m->initialized=true;m->held=false; }
static void mutex_lock(struct mutex *m) { assert(m->initialized&&!m->held);m->held=true; }
static void mutex_unlock(struct mutex *m) { assert(m->initialized&&m->held);m->held=false; }
static void mutex_destroy(struct mutex *m) { assert(m->initialized&&!m->held);m->initialized=false; }
static struct device *get_device(struct device *d) { assert(d->refs);d->refs++;return d; }
static void put_device(struct device *d) { assert(d->refs>1);d->refs--; }
static bool try_module_get(struct module *m) { if(m->going)return false;m->refs++;return true; }
static void module_put(struct module *m) { if(m){assert(m->refs);m->refs--;} }
static void *kzalloc(size_t size,int flags) { void *p=calloc(1,size);assert(p);allocations++;live_allocations++;last_allocation=p;return p; }
static void kfree(void *p) { assert(p&&live_allocations);frees++;live_allocations--;free(p); }
static u16 get_unaligned_le16(const void *p) { const u8 *b=p;return b[0]|(u16)b[1]<<8; }
static int device_property_read_string(struct device *d,const char *key,const char **name) {
 property_calls++;assert(!strcmp(key,"firmware-name"));if(property_error)return property_error;*name="matched-private-init";return 0;
}
static int request_firmware(const struct firmware **fw,const char *name,struct device *d) { requests++;if(request_error)return request_error;*fw=&input;return 0; }
static void release_firmware(const struct firmware *fw) { assert(fw==&input);releases++; }
static int i2c_check_functionality(void *adapter,int flags) { return 1; }
static int dev_err_probe(struct device *d,int ret,const char *fmt,...) { return ret; }
static struct regulator *regulator_get(struct device *d,const char *name) {
 lookups++;assert(!strcmp(name,"vdd"));if(lookup_error)return ERR_PTR(lookup_error);assert(!d->regulator.handles);d->regulator.handles++;return &d->regulator;
}
static void regulator_put(struct regulator *r) { regulator_put_calls++;assert(r->handles==1&&!r->enabled);r->handles--; }
static int regulator_enable(struct regulator *r) { enables++;assert(module_state.refs);if(enable_error)return enable_error;assert(r->handles==1&&!r->enabled);r->enabled++;return 0; }
static int regulator_disable(struct regulator *r) { disables++;assert(module_state.refs);assert(r->handles==1&&r->enabled==1);if(disable_error)return disable_error;r->enabled--;return 0; }
static void usleep_range(unsigned int low,unsigned int high) { assert(low<=high); }
static void v4l2_i2c_subdev_init(struct v4l2_subdev *sd,struct i2c_client *c,const void *ops) { sd->dev=&c->dev;sd->client=c;c->dev.data=sd; }
static void *dev_get_drvdata(struct device *d) { return d->data; }
static void *v4l2_get_subdevdata(struct v4l2_subdev *sd) { return sd->client; }
static void *i2c_get_clientdata(struct i2c_client *c) { return c->dev.data; }
static int i2c_master_send(struct i2c_client *c,const u8 *data,int len) { assert(len==2&&c->dev.regulator.enabled==1&&writes<64);memcpy(written_bytes[writes],data,2);writes++;return writes==fail_write_at?fail_write_result:len; }
static void v4l2_ctrl_handler_init(struct v4l2_ctrl_handler *h,int count) { h->error=ctrl_error; }
static struct v4l2_ctrl *v4l2_ctrl_new_std(struct v4l2_ctrl_handler *h,const struct v4l2_ctrl_ops *ops,int id,int min,int max,int step,int def) {
 assert(id==3&&min==0&&max==1023&&step==1&&def==0);focus.handler=h;focus.id=id;return &focus;
}
static void v4l2_ctrl_handler_free(struct v4l2_ctrl_handler *h) { ctrl_frees++; }
static int media_entity_pads_init(struct entity *e,unsigned int count,void *pads) { assert(!count&&!pads);return entity_error; }
static void media_entity_cleanup(struct entity *e) { entity_frees++; }
static void pm_runtime_enable(struct device *d) { assert(!d->pm_enabled);d->pm_enabled=true; }
static void pm_runtime_disable(struct device *d) { d->pm_enabled=false; }
static void pm_runtime_set_suspended(struct device *d) { assert(!d->regulator.enabled);d->active=false; }
static int pm_runtime_resume_and_get(struct device *d) {
 int ret=0;pm_gets++;assert(d->pm_enabled);d->usage++;
 if(!d->active){ret=bu64253_runtime_resume(d);if(!ret)d->active=true;}
 if(ret)d->usage--;
 return ret;
}
static int pm_runtime_get_if_in_use(struct device *d) { if(d->active&&d->usage){d->usage++;return 1;}return 0; }
static void pm_runtime_put(struct device *d) { pm_puts++;assert(d->usage);d->usage--; }
static void pm_runtime_put_noidle(struct device *d) { pm_puts_noidle++;assert(d->usage);d->usage--; }
static int v4l2_async_register_subdev(struct v4l2_subdev *sd) { return async_error; }
static void fake_final_release(struct binding *b) { struct v4l2_subdev *sd=b->sd;assert(sd&&!b->registered&&!b->users);b->sd=NULL;v4l2_subdev_release(sd); }
static void v4l2_async_unregister_subdev(struct v4l2_subdev *sd) {
 struct binding *b=&sd->dev->binding;
 if(b->sd!=sd||!b->registered)return;
 b->registered=false;
 if(!b->users)fake_final_release(b);
}
'''

main = r'''
static struct i2c_client *fresh(const u8 *data,size_t size) {
 assert(client_count<128);struct i2c_client *c=&clients[client_count++];c->dev.refs=1;c->adapter=(void *)1;
 input.data=data;input.size=size;property_error=request_error=lookup_error=enable_error=disable_error=ctrl_error=entity_error=async_error=0;
 allocations=frees=lookups=regulator_put_calls=enables=disables=writes=ctrl_frees=entity_frees=pm_gets=pm_puts=pm_puts_noidle=property_calls=requests=releases=0;
 fail_write_at=0;fail_write_result=0;return c;
}
static struct bu64253 *probe(struct i2c_client *c) { assert(!bu64253_probe(c));return to_bu64253(c->dev.data); }
static int register_node(struct bu64253 *l) {
 struct binding *b=&l->dev->binding;assert(!b->sd);assert(try_module_get(THIS_MODULE));
 int ret=l->sd.internal_ops->registered(&l->sd);
 if(ret){module_put(THIS_MODULE);return ret;}
 b->sd=&l->sd;b->registered=true;l->sd.owner=THIS_MODULE;l->sd.devnode=b;return 0;
}
static int open_node(struct bu64253 *l) { int ret=l->sd.internal_ops->open(&l->sd,NULL);if(!ret)l->dev->binding.users++;return ret; }
static void close_node(struct binding *b) { assert(b->sd&&b->users);assert(!b->sd->internal_ops->close(b->sd,NULL));b->users--;if(!b->registered&&!b->users)fake_final_release(b); }
static void remove_driver(struct i2c_client *c) { bu64253_remove(c);c->dev.data=NULL; }
static void complete_clean(struct i2c_client *c) { assert(c->dev.refs==1&&!c->dev.usage&&!c->dev.regulator.handles&&!c->dev.regulator.enabled);assert(!warnings);completed_cases++; }
static void invalid(const u8 *data,size_t size,int wanted) {
 struct i2c_client *c=fresh(data,size);assert(bu64253_probe(c)==wanted);assert(!lookups&&!enables&&!disables&&!writes&&!pm_gets);assert(allocations==1&&frees==1);complete_clean(c);
}
static void read_file(const char *path,u8 data[20]) { FILE *f=fopen(path,"rb");assert(f);assert(fread(data,1,20,f)==20);assert(fgetc(f)==EOF);assert(!fclose(f)); }
int main(int argc,char **argv) {
 assert(argc==3);u8 first[20],second[20],bad[21];read_file(argv[1],first);read_file(argv[2],second);
 for(int which=0;which<2;which++) {
  struct i2c_client *c=fresh(which?second:first,20);struct bu64253 *l=probe(c);assert(l->ref.refs==1&&c->dev.refs==2);
  assert(!register_node(l)&&l->ref.refs==2);assert(!open_node(l)&&!open_node(l));assert(writes==3&&enables==1&&module_state.refs==2&&c->dev.usage==2);
  for(unsigned int i=0;i<3;i++)assert(!memcmp(written_bytes[i],input.data+8+i*4,2));
  close_node(&c->dev.binding);close_node(&c->dev.binding);assert(!c->dev.usage);
  assert(!bu64253_runtime_suspend(&c->dev));c->dev.active=false;assert(!l->supply_enabled&&!l->power_module_ref&&module_state.refs==1);
  v4l2_async_unregister_subdev(&l->sd);assert(l->ref.refs==1&&module_state.refs==0);remove_driver(c);complete_clean(c);
 }
 /* Missing file plus seventeen illegal format cases. */
 struct i2c_client *c=fresh(NULL,0);request_error=-ENOENT;assert(bu64253_probe(c)==-ENOENT);assert(!lookups&&!enables&&!writes);complete_clean(c);
 invalid(first,0,-EINVAL);invalid(first,19,-EINVAL);memcpy(bad,first,20);bad[20]=0;invalid(bad,21,-EINVAL);
 static const unsigned int changes[][2]={{0,0},{4,2},{5,2},{6,1},{7,1},{8,0xe0},{9,0},{10,0},{12,0xd0},{13,0},{14,0},{16,0xc8},{17,0},{18,0}};
 for(unsigned int i=0;i<sizeof(changes)/sizeof(changes[0]);i++){memcpy(bad,first,20);bad[changes[i][0]]=changes[i][1];invalid(bad,20,-EINVAL);}
 c=fresh(first,20);property_error=-EINVAL;assert(bu64253_probe(c)==-EINVAL);assert(!requests&&!lookups&&!enables&&!writes);complete_clean(c);
 c=fresh(first,20);request_error=-EIO;assert(bu64253_probe(c)==-EIO);assert(!lookups&&!enables&&!writes);complete_clean(c);
 /* Fail every resource-registration stage and the unmatched-driver path. */
 for(int fault=0;fault<4;fault++) {
  c=fresh(first,20);if(fault==0)lookup_error=-EPROBE_DEFER;else if(fault==1)ctrl_error=-ENOMEM;else if(fault==2)entity_error=-ENOMEM;else async_error=-EINVAL;
  assert(bu64253_probe(c)<0);assert(!enables&&!writes);complete_clean(c);
 }
 c=fresh(first,20);probe(c);remove_driver(c);complete_clean(c);
 /* Each successful registration owns one ref. Rejected/duplicate callback paths cannot drop the base. */
 c=fresh(first,20);struct bu64253 *l=probe(c);
 for(int i=0;i<3;i++){assert(!register_node(l));assert(l->ref.refs==2);assert(bu64253_registered(&l->sd)==-EBUSY&&l->ref.refs==2);v4l2_async_unregister_subdev(&l->sd);assert(l->ref.refs==1);bu64253_release(&l->sd);assert(l->ref.refs==1);}
 remove_driver(c);complete_clean(c);
 /* Unregister with an open node, then close before driver remove. */
 c=fresh(first,20);l=probe(c);assert(!register_node(l)&&!open_node(l));v4l2_async_unregister_subdev(&l->sd);
 assert(bu64253_registered(&l->sd)==-EBUSY);close_node(&c->dev.binding);assert(l->ref.refs==1);remove_driver(c);complete_clean(c);
 /* Remove with two old FDs: deferred controls/regulator/free, no late PM call, rebind is rejected until final close. */
 c=fresh(first,20);l=probe(c);assert(!register_node(l)&&!open_node(l)&&!open_node(l));remove_driver(c);
 assert(l->ref.refs==1&&l->removing&&!l->quarantined&&c->dev.refs==2&&!ctrl_frees&&!entity_frees&&!regulator_put_calls&&!frees);
 assert(!c->dev.usage&&pm_puts_noidle==2&&module_state.refs==1);
 unsigned int gets=pm_gets, put=pm_puts, idle=pm_puts_noidle, calls=writes;
 assert(bu64253_probe(c)==-EBUSY);assert(!bu64253_close(&l->sd,NULL)); /* Direct callback models a stale close without touching PM; wrapper below counts actual FDs. */
 assert(pm_gets==gets&&pm_puts==put&&pm_puts_noidle==idle&&writes==calls);
 focus.handler=&l->ctrls;focus.id=V4L2_CID_FOCUS_ABSOLUTE;focus.val=123;mutex_lock(&l->lock);assert(bu64253_set_ctrl(&focus)==-ENODEV);mutex_unlock(&l->lock);
 assert(bu64253_open(&l->sd,NULL)==-ENODEV);c->dev.usage=777;
 close_node(&c->dev.binding);assert(c->dev.usage==777&&!regulator_put_calls);close_node(&c->dev.binding);assert(c->dev.usage==777&&regulator_put_calls==1&&ctrl_frees==1&&entity_frees==1);c->dev.usage=0;
 assert(!module_state.refs);l=probe(c);remove_driver(c);complete_clean(c);
 /* A pre-existing GOING state rejects the pre-enable pin: no new power/I2C. */
 c=fresh(first,20);l=probe(c);module_state.going=true;assert(bu64253_runtime_resume(&c->dev)==-ENODEV);assert(!enables&&!writes&&!module_state.refs);module_state.going=false;remove_driver(c);complete_clean(c);
 c=fresh(first,20);l=probe(c);assert(!register_node(l));enable_error=-EIO;assert(open_node(l)==-EIO);assert(!l->power_module_ref&&!l->supply_enabled&&module_state.refs==1&&!writes);remove_driver(c);complete_clean(c);
 /* Every init command short write/NACK balances the pre-enable module pin. */
 for(unsigned int at=1;at<=3;at++)for(int kind=0;kind<2;kind++) {
  c=fresh(first,20);l=probe(c);assert(!register_node(l));fail_write_at=at;fail_write_result=kind?-ENXIO:1;
  assert(open_node(l)==(kind?-ENXIO:-EIO));assert(!c->dev.usage&&!l->supply_enabled&&!l->power_module_ref&&enables==1&&disables==1&&module_state.refs==1);
  remove_driver(c);complete_clean(c);
 }
 /* Failed init rollback retains exactly one power pin; retries neither accumulate nor silently put it. */
 for(unsigned int at=1;at<=3;at+=2) {
  c=fresh(first,20);l=probe(c);assert(!register_node(l));fail_write_at=at;fail_write_result=-ENXIO;disable_error=-EIO;
  assert(open_node(l)==-ENXIO&&l->supply_enabled&&l->power_module_ref&&module_state.refs==2&&!c->dev.usage);
  assert(open_node(l)==-EIO&&enables==1&&module_state.refs==2);
  disable_error=0;fail_write_at=0;assert(!open_node(l)&&enables==2&&module_state.refs==2);close_node(&c->dev.binding);remove_driver(c);complete_clean(c);
 }
 assert(!live_allocations&&!module_state.refs&&list_empty(&bu64253_instances));
 /* Quarantine cases deliberately remain reachable until process exit, as in the candidate's until-reboot policy. */
 for(int old_fd=0;old_fd<2;old_fd++) {
  c=fresh(first,20);l=probe(c);assert(!register_node(l)&&!open_node(l));
  if(!old_fd){close_node(&c->dev.binding);disable_error=-EIO;assert(bu64253_runtime_suspend(&c->dev)==-EIO&&l->supply_enabled&&l->power_module_ref);}
  disable_error=-EIO;remove_driver(c);assert(l->quarantined&&l->supply_enabled&&l->power_module_ref);
  assert(c->dev.refs==2&&c->dev.regulator.handles==1&&c->dev.regulator.enabled==1&&!regulator_put_calls&&!ctrl_frees&&!entity_frees);
  assert(l->ref.refs==(old_fd?2:1));unsigned int kept=module_state.refs;assert(kept>=1);assert(bu64253_probe(c)==-EBUSY);
  unsigned int pm=pm_gets+pm_puts+pm_puts_noidle;if(old_fd)close_node(&c->dev.binding);assert(pm_gets+pm_puts+pm_puts_noidle==pm);
  assert(l->ref.refs==1&&module_state.refs==kept-(old_fd?1:0));assert(!regulator_put_calls&&!warnings);completed_cases++;
 }
 assert(live_allocations==2&&module_state.refs==2&&!warnings);
 printf("LIFETIME_C_RESULT cases=%u invalid_format_or_missing=18 init_short_nack=6 init_disable_retry=2 quarantined=2 expected_power_pins=2 warnings=0 result=0\n",completed_cases);
 return 0;
}
'''
preamble = preamble.replace('#define I2C_FUNC_I2C 1', '#define EPROBE_DEFER 517\n#define I2C_FUNC_I2C 1')
code = preamble + '\n' + body + '\n' + core_release + '\n' + main
attempt = 1
while (PRIVATE / ('lifetime-c-compile-r' + str(attempt) + '-private.log')).exists():
    attempt += 1
harness = PRIVATE / ('lifetime-c-host-r' + str(attempt) + '-private.c')
binary = PRIVATE / ('lifetime-c-host-r' + str(attempt) + '-asan')
harness.write_text(code)
start = time.monotonic()
cc = subprocess.run(['gcc', '-std=gnu11', '-g', '-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                     '-fno-pie', '-no-pie', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', str(harness), '-o', str(binary)],capture_output=True)
(PRIVATE / ('lifetime-c-compile-r' + str(attempt) + '-private.log')).write_bytes(cc.stdout+cc.stderr)
if cc.returncode:
    print((cc.stdout+cc.stderr).decode());raise SystemExit(cc.returncode)
env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1:strict_string_checks=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
run = subprocess.run([str(binary), str(PRIVATE / 'imx319-bu64253-init.bin'), str(PRIVATE / 's5k3m5sx-bu64253-init.bin')],capture_output=True,env=env,timeout=30)
(PRIVATE / ('lifetime-c-run-r' + str(attempt) + '-private.log')).write_bytes(run.stdout+run.stderr)
if run.returncode:
    print((run.stdout+run.stderr).decode());raise SystemExit(run.returncode)
assert b'result=0' in run.stdout
report = dict(stage=455, attempt=attempt, candidate='BU64253 lifetime r3',
              scope='unchanged candidate C section with sequential lifetime/PM/module/list stubs and ASAN+UBSAN',
              source_sha256=hashlib.sha256(text.encode()).hexdigest(),
              extracted_c_sha256=hashlib.sha256(body.encode()).hexdigest(),
              original_candidate_c_bodies_unmodified=True,
              dependency_0064_actual_core_function_sha256=hashlib.sha256(core_release.encode()).hexdigest(),
              compile_exit=cc.returncode, run_exit=run.returncode,
              result=run.stdout.decode().strip(), elapsed_seconds=round(time.monotonic()-start,3),
              invalid_format_or_missing_cases=18, init_short_write_or_nack_cases=6,
              valid_firmware_init_command_bytes_checked=True,
              init_disable_failure_retention_and_retry_cases=2, retained_quarantine_cases=2,
              quarantined_objects_and_power_module_pins_remain_reachable_at_exit=2,
              pre_enable_module_going_refusal_checked=True,
              old_fd_rebind_refusal_and_late_close_no_pm_checked=True,
              driver_framework_device_regulator_reference_assertions_checked=True,
              kernel_framework_concurrency_lockdep_pm_or_hardware_tested=False,
              actual_module_unload_or_sysfs_unbind_tested=False,
              sdk_or_phone_accessed=False, passed=True)
(HERE / ('lifetime-c-r' + str(attempt) + '-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
(HERE / 'lifetime-c-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
