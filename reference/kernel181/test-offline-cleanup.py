from pathlib import Path
import hashlib, json, os, re, subprocess

os.umask(0o077)
ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel181');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
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
regcore=(k/'drivers/base/regmap/regmap.c').read_text();regcache=(k/'drivers/base/regmap/regcache.c').read_text()
actual_cache=function(regcache,'regcache_cache_only')
actual_write=function(regcore,'_regmap_write')
actual_read=function(regcore,'_regmap_read')
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
struct regmap{
 struct slim_device *sdev;bool cache_only,cache_bypass,defer_caching,cache_dirty,locked,cache_valid;
 int cache_type;unsigned cached_reg,cached_value;void *lock_arg;
 void (*lock)(void *);void (*unlock)(void *);
 int (*reg_write)(void *,unsigned,unsigned);int (*reg_read)(void *,unsigned,unsigned *);
};
#define REGCACHE_NONE 0
#define REGCACHE_MAPLE 1
#define WARN_ON(c) assert(!(c))
#define trace_regmap_cache_only(...) ((void)0)
#define trace_regmap_reg_write(...) ((void)0)
#define trace_regmap_reg_read(...) ((void)0)
static unsigned live_writes,offline_attempts,software_writes;
static void map_lock(void *p){struct regmap *m=p;assert(!m->locked);m->locked=true;}
static void map_unlock(void *p){struct regmap *m=p;assert(m->locked);m->locked=false;}
static void *_regmap_map_get_context(struct regmap *m){return m;}
static bool regmap_writeable(struct regmap *m,unsigned r){return r<=0xffff;}
static bool regmap_readable(struct regmap *m,unsigned r){return r<=0xffff;}
static bool regmap_should_log(struct regmap *m){return false;}
static int regcache_write(struct regmap *m,unsigned r,unsigned v){assert(m->locked);software_writes++;if(r!=0xfffe){m->cache_valid=true;m->cached_reg=r;m->cached_value=v;}return 0;}
static int regcache_read(struct regmap *m,unsigned r,unsigned *v){assert(m->locked);if(m->cache_valid&&m->cached_reg==r&&r!=0xfffe){*v=m->cached_value;return 0;}return -ENOENT;}
static int _regmap_write(struct regmap *,unsigned,unsigned);
static int _regmap_read(struct regmap *,unsigned,unsigned *);
void regcache_cache_only(struct regmap *,bool);
struct regmap_irq_chip_data{struct regmap *map;};
struct wcd934x_ddata{struct regulator_bulk_data supplies[5];struct regmap_irq_chip_data *irq_data;struct regmap *regmap;struct clk *extclk;struct device *dev;int irq;};
#define to_slim_device(p) container_of(p,struct slim_device,dev)
#define to_slim_driver(p) container_of(p,struct slim_driver,driver)
static struct slim_device main_dev,if_dev;static struct slim_controller ctrl;static struct slim_driver drv;static struct device_node node;
static struct clk clk;static struct gpio_desc gpio;
static int mode,power,supply_refs,map_count,irq_count,children,ops,io_fail,action_calls,queries,querying,early_defer,callback_errors,core_queries;
static int wcd934x_regmap_config,wcd934x_regmap_irq_chip,wcd934x_devices[3];
static char release_order[64];static int release_n;static bool irq_enabled,irq_inflight;
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
static struct regmap *regmap_init_slimbus(struct slim_device *s,void *cfg){assert(power&&s->is_laddr_valid&&!querying);if(fail_io())return (void *)(intptr_t)-EIO;struct regmap *m=calloc(1,sizeof(*m));assert(m);m->sdev=s;m->cache_type=REGCACHE_MAPLE;m->lock=map_lock;m->unlock=map_unlock;m->lock_arg=m;map_count++;return m;}
static int regmap_bulk_read(struct regmap *m,int r,u8 *v,int n){assert(m->sdev->laddr==m->sdev->hardware_laddr&&!querying);if(fail_io())return -EIO;memset(v,1,n);return 0;}
static int hardware_write(void *p,unsigned r,unsigned v){struct regmap *m=p;assert(m->locked);if(m->sdev->status==SLIM_DEVICE_STATUS_DOWN){offline_attempts++;return -ENOTCONN;}assert(m->sdev->laddr==m->sdev->hardware_laddr);live_writes++;return fail_io()?-EIO:0;}
static int hardware_read(void *p,unsigned r,unsigned *v){struct regmap *m=p;assert(m->locked);if(m->sdev->status==SLIM_DEVICE_STATUS_DOWN){offline_attempts++;return -ENOTCONN;}*v=0;return 0;}
static int regmap_write(struct regmap *m,int r,int v){m->reg_write=hardware_write;m->reg_read=hardware_read;m->lock(m->lock_arg);int ret=_regmap_write(m,r,v);m->unlock(m->lock_arg);return ret;}

