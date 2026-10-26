"""Execute the exact candidate's routed power functions with faulting host APIs."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('host462_storage449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
storage.mount.mounted_build()
P=Path('/mnt/e/edk2-samurai-out/kernel462')
candidate=P/'candidate/drivers/media/i2c/imx471.c'
text=candidate.read_text();begin=text.index('/* Shared-route boards');end=text.index('static int imx471_init_shared_route',begin)
actual=text[begin:end]
prelude=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define BIT(n) (1UL << (n))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define IMX471_EXT_CLK 19200000
#define dev_err(...) ((void)0)
static int warnings;
#define WARN_ON(c) ((c) ? (++warnings,1) : 0)
enum { IMX471_VANA, IMX471_VDIG, IMX471_VIF };
struct shared { int route_owner,reset_owner,rails[3],clock; };
struct device { int unused; };
struct mux_state { struct shared *shared;int id; };
struct reset_control { struct shared *shared;int id; };
struct regulator { struct shared *shared;int id; };
struct regulator_bulk_data { struct regulator *consumer; };
struct clk { struct shared *shared; };
struct imx471 {
 struct mux_state *route;struct reset_control *reset;struct clk *img_clk;
 struct regulator_bulk_data supplies[3];struct device *dev;
 unsigned long supply_mask;bool route_selected,reset_acquired,clock_enabled;
};
static int calls,fail_at;
static int fault(void) {return ++calls==fail_at ? -EIO:0;}
static int mux_state_try_select(struct mux_state *m) {
 int ret=fault();if(ret)return ret;
 if(m->shared->route_owner)return -EBUSY;
 m->shared->route_owner=m->id;return 0;
}
static int mux_state_deselect(struct mux_state *m) {
 assert(m->shared->route_owner==m->id);
 assert(!m->shared->clock && !m->shared->reset_owner);
 for(int i=0;i<3;i++)assert(!m->shared->rails[i]);
 m->shared->route_owner=0;return 0;
}
static int reset_control_acquire(struct reset_control *r) {
 assert(r->shared->route_owner==r->id);int ret=fault();if(ret)return ret;
 assert(!r->shared->reset_owner);r->shared->reset_owner=r->id;return 0;
}
static int reset_control_assert(struct reset_control *r) {
 assert(r->shared->route_owner==r->id && r->shared->reset_owner==r->id);return fault();
}
static int reset_control_deassert(struct reset_control *r) {
 assert(r->shared->route_owner==r->id && r->shared->reset_owner==r->id);return fault();
}
static void reset_control_release(struct reset_control *r) {
 assert(r->shared->reset_owner==r->id);r->shared->reset_owner=0;
}
static int clk_set_rate(struct clk *c,unsigned long hz) {
 assert(c->shared->route_owner && hz==IMX471_EXT_CLK);return fault();
}
static int clk_prepare_enable(struct clk *c) {
 assert(c->shared->route_owner);int ret=fault();if(ret)return ret;
 assert(!c->shared->clock);c->shared->clock=1;return 0;
}
static void clk_disable_unprepare(struct clk *c) {assert(c->shared->clock==1);c->shared->clock=0;}
static int regulator_enable(struct regulator *r) {
 assert(r->shared->route_owner);int ret=fault();if(ret)return ret;
 assert(!r->shared->rails[r->id]);r->shared->rails[r->id]=1;return 0;
}
static int regulator_disable(struct regulator *r) {
 assert(r->shared->route_owner);int ret=fault();if(ret)return ret;
 assert(r->shared->rails[r->id]==1);r->shared->rails[r->id]=0;return 0;
}
static void usleep_range(unsigned long a,unsigned long b) {assert(a<=b);}
struct fixture {
 struct imx471 sensor;struct shared *shared;struct mux_state mux;struct reset_control reset;
 struct regulator regulators[3];struct clk clock;
};
static void init(struct fixture *f,struct shared *g,int id) {
 memset(f,0,sizeof(*f));f->shared=g;f->mux=(struct mux_state){g,id};
 f->reset=(struct reset_control){g,id};f->clock=(struct clk){g};
 f->sensor.route=&f->mux;f->sensor.reset=&f->reset;f->sensor.img_clk=&f->clock;
 for(int i=0;i<3;i++){f->regulators[i]=(struct regulator){g,i};f->sensor.supplies[i].consumer=&f->regulators[i];}
}
static void clean(struct fixture *f) {
 assert(!f->sensor.route_selected && !f->sensor.reset_acquired && !f->sensor.clock_enabled && !f->sensor.supply_mask);
 assert(!f->shared->route_owner && !f->shared->reset_owner && !f->shared->clock);
 for(int i=0;i<3;i++)assert(!f->shared->rails[i]);
}
'''
tests=r'''
int main(void) {
 int cases=0;
 struct shared g={0};struct fixture a,b;
 init(&a,&g,1);calls=fail_at=warnings=0;
 assert(!imx471_shared_power_on(&a.sensor));int on_calls=calls;assert(on_calls==9);
 assert(a.sensor.route_selected && a.sensor.reset_acquired && a.sensor.clock_enabled && a.sensor.supply_mask==7);
 assert(!imx471_shared_power_off(&a.sensor));clean(&a);cases++;
 init(&a,&g,1);init(&b,&g,2);calls=fail_at=0;
 assert(!imx471_shared_power_on(&a.sensor));
 assert(imx471_shared_power_on(&b.sensor)==-EBUSY);
 assert(g.route_owner==1 && !b.sensor.supply_mask && !b.sensor.reset_acquired && !b.sensor.clock_enabled);
 assert(!imx471_shared_power_off(&a.sensor));
 assert(!imx471_shared_power_on(&b.sensor));assert(g.route_owner==2);
 assert(!imx471_shared_power_off(&b.sensor));clean(&b);cases++;
 for(int fail=1;fail<=on_calls;fail++) {
  init(&a,&g,1);calls=warnings=0;fail_at=fail;
  assert(imx471_shared_power_on(&a.sensor)==-EIO);clean(&a);assert(!warnings);cases++;
 }
 for(int fail=1;fail<=4;fail++) {
  init(&a,&g,1);calls=fail_at=warnings=0;assert(!imx471_shared_power_on(&a.sensor));
  calls=0;fail_at=fail;assert(imx471_shared_power_off(&a.sensor)==-EIO);
  assert(g.route_owner==1 && a.sensor.route_selected && a.sensor.reset_acquired);
  assert(imx471_shared_power_on(&a.sensor)==-EIO);
  imx471_route_put(&a.sensor);assert(g.route_owner==1 && a.sensor.route_selected && warnings==1);
  calls=fail_at=0;assert(!imx471_shared_power_off(&a.sensor));clean(&a);cases++;
 }
 /* Probe has selected a route, but no powered resource was acquired yet. */
 init(&a,&g,1);calls=fail_at=0;assert(!imx471_route_get(&a.sensor));
 imx471_route_put(&a.sensor);clean(&a);cases++;
 printf("{\"actual_candidate_c_cases\":%d,\"power_on_failure_points\":%d,\"power_off_failure_points\":4,\"passed\":true}\n",cases,on_calls);
 return 0;
}
'''
source=P/'resource-contract-private.c';source.write_text(prelude+actual+tests)
exe=P/'resource-contract-private'
command=['cc','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(source),'-o',str(exe)]
build=subprocess.run(command,capture_output=True);(P/'resource-c-build-private.log').write_bytes(build.stdout+build.stderr)
assert build.returncode==0,(build.returncode,build.stderr.decode())
run=subprocess.run([str(exe)],capture_output=True);(P/'resource-c-run-private.log').write_bytes(run.stdout+run.stderr)
assert run.returncode==0,(run.returncode,run.stderr.decode())
result=json.loads(run.stdout)
result.update(stage=462,asan_ubsan=True,exact_candidate_functions_extracted=True,
    candidate_source_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
    extracted_functions_sha256=hashlib.sha256(actual.encode()).hexdigest(),
    references_not_hardware_voltage_simulated=True,peer_lease_refusal_and_next_owner_tested=True,
    dirty_shutdown_action_does_not_unlock=True,probe_or_remove_devres_quarantine_proven=False,
    no_claim_of_safe_unload_after_shutdown_failure=True,no_phone_sdk=True)
(HERE/'resource-c-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
