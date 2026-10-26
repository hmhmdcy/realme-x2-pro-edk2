from pathlib import Path
import ast, hashlib, json, os, re, subprocess

os.umask(0o077)
ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
manifest=json.loads((ref/'source-validation.json').read_text())
for n,h in manifest['source_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==h,n
def function(s,name):
    hit=re.search(r'^(?:static )?[^\n]*\b'+name+r'\([^;]*?\n\{',s,re.M);assert hit,name
    a=s.index('{',hit.start());b=a+1;depth=1
    while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[hit.start():b]+'\n'
def run(label,code,passed=True):
    src=out/(label+'-private.c');src.write_text(code);exe=out/(label+'-private')
    p=subprocess.run(['gcc','-std=gnu11','-g','-O1','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread',str(src),'-o',str(exe)],capture_output=True)
    (out/(label+'-compile-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
    p=subprocess.run([str(exe)],capture_output=True)
    (out/(label+'-run-private.log')).write_bytes(p.stdout+p.stderr)
    assert (p.returncode==0)==passed,(label,p.stdout.decode(),p.stderr.decode())
    if passed:assert not p.stderr,p.stderr.decode()
    return p.stdout.decode().strip()

machine=(k/'sound/soc/qcom/samurai-audio.c').read_text()
tree=ast.parse((ref.parent/'kernel172/test-jack.py').read_text())
prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='machine_prefix' for t in n.targets))
prefix='#include <stdlib.h>\n'+prefix
prefix=prefix.replace('struct snd_soc_card { void *data; void *dev; };','struct snd_soc_card { void *data; void *dev; int probed; int (*probe)(struct snd_soc_card *); int (*remove)(struct snd_soc_card *); };\nstatic int soc_card_ret(struct snd_soc_card *c,int r) {return r;}')
prefix=prefix.replace('struct snd_soc_component { int id; };','struct snd_soc_component { int id, alive; };\nstruct fake_jack { int alive; };\nstatic int stops, errors;\n#define dev_err(...) do {errors++;} while(0)')
a=prefix.index('static int snd_soc_card_jack_new_pins(');b=prefix.index('static int snd_soc_dai_set_channel_map(',a)
prefix=prefix[:a]+r'''
static int snd_soc_card_jack_new_pins(struct snd_soc_card *c,const char *s,int type,struct snd_soc_jack *j,struct snd_soc_jack_pin *p,int n) {
 creates++; if(create_ret)return create_ret; assert(n==5&&type==63); struct fake_jack *f=malloc(sizeof(*f));assert(f);f->alive=1;j->jack=f;return 0;
}
static int snd_jack_set_key(void *j,unsigned int b,unsigned int key) {assert(((struct fake_jack *)j)->alive);key_calls++;return key_calls==key_fail?-ENOMEM:0;}
static int snd_soc_dai_set_sysclk(struct snd_soc_dai *d,int id,int rate,int dir) {assert(d->component->alive);clock_calls++;assert(rate==9600000);return clock_ret;}
static int snd_soc_component_set_jack(struct snd_soc_component *c,struct snd_soc_jack *j,void *data) {
 assert(c->alive); if(j){assert(((struct fake_jack *)j->jack)->alive);binds++;} else stops++;return bind_ret;
}
'''+prefix[b:]
data=machine[machine.index('struct samurai_audio_data {'):machine.index('static int samurai_setup_jack(')]
actual=''.join(function(machine,n) for n in ['samurai_setup_jack','samurai_exit','samurai_card_probe','samurai_card_remove','samurai_init'])
card_core=(k/'sound/soc/soc-card.c').read_text()
actual+=''.join(function(card_core,n) for n in ['snd_soc_card_probe','snd_soc_card_remove'])
tests=r'''
int main(void) {
 struct samurai_audio_data data={0};struct snd_soc_card card={.data=&data,.probe=samurai_card_probe,.remove=samurai_card_remove};
 struct snd_soc_component *comp=malloc(sizeof(*comp));*comp=(struct snd_soc_component){.id=1,.alive=1};
 struct snd_soc_dai dai={.component=comp};struct snd_soc_dai *ds[]={&dai};
 struct snd_soc_dai_link rx={.id=SLIMBUS_0_RX},tx={.id=SLIMBUS_0_TX},other={.id=QUATERNARY_MI2S_RX};
 struct snd_soc_pcm_runtime r={.card=&card,.dai_link=&rx,.codecs=ds,.ncodecs=1};
 int cases=0;
 for(int cycle=0;cycle<25;cycle++) {
  assert(snd_soc_card_probe(&card)==0&&card.probed==1);
  int before=creates,bind_before=binds,stop_before=stops;
  r.dai_link=&rx;assert(samurai_init(&r)==0);assert(creates==before+1&&binds==bind_before+1);
  r.dai_link=&tx;assert(samurai_init(&r)==0);assert(creates==before+1&&binds==bind_before+1);
  r.dai_link=&other;samurai_exit(&r);assert(stops==stop_before);
  r.dai_link=&rx;samurai_exit(&r);assert(stops==stop_before+1&&!data.jack_component);
  r.dai_link=&tx;samurai_exit(&r);assert(stops==stop_before+1);
  /* The core removes components before card remove, then frees the ALSA jack. */
  comp->alive=0;free(comp);assert(snd_soc_card_remove(&card)==0&&!data.jack_created&&!data.jack_component&&!card.probed);
  free(data.jack.jack);comp=malloc(sizeof(*comp));assert(comp);*comp=(struct snd_soc_component){.id=cycle+2,.alive=1};dai.component=comp;cases++;
 }
 /* Failed binding still resets the newly allocated card jack during cleanup. */
 assert(snd_soc_card_probe(&card)==0&&card.probed==1);
 r.dai_link=&rx;bind_ret=-EIO;assert(samurai_init(&r)==-EIO&&!data.jack_component&&data.jack_created);
 samurai_exit(&r);assert(snd_soc_card_remove(&card)==0&&!data.jack_created);free(data.jack.jack);cases++;
 assert(snd_soc_card_probe(&card)==0&&card.probed==1);
 bind_ret=0;assert(samurai_init(&r)==0);bind_ret=-EIO;samurai_exit(&r);assert(!data.jack_component&&errors==1);
 assert(snd_soc_card_remove(&card)==0&&!data.jack_created);free(data.jack.jack);free(comp);cases++;
 assert(maps==52);printf("machine_cases=%d\n",cases);return 0;
}
'''
machine_code=prefix+data+actual+tests
machine_result=run('machine-lifetime',machine_code)
run('negative-machine-no-card-reset',machine_code.replace('\tdata->jack_created = false;','\t/* missing reset */'),False)
run('negative-machine-no-probe-callback',machine_code.replace('.probe=samurai_card_probe','.probe=NULL'),False)

mfd=(k/'drivers/mfd/wcd934x.c').read_text()
actual=''.join(function(mfd,n) for n in ['wcd934x_get_private','wcd934x_bring_up','wcd934x_slim_status_up','wcd934x_slim_status_down','wcd934x_slim_status','wcd934x_finish_probe','wcd934x_slim_remove'])
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
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define IS_ERR(p) ((uintptr_t)(p)>(uintptr_t)-4096)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define IRQF_TRIGGER_HIGH 4
#define PLATFORM_DEVID_AUTO (-1)
#define dev_err(...) ((void)0)
#define dev_info(...) ((void)0)
enum slim_device_status {SLIM_DEVICE_STATUS_UP=1,SLIM_DEVICE_STATUS_DOWN=0};
struct mutex {pthread_mutex_t real;int held;};
struct device {void *data;};struct slim_device {struct device dev;enum slim_device_status status;};
struct regmap {int live;};struct regmap_irq_chip_data {struct regmap *map;};
struct wcd934x_ddata {int supplies[5];struct regmap_irq_chip_data *irq_data;struct regmap *regmap;void *extclk;struct device *dev;int irq;};
static int map_count,irq_count,children,ops,fail_op,allocs,deletes,disabled;
static char release_trace[32];static int release_n;
static int wcd934x_regmap_config,wcd934x_regmap_irq_chip,wcd934x_devices[3];
static void *dev_get_drvdata(struct device *d){return d->data;}
static int dev_err_probe(struct device *d,int ret,const char *s){return ret;}
static void mutex_lock(struct mutex *m){assert(pthread_mutex_lock(&m->real)==0);assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;assert(pthread_mutex_unlock(&m->real)==0);}
static void usleep_range(int a,int b){}
static int fail(void){return ++ops==fail_op;}
static struct regmap *regmap_init_slimbus(struct slim_device *s,void *cfg){if(fail())return (void *)(intptr_t)-EIO;struct regmap *m=malloc(sizeof(*m));assert(m);m->live=1;map_count++;allocs++;return m;}
static int regmap_bulk_read(struct regmap *m,int r,u8 *v,int n){assert(m->live);if(fail())return -EIO;memset(v,1,n);return 0;}
static int regmap_write(struct regmap *m,int r,int v){assert(m->live);return fail()?-EIO:0;}
static int regmap_add_irq_chip(struct regmap *m,int irq,int flags,int base,void *cfg,struct regmap_irq_chip_data **p){assert(m->live);if(fail())return -EIO;*p=malloc(sizeof(**p));assert(*p);(*p)->map=m;irq_count++;return 0;}
static void mfd_remove_devices(struct device *d){assert(map_count==1&&irq_count==1);children=0;release_trace[release_n++]='c';}
static int mfd_add_devices(struct device *d,int id,void *cells,int n,void *mem,int irq,void *domain){assert(!children&&map_count==1&&irq_count==1);children=n;if(fail()){mfd_remove_devices(d);return -EIO;}return 0;}
static void regmap_del_irq_chip(int irq,struct regmap_irq_chip_data *p){assert(!children&&p&&p->map->live&&irq_count==1);free(p);irq_count--;release_trace[release_n++]='q';}
static void regmap_exit(struct regmap *m){assert(m&&m->live&&!children&&!irq_count);m->live=0;free(m);map_count--;deletes++;release_trace[release_n++]='m';}
static void regulator_bulk_disable(int n,int *s){assert(!children&&!irq_count&&!map_count);disabled++;}
'''
tests=r'''
static struct wcd934x_priv priv;static struct slim_device sdev;
static void init(void){memset(&priv,0,sizeof(priv));memset(&sdev,0,sizeof(sdev));sdev.dev.data=&priv.ddata;priv.ddata.dev=&sdev.dev;assert(pthread_mutex_init(&priv.lock.real,NULL)==0);ops=0;fail_op=0;release_n=0;memset(release_trace,0,sizeof(release_trace));}
static void done(void){assert(!priv.up&&!priv.ddata.regmap&&!priv.ddata.irq_data&&!map_count&&!irq_count&&!children);assert(pthread_mutex_destroy(&priv.lock.real)==0);}
static void *up_thread(void *p){assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_UP)==0);return NULL;}
static void *down_thread(void *p){assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_DOWN)==0);return NULL;}
int main(void){int cases=0,total;
 assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_UP)==-EPROBE_DEFER&&ops==0);cases++;
 init();assert(wcd934x_finish_probe(&sdev)==0&&ops==0&&!priv.up);sdev.status=SLIM_DEVICE_STATUS_UP;
 assert(wcd934x_finish_probe(&sdev)==0&&priv.up);int completed=ops;assert(wcd934x_finish_probe(&sdev)==0&&ops==completed);
 assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_DOWN)==0);done();cases++;
 init();assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_UP)==0);total=ops;int before=ops;
 assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_UP)==0&&ops==before);
 assert(wcd934x_slim_status(&sdev,99)==-EINVAL&&ops==before);
 assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_DOWN)==0);assert(strcmp(release_trace,"cqm")==0);
 assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_DOWN)==0);wcd934x_slim_remove(&sdev);assert(disabled==1);done();cases++;
 for(int f=1;f<=total;f++){init();fail_op=f;assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_UP)==-EIO);assert(!priv.up&&!priv.ddata.regmap&&!priv.ddata.irq_data&&!map_count&&!irq_count&&!children);
  assert(ops==f);fail_op=0;assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_UP)==0);assert(wcd934x_slim_status(&sdev,SLIM_DEVICE_STATUS_DOWN)==0);done();cases++;}
 for(int round=0;round<20;round++){init();pthread_t th[16];int a=allocs;
  for(int i=0;i<16;i++)assert(pthread_create(&th[i],NULL,up_thread,NULL)==0);
  for(int i=0;i<16;i++)assert(pthread_join(th[i],NULL)==0);
  assert(allocs==a+1&&map_count==1&&irq_count==1&&children==3);
  for(int i=0;i<16;i++)assert(pthread_create(&th[i],NULL,down_thread,NULL)==0);
  for(int i=0;i<16;i++)assert(pthread_join(th[i],NULL)==0);
  done();cases++;}
 assert(allocs==deletes);printf("mfd_cases=%d fault_points=%d concurrent_rounds=20\n",cases,total);return 0;}