static int regmap_add_irq_chip(struct regmap *m,int irq,int flags,int base,void *cfg,struct regmap_irq_chip_data **p){if(fail_io())return -EIO;*p=malloc(sizeof(**p));assert(*p);(*p)->map=m;irq_count++;irq_enabled=irq_inflight=true;return 0;}
static int slim_get_logical_addr(struct slim_device *d);
static void disable_irq(int irq){assert(irq==42&&irq_count==1&&irq_enabled);irq_enabled=irq_inflight=false;release_order[release_n++]='d';}
static void disable_irq_nosync(int irq){assert(irq==42&&irq_count==1&&irq_enabled);irq_enabled=false;}
static void mfd_remove_devices(struct device *d){assert(map_count==1&&irq_count==1);if(!io_fail)assert(!irq_enabled&&!irq_inflight);struct regmap *m=((struct wcd934x_ddata *)main_dev.dev.data)->regmap;assert(m->cache_only==(main_dev.status==SLIM_DEVICE_STATUS_DOWN));unsigned writes=live_writes,bad=offline_attempts;for(int irq=0;irq<6;irq++)for(int reg=0;reg<13;reg++)assert(regmap_write(m,0x220+reg,1)==0);if(main_dev.status==SLIM_DEVICE_STATUS_DOWN){assert(live_writes==writes&&offline_attempts==bad&&m->cache_dirty);unsigned value=99;m->lock(m->lock_arg);assert(_regmap_read(m,0xfffe,&value)==-EBUSY&&value==99);assert(_regmap_read(m,0x22c,&value)==0&&value==1);assert(_regmap_write(m,0x10000,1)==-EIO);m->unlock(m->lock_arg);assert(offline_attempts==bad);}else assert(live_writes==writes+78);children=0;release_order[release_n++]='c';}
static int mfd_add_devices(struct device *d,int id,void *cells,int n,void *mem,int irq,void *domain){assert(!children);assert(slim_get_logical_addr(&if_dev)==0);assert(if_dev.laddr==if_dev.hardware_laddr);children=n;if(fail_io()){mfd_remove_devices(d);return -EIO;}return 0;}
static void regmap_del_irq_chip(int irq,struct regmap_irq_chip_data *p){assert(!children&&irq_count==1);free(p);irq_count--;irq_enabled=irq_inflight=false;release_order[release_n++]='q';}
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
static void init(int m,int io){memset(&main_dev,0,sizeof(main_dev));memset(&if_dev,0,sizeof(if_dev));memset(&ctrl,0,sizeof(ctrl));memset(&drv,0,sizeof(drv));mode=m;io_fail=io;irq_enabled=irq_inflight=false;live_writes=offline_attempts=software_writes=0;ops=action_calls=queries=querying=early_defer=callback_errors=core_queries=release_n=0;memset(release_order,0,sizeof(release_order));
 mutex_init(&ctrl.lock);ctrl.get_laddr=get_address_stub;main_dev.ctrl=if_dev.ctrl=&ctrl;main_dev.dev.driver=&drv.driver;main_dev.dev.of_node=if_dev.dev.of_node=&node;if_dev.dev.refs=1;
 main_dev.status=if_dev.status=SLIM_DEVICE_STATUS_UP;main_dev.is_laddr_valid=if_dev.is_laddr_valid=true;main_dev.laddr=main_dev.hardware_laddr=0xcf;if_dev.laddr=if_dev.hardware_laddr=0xce;
 drv.probe=registered_probe;drv.device_status=wcd934x_slim_status;
}
static void done(void){release(&main_dev.dev);assert(if_dev.dev.refs==1&&!ctrl.lock.held);assert(!pthread_mutex_destroy(&ctrl.lock.real));}
int main(void){int cases=0,total;
 init(0,0);assert(slim_device_probe(&main_dev.dev)==0);assert(power&&map_count==1&&irq_count==1&&children==3&&queries==2&&early_defer>=2&&!callback_errors);
 struct wcd934x_priv *p=wcd934x_get_private(&main_dev);assert(p->ready&&p->up);total=ops;wcd934x_slim_remove(&main_dev);assert(!p->ready&&!p->up&&power==1);done();assert(strcmp(release_order,"dcqmgpr")==0);cases++;
 for(int m=1;m<=12;m++){init(m,0);int ret=slim_device_probe(&main_dev.dev);assert(ret<0);done();cases++;}
 for(int fail=1;fail<=total;fail++){init(0,fail);assert(slim_device_probe(&main_dev.dev)==-EIO);done();assert(!callback_errors);cases++;}
 for(int cycle=0;cycle<20;cycle++){init(0,0);assert(slim_device_probe(&main_dev.dev)==0);done();cases++;}
 for(int cycle=0;cycle<20;cycle++){init(0,0);assert(slim_device_probe(&main_dev.dev)==0);assert(irq_enabled);main_dev.status=SLIM_DEVICE_STATUS_DOWN;assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_DOWN)==0);assert(!children&&!irq_count&&!map_count&&!irq_enabled&&!irq_inflight);int stopped=release_n;assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_DOWN)==0&&release_n==stopped);main_dev.status=SLIM_DEVICE_STATUS_UP;assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_UP)==0&&irq_enabled&&irq_count==1);assert(!wcd934x_get_private(&main_dev)->ddata.regmap->cache_only);done();cases++;}
 printf("probe_cases=%d io_failure_points=%d wrapper_failure_managed_cleanup=1\n",cases,total);return 0;}
