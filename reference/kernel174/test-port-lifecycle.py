from pathlib import Path
import hashlib, json, os, subprocess

os.umask(0o077)
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel174')
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
source = (k/'sound/soc/codecs/wcd934x.c').read_text()
manifest = json.loads((ref/'source-validation.json').read_text())
assert hashlib.sha256(source.encode()).hexdigest() == manifest['source_sha256']['sound/soc/codecs/wcd934x.c']
functions = source[source.index('static int wcd934x_slim_port_interrupts('):source.index('static int wcd934x_set_channel_map(')]
irq = source[source.index('static irqreturn_t wcd934x_slim_irq_handler('):]
irq = irq[:irq.index('\nstatic ',1)]
prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
typedef int irqreturn_t;
#define IRQ_NONE 0
#define IRQ_HANDLED 1
#define BIT(n) (1UL << (n))
#define WCD934X_SLIM_PGD_PORT_INT_EN0 0x30
#define WCD934X_SLIM_PGD_PORT_INT_TX_EN0 0x32
#define WCD934X_SLIM_PGD_PORT_INT_STATUS_RX_0 0x34
#define WCD934X_SLIM_PGD_PORT_INT_STATUS_TX_1 0x37
#define WCD934X_SLIM_PGD_PORT_INT_CLR_RX_0 0x38
#define WCD934X_SLIM_PGD_PORT_INT_RX_SOURCE0 0x60
#define WCD934X_SLIM_IRQ_OVERFLOW 1
#define WCD934X_SLIM_IRQ_UNDERFLOW 2
#define WCD934X_SLIM_IRQ_PORT_CLOSED 4
#define SNDRV_PCM_TRIGGER_START 1
#define SNDRV_PCM_TRIGGER_RESUME 2
#define SNDRV_PCM_TRIGGER_PAUSE_RELEASE 3
#define SNDRV_PCM_TRIGGER_STOP 0
#define SNDRV_PCM_TRIGGER_SUSPEND 4
#define SNDRV_PCM_TRIGGER_PAUSE_PUSH 5
#define for_each_set_bit(j,p,n) for ((j)=0;(j)<(n);(j)++) if (*(p)&BIT(j))
struct slim_stream_config { unsigned long port_mask; unsigned int ch_count, rate; };
struct slim_stream_runtime { int prepared, active; };
struct wcd_slim_codec_dai_data { struct slim_stream_config sconfig; struct slim_stream_runtime *sruntime; };
struct regmap { unsigned int reg[256]; };
struct wcd934x_codec { struct regmap *if_regmap; void *dev; struct wcd_slim_codec_dai_data dai[2]; };
struct snd_soc_component { struct wcd934x_codec *wcd; };
struct snd_soc_dai { struct snd_soc_component *component; int id; void *dev; };
struct snd_pcm_substream { int unused; };
static int op, fail_op, errors, prepared_assertions;
static char trace[512];
static int hit(char ch) { trace[op++] = ch; return op == fail_op ? -101 : 0; }
static int regmap_read(struct regmap *m,unsigned int r,unsigned int *v)
{ int ret=hit('R'); if(ret) return ret; *v=m->reg[r]; return 0; }
static int regmap_update_bits(struct regmap *m,unsigned int r,unsigned int mask,unsigned int value)
{ int ret=hit(value?'E':'M'); if(ret) return ret; m->reg[r]=(m->reg[r]&~mask)|(value&mask); return 0; }
static int regmap_write(struct regmap *m,unsigned int r,unsigned int v)
{ int ret=hit('C'); if(ret) return ret; if(r>=0x38&&r<=0x3b) {
 m->reg[r-4]&=~v; for(int n=0;n<8;n++) if(v&BIT(n)) m->reg[0x60+(r-0x38)*8+n]=0;
 } else m->reg[r]=v; return 0; }
