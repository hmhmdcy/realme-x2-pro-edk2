from pathlib import Path
import hashlib, json, os, re, subprocess

os.umask(0o077)
ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel176');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
manifest=json.loads((ref/'source-validation.json').read_text())
for n,h in manifest['source_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==h,n
def function(s,name):
    hit=re.search(r'^(?:static )?(?:int|void|struct\s+\w+\s*\*)\s*'+name+r'\([^;]*?\n\{',s,re.M);assert hit,name
    a=s.index('{',hit.start());b=a+1;depth=1
    while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[hit.start():b]+'\n'
def run(label,code,passed=True):
    src=out/(label+'-private.c');src.write_text(code);exe=out/(label+'-private')
    r=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread',str(src),'-o',str(exe)],capture_output=True)
    (out/(label+'-compile-private.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode()
    r=subprocess.run([str(exe)],capture_output=True);(out/(label+'-run-private.log')).write_bytes(r.stdout+r.stderr)
    assert (r.returncode==0)==passed,(label,r.stdout.decode(),r.stderr.decode())
    if passed:assert not r.stderr,r.stderr.decode()
    return r.stdout.decode().strip()

core=(k/'drivers/slimbus/core.c').read_text();mfd=(k/'drivers/mfd/wcd934x.c').read_text()
absent=function(core,'slim_report_absent')
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <pthread.h>
struct mutex{pthread_mutex_t real;int held;};
struct slim_controller{struct mutex lock;int (*get_laddr)(void);int laddr_ida;};
struct slim_device{struct slim_controller *ctrl;bool is_laddr_valid;int laddr,status;};
#define SLIM_DEVICE_STATUS_DOWN 0
static int frees;static pthread_mutex_t status_lock=PTHREAD_MUTEX_INITIALIZER;
static void mutex_lock(struct mutex *m){assert(!pthread_mutex_lock(&m->real));assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;assert(!pthread_mutex_unlock(&m->real));}
static void ida_free(int *ida,int addr){assert(*ida==1&&addr==7);*ida=0;frees++;}
static void slim_device_update_status(struct slim_device *d,int status){assert(!pthread_mutex_lock(&status_lock));d->status=status;assert(!pthread_mutex_unlock(&status_lock));}
static int manager(void){return 0;}
'''
tests=r'''
static struct slim_device d;static void *invalidate(void *p){slim_report_absent(&d);return NULL;}
int main(void){int cases=0;struct slim_controller c={0};assert(!pthread_mutex_init(&c.lock.real,NULL));
 d=(struct slim_device){.is_laddr_valid=true,.status=1,.laddr=7};slim_report_absent(&d);assert(d.is_laddr_valid&&d.status==1);cases++;
 for(int managed=0;managed<2;managed++)for(int valid=0;valid<2;valid++){
  c.get_laddr=managed?manager:NULL;c.laddr_ida=valid&&!managed;frees=0;d=(struct slim_device){.ctrl=&c,.is_laddr_valid=valid,.status=1,.laddr=7};
  slim_report_absent(&d);slim_report_absent(&d);assert(!d.is_laddr_valid&&d.status==0&&frees==(valid&&!managed));cases++;}
 for(int round=0;round<20;round++){c.get_laddr=NULL;c.laddr_ida=1;frees=0;d=(struct slim_device){.ctrl=&c,.is_laddr_valid=true,.status=1,.laddr=7};pthread_t t[16];
  for(int i=0;i<16;i++) {assert(!pthread_create(&t[i],NULL,invalidate,NULL));}
  for(int i=0;i<16;i++) {assert(!pthread_join(t[i],NULL));}
  assert(frees==1&&!c.laddr_ida&&!d.is_laddr_valid);cases++;}
 assert(!pthread_mutex_destroy(&c.lock.real));printf("address_cases=%d concurrent_rounds=20 threads=16\n",cases);return 0;}
'''
address_code=prefix+absent+tests
address_result=run('address-invalidation',address_code)
run('negative-duplicate-ida-free',address_code.replace('if (was_valid && !ctrl->get_laddr)','if (!ctrl->get_laddr)').replace('\tbool was_valid;','').replace('\twas_valid = sbdev->is_laddr_valid;',''),False)

names=['wcd934x_get_private','wcd934x_bring_up','wcd934x_slim_status_up','wcd934x_slim_status_down','wcd934x_slim_status',
       'wcd934x_finish_probe','wcd934x_reset_addresses','wcd934x_stop_action','wcd934x_disable_supplies','wcd934x_slim_probe','wcd934x_slim_remove']
actual=''.join(function(mfd,n) for n in names)
private=mfd[mfd.index('struct wcd934x_priv {'):mfd.index('static struct wcd934x_priv *wcd934x_get_private(')]
defines=''.join('#define '+word+' '+str(i+1)+'\n' for i,word in enumerate(sorted(set(re.findall(r'\bWCD934X_[A-Z0-9_]+\b',actual)) - {'WCD934X_MAX_SUPPLY'})))
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
typedef uint16_t u16;typedef uint8_t u8;
#define WCD934X_MAX_SUPPLY 5
#define EPROBE_DEFER 517
#define GFP_KERNEL 0
#define GPIOD_OUT_LOW 0
#define IRQF_TRIGGER_HIGH 4
#define PLATFORM_DEVID_AUTO (-1)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define IS_ERR(p) ((uintptr_t)(p)>(uintptr_t)-4096)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define dev_err(...) ((void)0)
#define dev_info(...) ((void)0)
enum slim_device_status{SLIM_DEVICE_STATUS_DOWN=0,SLIM_DEVICE_STATUS_UP=1};
struct action{void (*fn)(void *);void *data;};struct device_node{int x;};struct device_driver{int x;};
struct device{void *data;struct device_driver *driver;struct device_node *of_node;struct action actions[16];int n,refs;};
struct mutex{pthread_mutex_t real;int held;};struct slim_controller{struct mutex lock;int (*get_laddr)(void);int laddr_ida;};
struct slim_device{struct device dev;struct slim_controller *ctrl;bool is_laddr_valid;int laddr,hardware_laddr;enum slim_device_status status;};
struct slim_driver{struct device_driver driver;int (*probe)(struct slim_device *);int (*device_status)(struct slim_device *,enum slim_device_status);};
struct clk{int x;};struct gpio_desc{int x;};struct regulator_bulk_data{const char *supply;};
struct regmap{struct slim_device *sdev;};struct regmap_irq_chip_data{struct regmap *map;};
struct wcd934x_ddata{struct regulator_bulk_data supplies[5];struct regmap_irq_chip_data *irq_data;struct regmap *regmap;struct clk *extclk;struct device *dev;int irq;};
#define to_slim_device(p) container_of(p,struct slim_device,dev)
#define to_slim_driver(p) container_of(p,struct slim_driver,driver)
static struct slim_device main_dev,if_dev;static struct slim_controller ctrl;static struct slim_driver drv;static struct device_node node;
static struct clk clk;static struct gpio_desc gpio;
static int mode,power,supply_refs,map_count,irq_count,children,ops,io_fail,action_calls,queries,querying,early_defer,callback_errors,core_queries;
static int wcd934x_regmap_config,wcd934x_regmap_irq_chip,wcd934x_devices[3];
static char release_order[64];static int release_n;
static void mutex_lock(struct mutex *m){assert(!pthread_mutex_lock(&m->real));assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;assert(!pthread_mutex_unlock(&m->real));}
static void mutex_init(struct mutex *m){assert(!pthread_mutex_init(&m->real,NULL));}
static void *dev_get_drvdata(struct device *d){return d->data;}
static void dev_set_drvdata(struct device *d,void *p){d->data=p;}
static int dev_err_probe(struct device *d,int err,const char *s){return err;}
static void free_mem(void *p){struct wcd934x_ddata *d=p;struct mutex *m=(struct mutex *)((char *)d+sizeof(*d));assert(!m->held);assert(!pthread_mutex_destroy(&m->real));main_dev.dev.data=NULL;free(p);}
static void add(struct device *d,void (*f)(void *),void *p){assert(d->n<16);d->actions[d->n++]=(struct action){f,p};}
static void *devm_kzalloc(struct device *d,size_t size,int flags){if(mode==1)return NULL;void *p=calloc(1,size);assert(p);add(d,free_mem,p);return p;}
static int devm_add_action_or_reset(struct device *d,void (*f)(void *),void *p){action_calls++;if((mode==6&&action_calls==1)||(mode==9&&action_calls==2)){f(p);return -ENOMEM;}add(d,f,p);return 0;}
static void release(struct device *d){while(d->n){struct action a=d->actions[--d->n];a.fn(a.data);}assert(!power&&!supply_refs&&!map_count&&!irq_count&&!children);}
static int of_irq_get(struct device_node *np,int n){return mode==2?-EPROBE_DEFER:42;}
static struct clk *devm_clk_get(struct device *d,const char *n){return mode==3?(void *)(intptr_t)-EPROBE_DEFER:&clk;}
static void supplies_put(void *p){assert(!power&&supply_refs==1);supply_refs--;release_order[release_n++]='r';}
static int devm_regulator_bulk_get(struct device *d,int n,struct regulator_bulk_data *s){if(mode==4)return -EIO;supply_refs++;add(d,supplies_put,s);return 0;}
static int regulator_bulk_enable(int n,struct regulator_bulk_data *s){if(mode==5)return -EIO;assert(supply_refs==1&&!power);power=1;return 0;}
static void regulator_bulk_disable(int n,struct regulator_bulk_data *s){assert(power==1&&!map_count&&!irq_count&&!children);power=0;release_order[release_n++]='p';}
static void gpio_put(void *p){assert(!children&&!irq_count&&!map_count);release_order[release_n++]='g';}
static struct gpio_desc *devm_gpiod_get_optional(struct device *d,const char *s,int flags){if(mode==7)return (void *)(intptr_t)-EIO;add(d,gpio_put,&gpio);return &gpio;}
static void usleep_range(int a,int b){}static void msleep(int ms){}
static void gpiod_set_value(struct gpio_desc *g,int value){assert(g==&gpio&&value==1&&power);main_dev.hardware_laddr=0xd0;if_dev.hardware_laddr=0xd1;}
static struct device_node *of_parse_phandle(struct device_node *np,const char *s,int idx){return mode==8?NULL:&node;}
static struct slim_device *of_slim_get_device(struct slim_controller *c,struct device_node *np){if(mode==10)return NULL;if_dev.dev.refs++;return &if_dev;}
static void of_node_put(struct device_node *np){}
static void put_device(struct device *d){assert(d==&if_dev.dev&&d->refs==2);d->refs--;}
static void ida_free(int *p,int id){assert(0);}
static void slim_device_update_status(struct slim_device *d,enum slim_device_status status);
static int slim_device_alloc_laddr(struct slim_device *d,bool report);
static int get_address_stub(void){return 0;}
static int fail_io(void){return ++ops==io_fail;}
static struct regmap *regmap_init_slimbus(struct slim_device *s,void *cfg){assert(power&&s->is_laddr_valid&&!querying);if(fail_io())return (void *)(intptr_t)-EIO;struct regmap *m=malloc(sizeof(*m));assert(m);m->sdev=s;map_count++;return m;}
static int regmap_bulk_read(struct regmap *m,int r,u8 *v,int n){assert(m->sdev->laddr==m->sdev->hardware_laddr&&!querying);if(fail_io())return -EIO;memset(v,1,n);return 0;}
static int regmap_write(struct regmap *m,int r,int v){assert(m->sdev->laddr==m->sdev->hardware_laddr);return fail_io()?-EIO:0;}
static int regmap_add_irq_chip(struct regmap *m,int irq,int flags,int base,void *cfg,struct regmap_irq_chip_data **p){if(fail_io())return -EIO;*p=malloc(sizeof(**p));assert(*p);(*p)->map=m;irq_count++;return 0;}
static int slim_get_logical_addr(struct slim_device *d);
static void mfd_remove_devices(struct device *d){assert(map_count==1&&irq_count==1);children=0;release_order[release_n++]='c';}
static int mfd_add_devices(struct device *d,int id,void *cells,int n,void *mem,int irq,void *domain){assert(!children);assert(slim_get_logical_addr(&if_dev)==0);assert(if_dev.laddr==if_dev.hardware_laddr);children=n;if(fail_io()){mfd_remove_devices(d);return -EIO;}return 0;}
static void regmap_del_irq_chip(int irq,struct regmap_irq_chip_data *p){assert(!children&&irq_count==1);free(p);irq_count--;release_order[release_n++]='q';}
static void regmap_exit(struct regmap *m){assert(!children&&!irq_count&&map_count==1);free(m);map_count--;release_order[release_n++]='m';}
'''
# The core helper calls the actual MFD notification from address assignment.
bridge=r'''
static void slim_device_update_status(struct slim_device *d,enum slim_device_status status){
 if(d->status==status) {return;}
 d->status=status;if(d->dev.driver){struct slim_driver *s=to_slim_driver(d->dev.driver);if(s->device_status){int r=s->device_status(d,status);if(r==-EPROBE_DEFER)early_defer++;else if(r)callback_errors++;}}
}
static int slim_device_alloc_laddr(struct slim_device *d,bool report){
 queries++;if(d==&main_dev){struct wcd934x_priv *p=wcd934x_get_private(d);assert(!p||!p->lock.held);if(mode==11)return -ENXIO;if(mode==12&&core_queries)return -ENXIO;}
 querying=1;d->laddr=d->hardware_laddr;d->is_laddr_valid=true;slim_device_update_status(d,SLIM_DEVICE_STATUS_UP);querying=0;return 0;
}
static int registered_probe(struct slim_device *d){int ret=wcd934x_slim_probe(d);if(!ret&&mode==12){d->is_laddr_valid=false;core_queries=1;}return ret;}
'''
core_probe=function(core,'slim_device_probe')
get_addr=function(core,'slim_get_logical_addr')
tests=r'''
static void init(int m,int io){memset(&main_dev,0,sizeof(main_dev));memset(&if_dev,0,sizeof(if_dev));memset(&ctrl,0,sizeof(ctrl));memset(&drv,0,sizeof(drv));mode=m;io_fail=io;ops=action_calls=queries=querying=early_defer=callback_errors=core_queries=release_n=0;memset(release_order,0,sizeof(release_order));
 mutex_init(&ctrl.lock);ctrl.get_laddr=get_address_stub;main_dev.ctrl=if_dev.ctrl=&ctrl;main_dev.dev.driver=&drv.driver;main_dev.dev.of_node=if_dev.dev.of_node=&node;if_dev.dev.refs=1;
 main_dev.status=if_dev.status=SLIM_DEVICE_STATUS_UP;main_dev.is_laddr_valid=if_dev.is_laddr_valid=true;main_dev.laddr=main_dev.hardware_laddr=0xcf;if_dev.laddr=if_dev.hardware_laddr=0xce;
 drv.probe=registered_probe;drv.device_status=wcd934x_slim_status;
}
static void done(void){release(&main_dev.dev);assert(if_dev.dev.refs==1&&!ctrl.lock.held);assert(!pthread_mutex_destroy(&ctrl.lock.real));}
int main(void){int cases=0,total;
 init(0,0);assert(slim_device_probe(&main_dev.dev)==0);assert(power&&map_count==1&&irq_count==1&&children==3&&queries==2&&early_defer>=2&&!callback_errors);
 struct wcd934x_priv *p=wcd934x_get_private(&main_dev);assert(p->ready&&p->up);total=ops;wcd934x_slim_remove(&main_dev);assert(!p->ready&&!p->up&&power==1);done();assert(strcmp(release_order,"cqm gpr")==0||strcmp(release_order,"cqmgpr")==0);cases++;
 for(int m=1;m<=12;m++){init(m,0);int ret=slim_device_probe(&main_dev.dev);assert(ret<0);done();cases++;}
 for(int fail=1;fail<=total;fail++){init(0,fail);assert(slim_device_probe(&main_dev.dev)==-EIO);done();assert(!callback_errors);cases++;}
 for(int cycle=0;cycle<20;cycle++){init(0,0);assert(slim_device_probe(&main_dev.dev)==0);done();cases++;}
 printf("probe_cases=%d io_failure_points=%d wrapper_failure_managed_cleanup=1\n",cases,total);return 0;}
'''
code=prefix+defines+private+absent+get_addr+actual+bridge+core_probe+tests
probe_result=run('reset-probe',code)
run('negative-stale-main-address',code.replace('\tslim_report_absent(sdev);',''),False)
run('negative-stale-interface-address',code.replace('\tslim_report_absent(sidev);',''),False)
run('negative-no-ready-gate',code.replace('\tif (!priv->ready) {\n\t\tret = -EPROBE_DEFER;\n\t\tgoto unlock;\n\t}','\tif (false)\n\t\tgoto unlock;'),False)
run('negative-power-cleanup-disabled',code.replace('\tregulator_bulk_disable(WCD934X_MAX_SUPPLY, ddata->supplies);','\t(void)ddata;'),False)
run('negative-stop-cleanup-disabled',code.replace('\twcd934x_slim_status_down(sdev);','\t(void)sdev;'),False)
report=dict(stage=176,actual_core_absent_get_address_and_bus_probe_executed=True,actual_mfd_probe_and_cleanup_executed=True,
 address_result=address_result,probe_result=probe_result,sanitizers=['address','undefined'],concurrent_absent_rounds=20,threads_per_round=16,
 hardware_reset_changes_logical_addresses_in_fixture=True,main_and_interface_query_before_io_verified=True,
 address_assignment_notification_outside_wcd_lock_verified=True,early_notification_deferred=True,
 failures_after_client_probe_managed_cleanup_verified=True,negative_controls_rejected=['duplicate-ida-free','stale-main-address','stale-interface-address','missing-ready-gate','disabled-power-cleanup','disabled-stop-cleanup'],all_passed=True)
check=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'reset-address-and-probe-cleanup.patch')],cwd=k,capture_output=True)
(out/'checkpatch-private.log').write_bytes(check.stdout+check.stderr);assert check.returncode==0
subprocess.run(['git','diff','--check'],cwd=k,check=True);manifest['checkpatch_pass']=True
for folder in [ref,out]:
    (folder/'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (folder/'source-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(report),flush=True)
