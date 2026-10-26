"""Fault-test actual PMIC enable, reset conflict and supplier-link functions."""
from pathlib import Path
import ast
import hashlib
import json
import os
import resource
import subprocess

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel267/common-power-tests-r2');P.mkdir(mode=0o700)
mfd=(R/'qcom-pm8008.c').read_text();reg=(R/'qcom-pm8008-regulator.c').read_text()
def fn(src,name):
    pos=src.index(name+'(');start=src.rfind('\nstatic ',0,pos)+1
    body=src.index('{',pos);depth=1;end=body+1
    while depth:depth+=(src[end]=='{')-(src[end]=='}');end+=1
    return src[start:end]+'\n'
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def run(name,text,negative=False):
    p=P/(name+'.c');p.write_text(text);binary=p.with_suffix('')
    q=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable',
      '-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(p),'-o',str(binary)],capture_output=True)
    (P/(name+'-compile-private.log')).write_bytes(q.stdout+q.stderr)
    assert q.returncode==0,(name,q.stderr.decode()[-1800:])
    q=subprocess.run([str(binary)],capture_output=True,preexec_fn=no_core,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1'))
    (P/(name+'-run-private.log')).write_bytes(q.stdout+q.stderr)
    if negative:
        assert q.returncode!=0 and b'Assertion' in q.stderr,(name,q.stderr[-1000:])
        return dict(rejected=True)
    assert q.returncode==0 and not q.stderr,(name,q.stderr[-1000:])
    return json.loads(q.stdout)

prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
struct regmap { int unused; };
struct pm8008_regulator { struct regmap *regmap;unsigned int base; };
struct regulator_dev { struct pm8008_regulator *data; };
static bool enabled,partial;
static int write_error,poll_error,cleanup_error,enable_calls,poll_calls,disable_calls;
#define LDO_STATUS_REG 8
#define ENABLE_BIT 128
#define rdev_get_drvdata(r) ((r)->data)
#define rdev_get_dev(r) (r)
#define dev_err(d,...) ((void)(d))
static int regulator_enable_regmap(struct regulator_dev *r) {
 assert(r);enable_calls++;if(!write_error||partial)enabled=true;return write_error;
}
static int regulator_disable_regmap(struct regulator_dev *r) {
 assert(r);disable_calls++;if(!cleanup_error)enabled=false;return cleanup_error;
}
static int poll_ready(struct regmap *m,unsigned int addr,unsigned int *value) {
 assert(m&&addr==0x4008&&enabled);poll_calls++;*value=poll_error?0:128;return poll_error;
}
#define regmap_read_poll_timeout(m,a,v,cond,delay,timeout) poll_ready((m),(a),&(v))
'''
tests=r'''
int main(void) {
 struct regmap m={0};struct pm8008_regulator p={.regmap=&m,.base=0x4000};struct regulator_dev r={.data=&p};
 unsigned int cases=0;
 for(int w=0;w<2;w++)for(int pa=0;pa<2;pa++)for(int pe=0;pe<3;pe++)for(int ce=0;ce<2;ce++) {
  write_error=w?-EIO:0;partial=pa;poll_error=pe==0?0:pe==1?-ETIMEDOUT:-EREMOTEIO;
  cleanup_error=ce?-EIO:0;enabled=false;enable_calls=poll_calls=disable_calls=0;
  int expected=write_error?write_error:poll_error;int ret=pm8008_regulator_enable(&r);
  assert(ret==expected&&enable_calls==1&&poll_calls==(!w));
  if(expected) {assert(disable_calls==1);if(!ce)assert(!enabled);}
  else assert(enabled&&!disable_calls);
  cases++;
 }
 printf("{\"enable_fault_outcome_cases\":%u,\"cleanup_failure_remains_uncertain\":true}\n",cases);return 0;
}
'''
actual=prefix+fn(reg,'pm8008_regulator_enable')+tests
results={'enable':run('enable',actual),
 'enable-negative':run('enable-no-rollback',actual.replace('cleanup = regulator_disable_regmap(rdev);','cleanup = 0;'),True)}

prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef unsigned int u32;
struct device_node { struct device_node *parent,*supplier;unsigned int address;bool available,compatible,reset; };
struct device { struct device_node *of_node;bool initial;unsigned int initial_address; };
struct i2c_client { struct device dev; };
struct gpio_desc { bool asserted; };
struct pm8008_reset { struct device *dev;struct gpio_desc *gpio,*blocker; };
static struct device_node nodes[3];static struct gpio_desc blocker;
static int gpio_error,gpio_calls,node_puts;static bool leased;
#define GPIOD_OUT_HIGH 1
#define PTR_ERR_OR_ZERO(p) ((uintptr_t)(p)>(uintptr_t)-4096?(int)(intptr_t)(p):0)
#define of_fwnode_handle(n) (n)
static int device_property_read_u32(struct device *d,const char *name,u32 *value) {
 assert(!strcmp(name,"qcom,initial-address"));if(!d->initial)return -EINVAL;*value=d->initial_address;return 0;
}
static bool of_device_is_compatible(struct device_node *n,const char *name) { assert(!strcmp(name,"qcom,pm8008"));return n->compatible; }
static int of_property_read_u32(struct device_node *n,const char *name,u32 *value) { assert(!strcmp(name,"reg"));*value=n->address;return 0; }
static struct device_node *of_parse_phandle(struct device_node *n,const char *name,int index) {
 assert(!strcmp(name,"qcom,address-setup-supplier")&&!index);return n->supplier;
}
static void of_node_put(struct device_node *n) { if(n)node_puts++; }
static struct gpio_desc *devm_fwnode_gpiod_get_index(struct device *d,struct device_node *n,const char *name,int index,int flags,const char *label) {
 assert(d&&n==&nodes[1]&&!strcmp(name,"reset")&&!index&&flags==1&&label);gpio_calls++;
 if(gpio_error)return (void *)(intptr_t)gpio_error;
 if(!n->reset)return (void *)(intptr_t)-ENOENT;
 assert(!leased);leased=true;blocker.asserted=true;return &blocker;
}
#define for_each_available_child_of_node(root,n) for(int i=0;i<3;i++) if(((n)=&nodes[i])->available && (n)->parent==(root))
'''
tests=r'''
int main(void) {
 unsigned int cases=0;struct device_node bus={0};struct i2c_client q={.dev={.of_node=&nodes[0]}};
 struct pm8008_reset reset;
 for(int initial=0;initial<2;initial++)for(int dependent=0;dependent<2;dependent++)
 for(int valid=0;valid<2;valid++)for(int has_reset=0;has_reset<2;has_reset++)for(int err=0;err<2;err++) {
  memset(nodes,0,sizeof(nodes));memset(&reset,0,sizeof(reset));leased=false;blocker.asserted=false;gpio_calls=node_puts=0;
  q.dev.initial=initial;q.dev.initial_address=8;nodes[0].parent=&bus;
  nodes[1]=(struct device_node){.parent=&bus,.supplier=valid?&nodes[0]:NULL,.address=8,.available=dependent,.compatible=true,.reset=has_reset};
  gpio_error=err?-517:0;
  int expected=!initial||!dependent?0:!valid?-EINVAL:gpio_error?gpio_error:!has_reset?-ENOENT:0;
  int ret=pm8008_hold_address_conflict(&q,&reset);assert(ret==expected);
  if(initial&&dependent&&valid)assert(gpio_calls==1);
  else assert(!gpio_calls&&!leased);
  if(initial&&dependent&&valid&&!err&&has_reset)assert(leased&&blocker.asserted&&reset.blocker==&blocker);
  cases++;
 }
 printf("{\"address_conflict_cases\":%u,\"held_before_assignment\":true}\n",cases);return 0;
}
'''
actual=prefix+fn(mfd,'pm8008_hold_address_conflict')+tests
results['address-conflict']=run('address-conflict',actual)
results['address-conflict-negative']=run('address-conflict-no-gpio',actual.replace('GPIOD_OUT_HIGH, "pm8008-address-conflict"','0, "pm8008-address-conflict"'),True)

tree=ast.parse((R.parent/'kernel232/test-reset-address.py').read_text());old={}
for item in tree.body:
    if isinstance(item,ast.Assign) and isinstance(item.value,ast.Constant) and isinstance(item.value.value,str):
        for target in item.targets:
            if isinstance(target,ast.Name):old[target.id]=item.value.value
results['supplier-link']=run('supplier-link',old['common']+fn(mfd,'pm8008_link_bound_supplier')+old['link_tests'])
report=dict(stage=267,actual_functions_extracted=True,asan_ubsan=True,results=results,
 source_sha256={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['qcom-pm8008.c','qcom-pm8008-regulator.c']},
 api_outcome_models_not_real_kernel_concurrency=True,hardware_not_changed=True)
(R/'common-power-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
