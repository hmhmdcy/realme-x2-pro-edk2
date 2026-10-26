"""Execute candidate C functions with bus/GPIO faults; no device access."""
from pathlib import Path
import ast,hashlib,json,os,re,resource,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel232/host-tests');P.mkdir(mode=0o700,exist_ok=True)
mfd=(R/'qcom-pm8008.c').read_text();provider=(R/'reset-realme-rmx1931-pm8008.c').read_text()
def fn(src,name):
 pos=src.index(name+'(');start=src.rfind('\nstatic ',0,pos)+1;body=src.index('{',pos);depth=1;end=body+1
 while depth:
  depth+=(src[end]=='{')-(src[end]=='}');end+=1
 return src[start:end]+'\n'
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def run(name,source,negative=False):
 c=P/(name+'.c');binary=P/name;c.write_text(source)
 build=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function',
  '-Wno-unused-variable','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(c),'-o',str(binary)],capture_output=True)
 (P/(name+'-compile-private.log')).write_bytes(build.stdout+build.stderr)
 assert build.returncode==0,name+' compile failed: '+build.stderr.decode()[-1800:]
 result=subprocess.run([str(binary)],capture_output=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1'),preexec_fn=no_core)
 (P/(name+'-run-private.log')).write_bytes(result.stdout+result.stderr)
 if negative:
  assert result.returncode==-6 and b'Assertion' in result.stderr,(name,result.returncode,result.stderr[-1500:])
  return dict(assertion_rejected=True)
 assert result.returncode==0,(name,result.returncode,result.stderr[-1800:])
 return json.loads(result.stdout)

# Reuse the 195 fault cases against actual232 identity/address functions,
# through each of the two actual backend branches (GPIO and reset controller).
tree=ast.parse((R.parent/'kernel195/test-pmic-address.py').read_text());old={}
for item in tree.body:
 if isinstance(item,ast.Assign) and isinstance(item.value,ast.Constant) and isinstance(item.value.value,str):
  for target in item.targets:
   if isinstance(target,ast.Name):old[target.id]=item.value.value
stub=old['stub'].replace('struct gpio_desc { int unused; };','struct gpio_desc { int unused; };\nstruct reset_control { int unused; };')
stub+='''
struct pm8008_reset { struct device *dev; struct gpio_desc *gpio; struct reset_control *control; };
static int backend;static struct reset_control reset_control;
static int reset_control_assert(struct reset_control *r) { assert(r==&reset_control);return gpiod_direction_output(&reset_gpio,1); }
static int reset_control_deassert(struct reset_control *r) { assert(r==&reset_control);return gpiod_direction_output(&reset_gpio,0); }
'''
block='''
#define PM8008_FACTORY_ADDRESS 8
#define PM8008_ASSIGNED_ADDRESS 4
#define PM8008_SID_CONFIG 0x0644
'''+''.join(fn(mfd,n) for n in ['pm8008_has_reset','pm8008_set_reset','pm8008_read_identity','pm8008_initialize_address'])
tests=old['tests'].split(' start();get_error=-517;')[0]
tests=tests.replace('pm8008_initialize_address(&client,g)',
 'pm8008_initialize_address(&client,&(struct pm8008_reset){.gpio=backend?NULL:g,.control=backend&&g?&reset_control:NULL})')
tests=tests.replace('int main(void) {','static void run_backend(void) {')
tests+='''
}
int main(void) { backend=0;run_backend();backend=1;run_backend();printf("{\\"legacy_address_cases_both_backends\\":%d}\\n",cases);return 0; }
'''
results=dict(address=run('address-both-backends',stub+block+tests))

common=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define EPROBE_DEFER 517
#define READ_ONCE(x) (x)
#define GFP_KERNEL 0
#define IS_ERR(x) ((uintptr_t)(x)>(uintptr_t)-4096)
#define PTR_ERR(x) ((int)(intptr_t)(x))
#define ARRAY_SIZE(x) ((int)(sizeof(x)/sizeof((x)[0])))
#define dev_err(d,...) do { (void)(d); } while(0)
#define dev_info(d,...) do { (void)(d); } while(0)
struct mutex { int depth; };
static void mutex_lock(struct mutex *m) { assert(!m->depth);m->depth=1; }
static void mutex_unlock(struct mutex *m) { assert(m->depth);m->depth=0; }
struct device_driver { int id; };
enum { DL_DEV_NO_DRIVER,DL_DEV_PROBING,DL_DEV_DRIVER_BOUND,DL_DEV_UNBINDING };
struct device { int bound,locked;struct { int status; } links;struct device_driver *driver; };
struct device_link { int value; };
#define DL_FLAG_AUTOPROBE_CONSUMER 16
static int link_calls,link_fail;
static struct device_link link;
static void device_lock(struct device *d) { assert(!d->locked);d->locked=1; }
static void device_unlock(struct device *d) { assert(d->locked);d->locked=0; }
static int device_is_bound(struct device *d) { assert(d->locked);return d->bound; }
static struct device_link *device_link_add(struct device *a,struct device *b,int flags) {
 assert(a!=b && b->locked && flags==DL_FLAG_AUTOPROBE_CONSUMER);link_calls++;return link_fail?NULL:&link;
}
'''
link_tests=r'''
int main(void) {
 struct device_driver expected={0},wrong={0};struct device dev={0},sup={.bound=1,.links={DL_DEV_DRIVER_BOUND},.driver=&expected};
 assert(!pm8008_link_bound_supplier(&dev,&sup,&expected));assert(link_calls==1 && !sup.locked);
 sup.links.status=DL_DEV_UNBINDING;assert(pm8008_link_bound_supplier(&dev,&sup,&expected)==-EPROBE_DEFER);assert(link_calls==1);
 sup.links.status=DL_DEV_PROBING;assert(pm8008_link_bound_supplier(&dev,&sup,&expected)==-EPROBE_DEFER);
 sup.links.status=DL_DEV_DRIVER_BOUND;sup.bound=0;assert(pm8008_link_bound_supplier(&dev,&sup,&expected)==-EPROBE_DEFER);
 sup.bound=1;sup.driver=&wrong;assert(pm8008_link_bound_supplier(&dev,&sup,&expected)==-EINVAL);
 assert(!pm8008_link_bound_supplier(&dev,&sup,NULL));link_fail=1;assert(pm8008_link_bound_supplier(&dev,&sup,NULL)==-EINVAL);
 assert(pm8008_link_bound_supplier(&dev,&dev,NULL)==-EINVAL);assert(!dev.locked && !sup.locked && link_calls==3);
 puts("{\"supplier_link_cases\":8}");return 0;
}
'''
link_fn=fn(mfd,'pm8008_link_bound_supplier')
results['link']=run('supplier-state',common+link_fn+link_tests)
mutant=link_fn.replace(' ||\n\t    READ_ONCE(supplier->links.status) != DL_DEV_DRIVER_BOUND','')
assert mutant!=link_fn
results['link_negative_control']=run('supplier-without-unbind-guard',common+mutant+link_tests,True)

provider_stub=common+r'''
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
struct gpio_desc { int cached,fail,read_error; };
struct reset_controller_dev { struct device *dev; };
static int gpio_calls;static int gpio_ids[32];static struct gpio_desc *p_gpio;
static int gpiod_direction_output(struct gpio_desc *g,int value) {
 assert(gpio_calls<32);gpio_ids[gpio_calls++]=g==p_gpio?0:1;
 g->cached=value; /* real SPMI controller updates software cache before I/O */
 return g->fail;
}
static int gpiod_get_value_cansleep(struct gpio_desc *g) { return g->read_error?g->read_error:g->cached; }
'''
start=provider.index('enum rmx1931_pm8008_reset_id');end=provider.index('static struct rmx1931_pm8008_resets *',start)
provider_block=provider[start:end]+''.join(fn(provider,n) for n in ['to_rmx1931_pm8008_resets','rmx1931_pm8008_set_reset','rmx1931_pm8008_assert','rmx1931_pm8008_deassert','rmx1931_pm8008_status','rmx1931_pm8008_hold'])
provider_tests=r'''
int main(void) {
 struct device dev={0};struct gpio_desc p={.cached=1},q={0};p_gpio=&p;
 struct rmx1931_pm8008_resets r={.rcdev={.dev=&dev},.p=&p,.q=&q,.p_state_valid=true,.p_asserted=true};
 assert(!rmx1931_pm8008_deassert(&r.rcdev,1));assert(gpio_calls==1 && !q.cached);
 assert(!rmx1931_pm8008_deassert(&r.rcdev,0));p.cached=1; /* a misleading cache cannot override tracked P */
 assert(rmx1931_pm8008_assert(&r.rcdev,1)==-EBUSY);assert(gpio_calls==2);
 p.fail=-EIO;assert(rmx1931_pm8008_assert(&r.rcdev,0)==-EIO);assert(p.cached==1 && !r.p_state_valid);
 assert(rmx1931_pm8008_status(&r.rcdev,0)==-EIO);
 assert(rmx1931_pm8008_assert(&r.rcdev,1)==-EIO);assert(gpio_calls==3);
 p.fail=0;assert(!rmx1931_pm8008_assert(&r.rcdev,0));assert(r.p_state_valid && r.p_asserted);
 p.read_error=-ETIMEDOUT;assert(rmx1931_pm8008_deassert(&r.rcdev,1)==-ETIMEDOUT);assert(gpio_calls==4);
 p.read_error=0;p.cached=0;assert(rmx1931_pm8008_assert(&r.rcdev,1)==-EBUSY);
 p.cached=1;assert(!rmx1931_pm8008_assert(&r.rcdev,1));assert(q.cached==1);
 assert(rmx1931_pm8008_assert(&r.rcdev,2)==-EINVAL);assert(rmx1931_pm8008_status(&r.rcdev,2)==-EINVAL);
 p.fail=-EIO;int n=gpio_calls;rmx1931_pm8008_hold(&r);assert(gpio_calls==n+1 && gpio_ids[n]==0);
 p.fail=0;n=gpio_calls;rmx1931_pm8008_hold(&r);assert(gpio_calls==n+2 && gpio_ids[n]==0 && gpio_ids[n+1]==1);
 p.fail=-EIO;assert(rmx1931_pm8008_deassert(&r.rcdev,0)==-EIO);assert(!r.p_state_valid && !p.cached);
 assert(rmx1931_pm8008_deassert(&r.rcdev,1)==-EIO);assert(!r.lock.depth);
 puts("{\"provider_fault_and_order_cases\":14}");return 0;
}
'''
results['provider']=run('provider-cached-spmi-failure',provider_stub+provider_block+provider_tests)
mutant=provider_block.replace('if (!priv->p_state_valid)', 'if (false)')
assert mutant!=provider_block
results['provider_negative_control']=run('provider-without-validity-guard',provider_stub+mutant+provider_tests,True)

# Exercise actual reset orchestration. OF lookup and device lifetime are mocked;
# Linux device-core teardown itself requires a separate native test.
orchestration_stub=common+r'''
struct device_node { int value; };
struct gpio_desc { int value; };struct reset_control { int value; };
struct i2c_client { struct device dev; int addr; };
struct pm8008_reset { struct device *dev;struct gpio_desc *gpio;struct reset_control *control; };
static struct mutex pm8008_address_lock;static bool experimental_p_address_only;
static struct device_node node;static struct pm8008_reset allocated;
static int is_p,static_error,get_error,action_error,link_error,init_error,id_error,reset_error;
static int reset_calls,reset_values[8],id_calls,init_calls,get_calls,node_puts,action_set,link_count;
static void (*action)(void *);static void *action_data;
static struct device_node *pm8008_address_supplier_node(struct i2c_client *c) {
 (void)c;return static_error?(void *)(intptr_t)static_error:is_p?&node:NULL;
}
static void *devm_kzalloc(struct device *d,size_t size,int flags) { (void)d;(void)flags;assert(size==sizeof(allocated));memset(&allocated,0,size);return &allocated; }
static int pm8008_get_reset(struct i2c_client *c,struct pm8008_reset *r) { get_calls++;r->dev=&c->dev;return get_error; }
static int pm8008_set_reset(struct pm8008_reset *r,bool value) { assert(r==&allocated && !pm8008_address_lock.depth);reset_values[reset_calls++]=value;return reset_error; }
static int devm_add_action_or_reset(struct device *d,void (*fn)(void *),void *data) {
 (void)d;if(action_error){fn(data);return action_error;}action=fn;action_data=data;action_set++;return 0;
}
static int pm8008_link_address_supplier(struct i2c_client *c,struct device_node *n) {
 (void)c;assert(n==&node && !pm8008_address_lock.depth);link_count++;return link_error;
}
static int pm8008_initialize_address(struct i2c_client *c,struct pm8008_reset *r) {
 (void)c;(void)r;assert(pm8008_address_lock.depth);init_calls++;return init_error;
}
static int pm8008_read_identity(struct i2c_client *c,int addr) { assert(c->addr==addr && addr==8 && pm8008_address_lock.depth);id_calls++;return id_error; }
static void of_node_put(struct device_node *n) { if(n){assert(n==&node);node_puts++;} }
'''
orchestration_tests=r'''
static void start(void) {
 is_p=1;experimental_p_address_only=true;static_error=get_error=action_error=link_error=init_error=id_error=reset_error=0;
 reset_calls=id_calls=init_calls=get_calls=node_puts=action_set=link_count=0;action=NULL;
}
static void cleanup(void) { if(action)action(action_data);assert(!pm8008_address_lock.depth); }
int main(void) {
 struct i2c_client c={.addr=8};
 start();experimental_p_address_only=false;assert(pm8008_reset_and_address(&c)==-EOPNOTSUPP);assert(!get_calls && !reset_calls && !id_calls && node_puts==1);
 start();static_error=-EINVAL;assert(pm8008_reset_and_address(&c)==-EINVAL);assert(!get_calls && !node_puts);
 start();get_error=-EPROBE_DEFER;assert(pm8008_reset_and_address(&c)==-EPROBE_DEFER);assert(!reset_calls && node_puts==1);
 start();action_error=-ENOMEM;assert(pm8008_reset_and_address(&c)==-ENOMEM);assert(reset_calls==1 && reset_values[0]==1 && !init_calls);
 start();reset_error=-EIO;assert(pm8008_reset_and_address(&c)==-EIO);assert(!link_count && !init_calls);cleanup();assert(reset_calls==2);
 start();link_error=-EPROBE_DEFER;assert(pm8008_reset_and_address(&c)==-EPROBE_DEFER);assert(reset_calls==1 && reset_values[0]==1 && !init_calls);cleanup();assert(reset_values[1]==1);
 start();init_error=-EIO;assert(pm8008_reset_and_address(&c)==-EIO);assert(!id_calls);cleanup();assert(reset_values[1]==1);
 start();id_error=-ENODEV;assert(pm8008_reset_and_address(&c)==-ENODEV);assert(init_calls==1 && id_calls==1);cleanup();assert(reset_values[1]==1);
 start();assert(!pm8008_reset_and_address(&c));assert(init_calls==1 && id_calls==1 && reset_calls==1 && link_count==1);cleanup();assert(reset_values[1]==1);
 start();is_p=0;experimental_p_address_only=false;assert(!pm8008_reset_and_address(&c));assert(init_calls==1 && !id_calls && !action_set && !reset_calls && !link_count && !node_puts);
 puts("{\"orchestration_fault_cases\":10}");return 0;
}
'''
results['orchestration']=run('p-reset-orchestration',orchestration_stub+fn(mfd,'pm8008_hold_reset')+fn(mfd,'pm8008_reset_and_address')+orchestration_tests)
# Test the unchanged actual probe entry through the first child setup boundary.
# The suffix is an observable sentinel, not a model of the regulator subsystem.
probe=fn(mfd,'pm8008_probe');boundary='\tdummy = devm_i2c_new_dummy_device('
assert probe.count(boundary)==1
prefix=probe.split(boundary)[0]+'\tchild_boundary++;return 99;\n}\n'
entry_stub=common+r'''
struct i2c_client { struct device dev; };
static bool experimental_p_address_only;static int is_p,init_ret,child_boundary,init_calls;
static int pm8008_reset_and_address(struct i2c_client *c) { (void)c;init_calls++;return init_ret; }
static int device_property_present(struct device *d,const char *s) { (void)d;assert(!strcmp(s,"qcom,address-setup-supplier"));return is_p; }
static int dev_err_probe(struct device *d,int ret,const char *s) { (void)d;(void)s;return ret; }
'''
entry_tests=r'''
int main(void) {
 struct i2c_client c={0};experimental_p_address_only=true;is_p=1;
 assert(!pm8008_probe(&c));assert(!child_boundary);
 init_ret=-ENODEV;assert(pm8008_probe(&c)==-ENODEV);assert(!child_boundary);
 init_ret=-EOPNOTSUPP;experimental_p_address_only=false;assert(pm8008_probe(&c)==-EOPNOTSUPP);assert(!child_boundary);
 init_ret=0;is_p=0;assert(pm8008_probe(&c)==99);assert(child_boundary==1);
 experimental_p_address_only=true;assert(pm8008_probe(&c)==99);assert(child_boundary==2 && init_calls==5);
 puts("{\"actual_probe_entry_boundary_cases\":5}");return 0;
}
'''
results['probe_entry']=run('probe-child-boundary',entry_stub+prefix+entry_tests)
mutant=prefix.replace('if (experimental_p_address_only &&','if (false &&')
assert mutant!=prefix
results['probe_entry_negative_control']=run('probe-without-child-guard',entry_stub+mutant+entry_tests,True)
report=dict(stage=232,actual_candidate_function_bodies_executed=True,
 mfd_sha256=hashlib.sha256(mfd.encode()).hexdigest(),provider_sha256=hashlib.sha256(provider.encode()).hexdigest(),
 results=results,asan_ubsan_passed=True,no_native_faults_injected=True,
 native_device_core_unbind_and_real_gpio_voltage_not_proven=True)
(R/'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