static struct wcd934x_codec *snd_soc_component_get_drvdata(struct snd_soc_component *c) {return c->wcd;}
static bool of_machine_is_compatible(const char *s) {(void)s;return false;}
#define dev_info(...) do {} while(0)
#define dev_err_ratelimited(...) do {errors++;} while(0)
static struct regmap map;
static int slim_stream_prepare(struct slim_stream_runtime *r,struct slim_stream_config *c)
{ (void)c; prepared_assertions++; assert(!(map.reg[0x30]&1)); assert(!(map.reg[0x32]&BIT(5)));
 int ret=hit('P'); if(!ret)r->prepared=1; return ret; }
static int slim_stream_enable(struct slim_stream_runtime *r)
{ assert(r->prepared); int ret=hit('B'); if(!ret)r->active=1; return ret; }
static int slim_stream_disable(struct slim_stream_runtime *r)
{ int ret=hit('D'); r->active=0; return ret; }
static int slim_stream_unprepare(struct slim_stream_runtime *r)
{ int ret=hit('U'); r->prepared=0; return ret; }
'''
tests = r'''
static struct slim_stream_runtime runtime;
static struct wcd934x_codec wcd;
static struct snd_soc_component component;
static struct snd_soc_dai dai;
static void reset(unsigned long ports) {
 memset(&map,0,sizeof(map)); memset(&runtime,0,sizeof(runtime)); memset(&wcd,0,sizeof(wcd));
 wcd.if_regmap=&map; wcd.dai[0].sconfig.port_mask=ports; wcd.dai[0].sruntime=&runtime;
 component.wcd=&wcd; dai.component=&component; dai.id=0;
 op=0; fail_op=0; errors=0; memset(trace,0,sizeof(trace));
 for(int i=0;i<4;i++)map.reg[0x30+i]=0x10;
}
static void begin_trace(int fail) {op=0;fail_op=fail;memset(trace,0,sizeof(trace));}
int main(void) {
 int cases=0;
 /* Full port-number/bank mapping, with unrelated enabled ports preserved. */
 for(int p=0;p<32;p++) {
  reset(BIT(p)); int bank=p<16?2+p/8:(p-16)/8; unsigned int bit=BIT(p%8);
  assert(wcd934x_slim_port_interrupts(&wcd,&wcd.dai[0],true)==0);
  for(int b=0;b<4;b++)assert(map.reg[0x30+b]==(0x10|(b==bank?bit:0)));
  map.reg[0x34+bank]=0xff; map.reg[0x60+bank*8+p%8]=6;
  assert(wcd934x_slim_port_interrupts(&wcd,&wcd.dai[0],false)==0);
  assert(wcd934x_slim_port_clear(&wcd,&wcd.dai[0])==0);
  assert(map.reg[0x34+bank]==(0xff&~bit)); cases++;
 }
 /* Start/pause/resume/stop order, stale latches and independent opposite DAI. */
 reset(BIT(5)|BIT(16));
 for(int round=0;round<3;round++) {
  map.reg[0x36]|=BIT(5); map.reg[0x75]=6;
  begin_trace(0); int start=round==0?SNDRV_PCM_TRIGGER_START:round==1?SNDRV_PCM_TRIGGER_PAUSE_RELEASE:SNDRV_PCM_TRIGGER_RESUME;
  assert(wcd934x_trigger(NULL,start,&dai)==0); assert(strcmp(trace,"MMCCPBEE")==0);
  assert(runtime.active&&runtime.prepared); assert(map.reg[0x30]==0x11&&map.reg[0x32]==0x30);
  assert(!map.reg[0x36]&&!map.reg[0x75]);
  begin_trace(0); int stop=round==0?SNDRV_PCM_TRIGGER_PAUSE_PUSH:round==1?SNDRV_PCM_TRIGGER_SUSPEND:SNDRV_PCM_TRIGGER_STOP;
  assert(wcd934x_trigger(NULL,stop,&dai)==0); assert(strcmp(trace,"MMDUCC")==0);
  assert(!runtime.active&&!runtime.prepared); assert(map.reg[0x30]==0x10&&map.reg[0x32]==0x10); cases++;
 }
 /* Inject every startup and teardown transport failure: preserve first errno and perform cleanup. */
 for(int fail=1;fail<=8;fail++) {
  reset(BIT(5)|BIT(16)); begin_trace(fail);
  assert(wcd934x_trigger(NULL,SNDRV_PCM_TRIGGER_START,&dai)==-101);
  assert(!runtime.active&&!runtime.prepared); assert(!(map.reg[0x30]&1)&&!(map.reg[0x32]&BIT(5))); cases++;
 }
 for(int fail=1;fail<=6;fail++) {
  reset(BIT(5)|BIT(16)); assert(wcd934x_trigger(NULL,SNDRV_PCM_TRIGGER_START,&dai)==0); begin_trace(fail);
  assert(wcd934x_trigger(NULL,SNDRV_PCM_TRIGGER_STOP,&dai)==-101);
  assert(strcmp(trace,"MMDUCC")==0); assert(!runtime.active&&!runtime.prepared); cases++;
 }
 /* IRQs already latched during stop are acknowledged; active FIFO faults stay visible. */
 for(int masked=0;masked<2;masked++) {
  reset(BIT(5)); map.reg[0x36]=BIT(5); map.reg[0x75]=6;
  if(!masked)map.reg[0x32]|=BIT(5);
  assert(wcd934x_slim_irq_handler(0,&wcd)==IRQ_HANDLED);
  assert(errors==(masked?0:2)); assert(map.reg[0x32]==0x10); assert(!map.reg[0x36]); cases++;
 }
 /* Failed status/source/mask reads cannot use uninitialized values or falsely acknowledge data. */
 for(int fail=1;fail<=6;fail++) {
  reset(BIT(5)); map.reg[0x36]=BIT(5); map.reg[0x75]=6; map.reg[0x32]|=BIT(5); begin_trace(fail);
  assert(wcd934x_slim_irq_handler(0,&wcd)==IRQ_NONE); assert(!errors); assert(map.reg[0x36]==BIT(5)); cases++;
 }
 reset(BIT(5)); assert(wcd934x_trigger(NULL,99,&dai)==-EINVAL); assert(!op); cases++;
 printf("passed=%d\n",cases); return 0;
}
'''
full = prefix+functions+irq+tests
def run(label,text,expect_pass):
    p=out/(label+'-private.c'); p.write_text(text)
    exe=out/(label+'-private')
    built=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Wno-unused-parameter','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(p),'-o',str(exe)],capture_output=True)
    (out/(label+'-compile-private.log')).write_bytes(built.stdout+built.stderr)
    assert built.returncode==0, built.stderr.decode()
    result=subprocess.run([str(exe)],capture_output=True)
    (out/(label+'-run-private.log')).write_bytes(result.stdout+result.stderr)
    assert (result.returncode==0)==expect_pass, (label,result.stderr.decode())
    return result.stdout.decode().strip()
passed=run('port-lifecycle',full,True)
needle='\t\tret = wcd934x_slim_port_interrupts(wcd, dai_data, false);\n\t\tcleanup = slim_stream_disable'
assert full.count(needle)==1
run('negative-no-stop-mask',full.replace(needle,'\t\tret = 0;\n\t\tcleanup = slim_stream_disable'),False)
run('negative-no-irq-mask-filter',full.replace('\t\t\tif (!(int_val & BIT(port_id % 8)))\n\t\t\t\tgoto clear;','\t\t\tif (int_val == 0xffffffff)\n\t\t\t\tgoto clear;'),False)
report=dict(stage=174,actual_c_functions_executed=True,sanitizers='address,undefined',passed=int(passed.split('=')[1]),
            all_32_port_mappings_checked=True,pause_resume_rearms=True,unrelated_port_bits_preserved=True,
            startup_fault_injections=8,stop_fault_injections=6,irq_read_failure_injections=6,
            active_irq_errors_reported=True,masked_pending_irq_acknowledged=True,
            negative_controls_rejected=['no-stop-mask','no-irq-mask-filter'],all_passed=True)
for folder in [ref,out]: (folder/'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