'''
mfd_code=prefix+defines+private+actual+tests
mfd_result=run('mfd-lifetime',mfd_code)
run('negative-mfd-no-regmap-exit',mfd_code.replace('\tregmap_exit(ddata->regmap);','\t/* missing exit */'),False)
run('negative-mfd-no-up-guard',mfd_code.replace('\tif (priv->up)\n\t\treturn 0;',''),False)
run('negative-mfd-no-initial-up',mfd_code.replace('return wcd934x_slim_status(sdev, SLIM_DEVICE_STATUS_UP);','return 0;'),False)

codec=(k/'sound/soc/codecs/wcd934x.c').read_text()
actual=''.join(function(codec,n) for n in ['wcd934x_put_device_action','wcd934x_regmap_exit_action','wcd934x_init_slim_interface'])
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define IS_ERR(p) ((uintptr_t)(p)>(uintptr_t)-4096)
#define PTR_ERR(p) ((int)(intptr_t)(p))
struct action{void (*fn)(void *);void *data;};
struct device {struct action actions[4];int count,refs;};struct device_node{int x;};
struct slim_device{struct device dev;void *ctrl;};struct regmap{struct device *dev;};
struct wcd934x_codec{struct device *dev;struct slim_device *sdev,*sidev;struct regmap *if_regmap;};
static struct device owner;static struct slim_device sidev,sdev;static int mode,maps,action_calls;static char trace[8];static int pos;
static int wcd934x_ifc_regmap_config;
static int dev_err_probe(struct device *d,int err,const char *s){return err;}
static struct slim_device *of_slim_get_device(void *c,struct device_node *np){if(mode==1)return NULL;sidev.dev.refs++;return &sidev;}
static void put_device(struct device *d){assert(d->refs==2);d->refs--;trace[pos++]='p';}
static int devm_add_action_or_reset(struct device *d,void (*f)(void *),void *p){action_calls++;if((mode==2&&action_calls==1)||(mode==5&&action_calls==2)){f(p);return -ENOMEM;}d->actions[d->count++]=(struct action){f,p};return 0;}
static int slim_get_logical_addr(struct slim_device *s){return mode==3?-EIO:0;}
static struct regmap *regmap_init_slimbus(struct slim_device *s,void *cfg){assert(s->dev.refs==2);if(mode==4)return (void *)(intptr_t)-EIO;struct regmap *m=malloc(sizeof(*m));assert(m);m->dev=&s->dev;maps++;return m;}
static void regmap_exit(struct regmap *m){assert(m->dev->refs==2&&maps==1);maps--;free(m);trace[pos++]='m';}
static void release(struct device *d){while(d->count){struct action a=d->actions[--d->count];a.fn(a.data);}}
'''
tests=r'''
int main(void){struct device_node node={0};int cases=0;
 for(mode=0;mode<=5;mode++){memset(&owner,0,sizeof(owner));memset(&sidev,0,sizeof(sidev));sidev.dev.refs=1;maps=0;action_calls=0;pos=0;memset(trace,0,sizeof(trace));
  struct wcd934x_codec w={.dev=&owner,.sdev=&sdev};int ret=wcd934x_init_slim_interface(&w,&node);
  if(mode==0){assert(ret==0&&owner.count==2&&sidev.dev.count==0&&maps==1);}else assert(ret==((mode==2||mode==5)?-ENOMEM:mode==1?-EINVAL:-EIO));
  release(&owner);assert(!maps&&sidev.dev.refs==1&&sidev.dev.count==0);
  if(mode==0||mode==5) {assert(strcmp(trace,"mp")==0);}
  cases++;}
 printf("interface_cases=%d\n",cases);return 0;}
'''
interface_code=prefix+actual+tests
interface_result=run('interface-lifetime',interface_code)
run('negative-interface-wrong-owner',interface_code.replace('devm_add_action_or_reset(dev, wcd934x_regmap_exit_action,','devm_add_action_or_reset(&wcd->sidev->dev, wcd934x_regmap_exit_action,'),False)
report=dict(stage=175,actual_c_functions_executed=True,sanitizers=['address','undefined'],machine_result=machine_result,
 mfd_result=mfd_result,interface_result=interface_result,card_rebind_cycles=25,concurrent_status_rounds=20,status_threads_per_round=16,
 modeled_mfd_core_partial_add_rollback_contract=True,codec_interface_action_ownership_and_release_order_verified=True,
 actual_asoc_card_probe_and_remove_executed=True,
 already_up_probe_and_early_status_callback_verified=True,
 negative_controls_rejected=['missing-card-reset','missing-card-probe-callback','missing-mfd-regmap-exit','duplicate-up-guard','missing-initial-up','wrong-interface-owner'],all_passed=True)
for folder in [ref,out]:(folder/'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