'''
code=prefix+defines+private+actual_cache+actual_write+actual_read+absent+get_addr+actual+bridge+core_probe+tests
probe_result=run('reset-probe',code)
run('negative-offline-cache-disabled',code.replace('\t\tregcache_cache_only(ddata->regmap, true);','\t\t(void)ddata;'),False)
run('negative-cache-on-live-removal',code.replace('\tif (sdev->status == SLIM_DEVICE_STATUS_DOWN)','\tif (true)'),False)
run('negative-no-parent-disable',code.replace('\tdisable_irq(ddata->irq);',''),False)
run('negative-parent-disable-too-late',code.replace('\tdisable_irq(ddata->irq);','').replace('\tmfd_remove_devices(&sdev->dev);','\tmfd_remove_devices(&sdev->dev);\n\tdisable_irq(ddata->irq);'),False)
run('negative-parent-nosync',code.replace('\tdisable_irq(ddata->irq);','\tdisable_irq_nosync(ddata->irq);'),False)
run('negative-stale-main-address',code.replace('\tslim_report_absent(sdev);',''),False)
run('negative-stale-interface-address',code.replace('\tslim_report_absent(sidev);',''),False)
run('negative-no-ready-gate',code.replace('\tif (!priv->ready) {\n\t\tret = -EPROBE_DEFER;\n\t\tgoto unlock;\n\t}','\tif (false)\n\t\tgoto unlock;'),False)
run('negative-power-cleanup-disabled',code.replace('\tregulator_bulk_disable(WCD934X_MAX_SUPPLY, ddata->supplies);','\t(void)ddata;'),False)
run('negative-stop-cleanup-disabled',code.replace('\twcd934x_slim_status_down(sdev);','\t(void)sdev;'),False)
report=dict(stage=181,actual_core_absent_get_address_and_bus_probe_executed=True,actual_mfd_probe_and_cleanup_executed=True,
 address_result=address_result,probe_result=probe_result,sanitizers=['address','undefined'],concurrent_absent_rounds=20,threads_per_round=16,
 hardware_reset_changes_logical_addresses_in_fixture=True,main_and_interface_query_before_io_verified=True,
 address_assignment_notification_outside_wcd_lock_verified=True,early_notification_deferred=True,
 failures_after_client_probe_managed_cleanup_verified=True,negative_controls_rejected=['duplicate-ida-free','stale-main-address','stale-interface-address','missing-ready-gate','disabled-power-cleanup','disabled-stop-cleanup','missing-parent-disable','parent-disable-too-late','parent-nosync','offline-cache-disabled','cache-on-live-removal'],actual_regcache_mode_and_internal_read_write_executed=True,uncached_offline_read_returns_EBUSY_without_fake_value=True,invalid_offline_write_error_preserved=True,offline_hardware_access_rejected=True,live_cleanup_hardware_io_preserved=True,old_cache_destroyed_and_fresh_map_active=True,parent_irq_quiesce_before_children_verified=True,parent_irq_recreated_enabled_20_cycles=True,all_passed=True)
check=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'offline-irq-cleanup.patch')],cwd=k,capture_output=True)
(out/'checkpatch-private.log').write_bytes(check.stdout+check.stderr);assert check.returncode==0
subprocess.run(['git','diff','--check'],cwd=k,check=True);manifest['checkpatch_pass']=True
for folder in [ref,out]:
    (folder/'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (folder/'source-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(report),flush=True)
