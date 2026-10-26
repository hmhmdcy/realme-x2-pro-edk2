"""Reproduce the parent failures and test actual IRQ/stop functions with real locks."""
from pathlib import Path
import hashlib
import json
import subprocess
import host

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
PREFIX = 'drivers/media/platform/qcom/camss/'
BASE = '21facb9a7941ecd0a624a9e4fccd9ae544dde7b5'


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}\n', start) + 3]


prefix = r'''
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;typedef uint32_t u32;typedef int irqreturn_t;
#define BIT(n) (1u<<(n))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define IRQ_HANDLED 1
#define MSM_VFE_COMPOSITE_IRQ_NUM 4
#define MSM_VFE_IMAGE_MASTERS_NUM 7
enum vfe_line_id {VFE_LINE_RDI0=0};
enum vfe_output_state {VFE_OUTPUT_OFF=0,VFE_OUTPUT_ON=6};
struct vfe_device;
struct vfe_wm {u8 bus_client;};
struct vfe_output {unsigned int wm_num;struct vfe_wm wm[3];enum vfe_output_state state;struct {int active_num;}gen2;};
struct vfe_line {bool is_pix;unsigned int id,num_outputs;struct vfe_output output[5];struct vfe_device *vfe;};
#define to_vfe(line) ((line)->vfe)
struct vfe_hw_ops {void (*vfe_output_stop)(struct vfe_device*,struct vfe_output*);void (*vfe_wm_stop)(struct vfe_device*,u8,struct vfe_line*);};
struct resources {unsigned int line_num;const struct vfe_hw_ops *hw_ops;};
struct isr_ops {void (*reset_ack)(struct vfe_device*);void (*reg_update)(struct vfe_device*,int);void (*sof)(struct vfe_device*,int);void (*comp_done)(struct vfe_device*,int);void (*wm_done)(struct vfe_device*,int);};
struct vfe_device {unsigned char *base;struct resources *res;struct vfe_line line[4];struct isr_ops isr_ops;pthread_mutex_t output_lock,stream_lock;int stream_count;};
static unsigned char mmio[0x4000];
static unsigned int wm_done[24],reg_ack[4],sof_ack[4],wm_stop_count[24],output_stop_count;
static unsigned int resets;static bool live_wm[24];static int reset_result;
static atomic_bool concurrent_stop,hold_reset,reset_entered,release_reset,enable_attempted,enable_acquired;
static pthread_barrier_t stops_at_put;
static void reg_cb(struct vfe_device*v,int id){(void)v;assert(id>=0&&id<4);reg_ack[id]++;}
static void sof_cb(struct vfe_device*v,int id){(void)v;assert(id>=0&&id<4);sof_ack[id]++;}
static void comp_cb(struct vfe_device*v,int id){(void)v;assert(id>=0&&id<6);}
static void done_cb(struct vfe_device*v,int id){(void)v;assert(id>=0&&id<24);wm_done[id]++;}
static void reset_cb(struct vfe_device*v){(void)v;}
static u32 rd(void *address){size_t n=(unsigned char*)address-mmio;assert(n<sizeof(mmio)&&!(n&3));return *(u32*)(mmio+n);}
static void wr(u32 value,void *address){size_t n=(unsigned char*)address-mmio;assert(n<sizeof(mmio)&&!(n&3));*(u32*)(mmio+n)=value;}
#define readl_relaxed rd
#define writel_relaxed wr
#define wmb() do{}while(0)
#define mutex_lock(m) do{assert(!pthread_mutex_lock(m));}while(0)
#define mutex_unlock(m) do{assert(!pthread_mutex_unlock(m));}while(0)
#define spin_lock_irqsave(m,flags) do{(flags)=0;mutex_lock(m);}while(0)
#define spin_unlock_irqrestore(m,flags) do{(void)(flags);mutex_unlock(m);}while(0)
static void wm_stop(struct vfe_device*v,u8 wm,struct vfe_line*line){(void)v;(void)line;assert(wm<24);wm_stop_count[wm]++;live_wm[wm]=false;}
#ifndef BASELINE
static void output_stop(struct vfe_device*v,struct vfe_output*o){output_stop_count++;for(unsigned int i=0;i<o->wm_num;i++)wm_stop(v,o->wm[i].bus_client,NULL);}
#endif
static int vfe_put_output(struct vfe_line*line){
 mutex_lock(&line->vfe->output_lock);
 for(unsigned int i=0;i<line->num_outputs;i++)line->output[i].state=VFE_OUTPUT_OFF;
 mutex_unlock(&line->vfe->output_lock);
 if(atomic_load(&concurrent_stop)){int n=pthread_barrier_wait(&stops_at_put);assert(n==0||n==PTHREAD_BARRIER_SERIAL_THREAD);}
 return 0;
}
static int vfe_reset(struct vfe_device*v){
#ifndef BASELINE
 assert(pthread_mutex_trylock(&v->stream_lock)==EBUSY);
#else
 (void)v;
#endif
 resets++;memset(live_wm,0,sizeof(live_wm));
 atomic_store(&reset_entered,true);
 if(atomic_load(&hold_reset))while(!atomic_load(&release_reset))sched_yield();
 return reset_result;
}
'''
tests = r'''
static struct vfe_hw_ops ops={.vfe_wm_stop=wm_stop};
static struct resources res={.line_num=3,.hw_ops=&ops};
static struct vfe_device vfe;
static void initialize(unsigned int count){
 memset(&vfe,0,sizeof(vfe));memset(mmio,0,sizeof(mmio));memset(wm_done,0,sizeof(wm_done));
 memset(reg_ack,0,sizeof(reg_ack));memset(sof_ack,0,sizeof(sof_ack));memset(wm_stop_count,0,sizeof(wm_stop_count));
 memset(live_wm,0,sizeof(live_wm));resets=output_stop_count=0;reset_result=0;
 atomic_store(&concurrent_stop,false);atomic_store(&hold_reset,false);atomic_store(&reset_entered,false);
 atomic_store(&release_reset,false);atomic_store(&enable_attempted,false);atomic_store(&enable_acquired,false);
 assert(!pthread_mutex_init(&vfe.stream_lock,NULL));assert(!pthread_mutex_init(&vfe.output_lock,NULL));
 vfe.base=mmio;vfe.res=&res;vfe.stream_count=count;
 vfe.isr_ops=(struct isr_ops){reset_cb,reg_cb,sof_cb,comp_cb,done_cb};
 ops.vfe_output_stop=NULL;
 for(unsigned int i=0;i<4;i++){
  vfe.line[i].vfe=&vfe;vfe.line[i].id=i;vfe.line[i].num_outputs=1;
  vfe.line[i].output[0].wm_num=1;vfe.line[i].output[0].wm[0].bus_client=i;
  vfe.line[i].output[0].state=VFE_OUTPUT_ON;vfe.line[i].output[0].gen2.active_num=2;live_wm[i]=true;
 }
}
static void destroy(void){assert(!pthread_mutex_destroy(&vfe.stream_lock));assert(!pthread_mutex_destroy(&vfe.output_lock));}
#ifndef BASELINE
static void *stop_worker(void *arg){struct vfe_line*line=arg;assert(vfe_disable(line)==0);return NULL;}
static void *enable_worker(void *arg){struct vfe_device*v=arg;atomic_store(&enable_attempted,true);mutex_lock(&v->stream_lock);atomic_store(&enable_acquired,true);v->stream_count++;mutex_unlock(&v->stream_lock);return NULL;}
#endif
int main(void){
 initialize(2);*(u32*)(mmio+0x2060)=BIT(0)|BIT(1);
 assert(vfe_isr(0,&vfe)==IRQ_HANDLED);
#ifdef BASELINE
 assert(!wm_done[0]&&!wm_done[1]);
 assert(vfe_disable(&vfe.line[0])==0);
 assert(resets==1 && vfe.stream_count==1 && !live_wm[1]);
 puts("NEGATIVE CONTROL: parent drops bus-only DONE and resets peer line on first stop");
 destroy();return 0;
#else
 assert(wm_done[0]==1&&wm_done[1]==1);
 assert(*(u32*)(mmio+0x2054)==(BIT(0)|BIT(1)));
 /* Top IRQ bit9 alone must never manufacture a completed frame. */
 *(u32*)(mmio+0x6c)=BIT(9);*(u32*)(mmio+0x2060)=0;vfe_isr(0,&vfe);
 assert(wm_done[0]==1&&wm_done[1]==1);
 assert(vfe_disable(&vfe.line[0])==0);
 assert(!resets&&vfe.stream_count==1&&!live_wm[0]&&live_wm[1]);
 assert(wm_stop_count[0]==1&&!wm_stop_count[1]);
 assert(vfe_disable(&vfe.line[1])==0);
 assert(resets==1&&!vfe.stream_count&&wm_stop_count[1]==1);destroy();
 initialize(1);reset_result=-EIO;
 assert(vfe_disable(&vfe.line[0])==-EIO&&resets==1&&!vfe.stream_count);
 assert(vfe.line[0].output[0].state==VFE_OUTPUT_OFF);destroy();
 /* An output callback owns both NV12 WMs; inactive auxiliary outputs are skipped. */
 initialize(2);ops.vfe_output_stop=output_stop;
 struct vfe_line*pix=&vfe.line[0];pix->num_outputs=3;pix->output[0].wm_num=2;
 pix->output[0].wm[0].bus_client=3;pix->output[0].wm[1].bus_client=4;
 pix->output[1].state=VFE_OUTPUT_OFF;pix->output[1].wm_num=1;pix->output[1].wm[0].bus_client=13;
 pix->output[2].state=VFE_OUTPUT_ON;pix->output[2].wm_num=1;pix->output[2].wm[0].bus_client=14;
 assert(vfe_disable(pix)==0&&output_stop_count==2&&wm_stop_count[3]==1&&wm_stop_count[4]==1&&wm_stop_count[14]==1);
 assert(!wm_stop_count[13]&&!resets&&live_wm[1]);destroy();
 /* Both callers reach the decrement together: exactly one performs the last reset. */
 initialize(2);atomic_store(&concurrent_stop,true);assert(!pthread_barrier_init(&stops_at_put,NULL,2));
 pthread_t a,b;assert(!pthread_create(&a,NULL,stop_worker,&vfe.line[0]));assert(!pthread_create(&b,NULL,stop_worker,&vfe.line[1]));
 assert(!pthread_join(a,NULL));assert(!pthread_join(b,NULL));
 assert(resets==1&&!vfe.stream_count&&wm_stop_count[0]==1&&wm_stop_count[1]==1);
 assert(!pthread_barrier_destroy(&stops_at_put));destroy();
 /* The last reset holds stream_lock until completion, excluding a new enable. */
 initialize(1);atomic_store(&hold_reset,true);assert(!pthread_create(&a,NULL,stop_worker,&vfe.line[0]));
 while(!atomic_load(&reset_entered))sched_yield();
 assert(!pthread_create(&b,NULL,enable_worker,&vfe));while(!atomic_load(&enable_attempted))sched_yield();
 assert(!atomic_load(&enable_acquired));atomic_store(&release_reset,true);
 assert(!pthread_join(a,NULL));assert(!pthread_join(b,NULL));assert(resets==1&&vfe.stream_count==1&&atomic_load(&enable_acquired));destroy();
 puts("PASS: actual ISR bus-only DONE; peer preservation; final reset; failure propagation; paired WM stop; simultaneous stop/reset-enable locking");
 return 0;
#endif
}
'''
records = []
for name, baseline in [('parent-negative', True), ('fixed', False)]:
    source17 = subprocess.check_output(['git','-C',str(TREE),'show',BASE+':'+PREFIX+'camss-vfe-17x.c'],text=True) if baseline else (TREE/PREFIX/'camss-vfe-17x.c').read_text()
    source = subprocess.check_output(['git','-C',str(TREE),'show',BASE+':'+PREFIX+'camss-vfe.c'],text=True) if baseline else (TREE/PREFIX/'camss-vfe.c').read_text()
    definitions = source17[source17.index('#define VFE_GLOBAL_RESET_CMD'):source17.index('static inline void vfe_reg_set')]
    functions = definitions + function(source17,'static irqreturn_t vfe_isr(')
    functions += function(source, 'static int vfe_disable_output(' if baseline else 'static void vfe_disable_output(')
    functions += function(source,'int vfe_disable(')
    harness = ('#define BASELINE 1\n' if baseline else '') + prefix + functions + tests
    path = host.PRIVATE / (name + '-multistream-private.c')
    binary = path.with_suffix('')
    path.write_text(harness)
    command = ['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
               '-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-pthread',str(path),'-o',str(binary)]
    build = subprocess.run(command,capture_output=True,text=True)
    (host.PRIVATE / (name+'-multistream-build-private.log')).write_text(build.stdout+build.stderr)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)],capture_output=True,text=True,timeout=15)
    row = dict(name=name, baseline_known_failures_observed=baseline, exit=run.returncode,
        stdout=run.stdout,stderr=run.stderr,source_sha256=hashlib.sha256(functions.encode()).hexdigest(),
        harness_sha256=hashlib.sha256(harness.encode()).hexdigest())
    records.append(row)
    (ROOT/'multistream-host-tests-validation.json').write_text(json.dumps(dict(stage=282,tests=records,
        actual_driver_functions=True,real_pthread_locks=True,mock_mmio_only=True,no_hardware_multistream_test=True),indent=2)+'\n')
    assert run.returncode == 0 and not run.stderr, row
print(json.dumps(records,indent=2))
