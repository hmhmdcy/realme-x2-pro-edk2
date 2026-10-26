"""Compile the actual CCI PM/removal callbacks with shared-supply and failure injection."""
from pathlib import Path
import hashlib,json,subprocess,sys
import host
R=Path(__file__).resolve().parent;s=(R/'i2c-qcom-cci.c').read_text()
def block(start):
 a=s.index(start);b=s.index('{',a);depth=1;i=b+1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]+'\n'
code=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define __maybe_unused
struct cci;
struct device { struct cci *data; int active,usage; };
struct platform_device { struct device dev; };
struct regulator { int refs,fail_enable,fail_disable; };
struct clocks { int count,fail; };
struct i2c_adapter { int registered; };
struct master { struct cci *cci; struct i2c_adapter adap; };
struct cci_data { int num_masters; };
struct cci { struct device *dev; struct regulator *vddio; bool io_enabled,clocks_enabled; int nclocks; struct clocks *clocks; const struct cci_data *data; struct master master[2]; };
static int warnings,halted,inits,force_resume_error;static char events[100];static int n_events;
static void event(char c){assert(n_events<99);events[n_events++]=c;events[n_events]=0;}
static int regulator_enable(struct regulator *r){event('V');if(r->fail_enable){--r->fail_enable;return -EIO;}++r->refs;return 0;}
static int regulator_disable(struct regulator *r){event('v');if(r->fail_disable){--r->fail_disable;return -EIO;}assert(r->refs>0);--r->refs;return 0;}
static int clk_bulk_prepare_enable(int n,struct clocks *c){assert(n==1);event('C');if(c->fail){--c->fail;return -ERANGE;}assert(!c->count);++c->count;return 0;}
static void clk_bulk_disable_unprepare(int n,struct clocks *c){assert(n==1 && c->count==1);event('c');--c->count;}
static struct cci *dev_get_drvdata(struct device *d){return d->data;}
static struct cci *platform_get_drvdata(struct platform_device *p){return p->dev.data;}
static void cci_init(struct cci *c){assert(c->clocks_enabled && (!c->vddio || c->io_enabled));event('I');++inits;}
#define dev_err(dev,...) do{(void)(dev);++warnings;}while(0)
#define dev_warn(dev,...) do{(void)(dev);++warnings;}while(0)
'''
for name in ['static int cci_enable_clocks(', 'static void cci_disable_clocks(', 'static int cci_enable_io(', 'static int cci_disable_io(', 'static void cci_release_power(', 'static int __maybe_unused cci_suspend_runtime(', 'static int __maybe_unused cci_resume_runtime(']:code+=block(name)
code+=r'''
static int pm_runtime_resume_and_get(struct device *d){int r;if(force_resume_error)return force_resume_error;if(!d->active){r=cci_resume_runtime(d);if(r)return r;d->active=1;}++d->usage;return 0;}
static void pm_runtime_put_noidle(struct device *d){assert(d->usage>0);--d->usage;}
static void i2c_del_adapter(struct i2c_adapter *a){assert(a->registered);a->registered=0;event('D');}
static int cci_halt(struct cci *c,int i){assert(i>=0 && i<2 && c->clocks_enabled);assert(!c->vddio || c->io_enabled);event('H');++halted;return 0;}
'''
code+=block('static void cci_remove(')
code+=r'''
static struct platform_device p;static struct cci c,c2;static struct regulator io;static struct clocks clk,clk2;static struct device d2;static const struct cci_data cfg={2};
static void setup(struct cci *x,struct device *d,struct clocks *k){memset(x,0,sizeof(*x));memset(d,0,sizeof(*d));memset(k,0,sizeof(*k));x->dev=d;d->data=x;x->vddio=&io;x->nclocks=1;x->clocks=k;x->data=&cfg;for(int i=0;i<2;++i){x->master[i].cci=x;x->master[i].adap.registered=1;}}
static void reset(void){memset(&io,0,sizeof(io));setup(&c,&p.dev,&clk);warnings=halted=inits=force_resume_error=n_events=0;events[0]=0;}
int main(void){int cases=0;
 reset();c.vddio=NULL;assert(!cci_resume_runtime(c.dev));assert(!strcmp(events,"CI") && clk.count==1 && !io.refs);assert(!cci_suspend_runtime(c.dev));assert(!clk.count);++cases;
 reset();assert(!cci_resume_runtime(c.dev));assert(!strcmp(events,"VCI") && io.refs==1 && clk.count==1);assert(!cci_suspend_runtime(c.dev));assert(!strcmp(events,"VCIvc") && !io.refs && !clk.count);++cases;
 reset();io.fail_enable=1;assert(cci_resume_runtime(c.dev)==-EIO);assert(!io.refs && !clk.count && !inits && !c.io_enabled);++cases;
 reset();clk.fail=1;assert(cci_resume_runtime(c.dev)==-ERANGE);assert(!io.refs && !clk.count && !c.io_enabled && !c.clocks_enabled);++cases;
 reset();clk.fail=1;io.fail_disable=1;assert(cci_resume_runtime(c.dev)==-ERANGE);assert(io.refs==1 && c.io_enabled && !clk.count && warnings==1);assert(!cci_resume_runtime(c.dev));assert(io.refs==1 && clk.count==1 && n_events==5 && !strcmp(events,"VCvCI"));cci_release_power(&c);assert(!io.refs && !clk.count);++cases;
 reset();assert(!cci_resume_runtime(c.dev));io.fail_disable=1;assert(cci_suspend_runtime(c.dev)==-EIO);assert(io.refs==1 && clk.count==1 && c.io_enabled && c.clocks_enabled);assert(!cci_suspend_runtime(c.dev));assert(!io.refs && !clk.count);++cases;
 reset();assert(!cci_enable_io(&c));assert(!cci_enable_io(&c));assert(io.refs==1);assert(!cci_enable_clocks(&c));assert(!cci_enable_clocks(&c));assert(clk.count==1);cci_release_power(&c);cci_release_power(&c);assert(!io.refs && !clk.count);++cases;
 reset();setup(&c2,&d2,&clk2);assert(!cci_resume_runtime(c.dev));assert(!cci_resume_runtime(c2.dev));assert(io.refs==2);assert(!cci_suspend_runtime(c.dev));assert(io.refs==1 && clk2.count==1 && c2.io_enabled);assert(!cci_suspend_runtime(c2.dev));assert(!io.refs);++cases;
 reset();cci_remove(&p);assert(halted==2 && !p.dev.usage && p.dev.active && io.refs==1 && clk.count==1);assert(!strcmp(events,"VCIDHDH"));cci_release_power(&c);assert(!io.refs && !clk.count);++cases;
 reset();assert(!cci_resume_runtime(c.dev));p.dev.active=1;p.dev.usage=1;n_events=0;events[0]=0;cci_remove(&p);assert(halted==2 && p.dev.usage==1 && inits==1 && !strcmp(events,"DHDH"));cci_release_power(&c);assert(!io.refs && !clk.count);++cases;
 reset();force_resume_error=-EIO;cci_remove(&p);assert(!halted && !p.dev.usage && !io.refs && !clk.count && warnings==1 && !strcmp(events,"DD"));cci_release_power(&c);++cases;
 reset();assert(!cci_resume_runtime(c.dev));io.fail_disable=1;cci_release_power(&c);assert(io.refs==1 && c.io_enabled && !clk.count && warnings==1);cci_release_power(&c);assert(!io.refs && !c.io_enabled && !clk.count);++cases;
 reset();assert(!cci_enable_io(&c));cci_release_power(&c);assert(!io.refs && !clk.count);++cases;
 reset();assert(!cci_enable_clocks(&c));cci_release_power(&c);assert(!io.refs && !clk.count);++cases;
 printf("{\"actual_pm_and_remove_cases\":%d,\"passed\":true}\n",cases);return 0;
}
'''
attempt=int(sys.argv[1]) if sys.argv[1:] else 1;assert attempt in [1,2]
out=host.PRIVATE/('cci-power-host-r'+str(attempt));out.mkdir(mode=0o700);(out/'test.c').write_text(code)
q=subprocess.run(['cc','-std=gnu11','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all',str(out/'test.c'),'-o',str(out/'test')],capture_output=True);(out/'compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
q=subprocess.run([str(out/'test')],capture_output=True);(out/'run-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
d=json.loads(q.stdout);d.update(stage=276,source_sha256=hashlib.sha256(s.encode()).hexdigest(),actual_callbacks_compiled=True,ubsan=True,physical_faults_not_injected=True,shared_supply_references_tested=True)
(R/'cci-power-callback-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
