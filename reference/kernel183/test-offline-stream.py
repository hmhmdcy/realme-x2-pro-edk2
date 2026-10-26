"""Execute actual core/NGD/abort/codec functions with thin host transports."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

os.umask(0o077)
ref = Path(__file__).resolve().parent
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel183')
manifest = json.loads((ref / 'source-validation.json').read_text())
def function(name, signature):
    text = (k / name).read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == manifest['source_sha256'][name]
    start = text.index(signature); opening = text.index('{', start); depth = 1; end = opening + 1
    while depth:
        if text[end] == '{': depth += 1
        if text[end] == '}': depth -= 1
        end += 1
    return text[start:end] + '\n'
online = function('drivers/slimbus/core.c', 'bool slim_device_is_online(')
abort = function('drivers/slimbus/stream.c', 'int slim_stream_abort(')
ngd = function('drivers/slimbus/qcom-ngd-ctrl.c', 'static bool qcom_slim_ngd_is_online(')
disable = function('drivers/slimbus/stream.c', 'int slim_stream_disable(')
unprepare = function('drivers/slimbus/stream.c', 'int slim_stream_unprepare(')
codec = ''.join(function('sound/soc/codecs/wcd934x.c', s) for s in
                ['static int wcd934x_slim_port_interrupts(', 'static int wcd934x_slim_port_clear(',
                 'static int wcd934x_slim_stop(', 'static int wcd934x_trigger('])
prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
#define READ_ONCE(x) (x)
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define SLIM_DEVICE_STATUS_DOWN 0
#define SLIM_DEVICE_STATUS_UP 1
#define QCOM_SLIM_NGD_CTRL_DOWN 0
#define QCOM_SLIM_NGD_CTRL_ASLEEP 1
#define QCOM_SLIM_NGD_CTRL_AWAKE 2
#define SLIM_MSG_MC_BEGIN_RECONFIGURATION 1
#define SLIM_MSG_MC_RECONFIGURE_NOW 2
#define SLIM_LA_MANAGER 255
struct slim_stream_runtime;
struct slim_controller { bool (*is_online)(struct slim_controller *); int (*disable_stream)(struct slim_stream_runtime *); };
struct qcom_slim_ngd_ctrl { struct slim_controller ctrl; int state; bool registered; struct {void *handle;} qmi; };
struct slim_device { struct slim_controller *ctrl; int status; bool is_laddr_valid; };
struct slim_port {int unused;};
struct slim_stream_runtime {struct slim_device *dev; struct slim_port *ports; int num_ports;};
struct slim_msg_txn {int mc;};
#define DEFINE_SLIM_BCAST_TXN(n,mc,rl,la,msg) struct slim_msg_txn n={mc}
static int hw_calls, fail_op, fail_errno, drop_op, freed;
static struct qcom_slim_ngd_ctrl ngdc;
static int io(void) {
 int op=++hw_calls;
 if(op==drop_op) {ngdc.state=QCOM_SLIM_NGD_CTRL_DOWN;ngdc.qmi.handle=NULL;return -ENOTCONN;}
 if(op==fail_op)return fail_errno;
 if(!ngdc.qmi.handle||ngdc.state==QCOM_SLIM_NGD_CTRL_DOWN)return -ENOTCONN;
 return 0;
}
static void kfree(void *p) {if(p)freed++;free(p);}
static int slim_do_transfer(struct slim_controller *c,struct slim_msg_txn *t) {(void)c;(void)t;return io();}
static int slim_deactivate_remove_channel(struct slim_stream_runtime *r,struct slim_port *p) {(void)r;(void)p;return io();}
static int slim_disconnect_port(struct slim_stream_runtime *r,struct slim_port *p) {(void)r;(void)p;return io();}
#define SNDRV_PCM_TRIGGER_STOP 0
#define SNDRV_PCM_TRIGGER_START 1
#define SNDRV_PCM_TRIGGER_RESUME 2
#define SNDRV_PCM_TRIGGER_PAUSE_RELEASE 3
#define SNDRV_PCM_TRIGGER_SUSPEND 4
#define SNDRV_PCM_TRIGGER_PAUSE_PUSH 5
#define WCD934X_SLIM_PGD_PORT_INT_EN0 0x30
#define WCD934X_SLIM_PGD_PORT_INT_CLR_RX_0 0x38
struct slim_stream_config {unsigned long port_mask; unsigned int ch_count,rate;};
struct wcd_slim_codec_dai_data {struct slim_stream_config sconfig;struct slim_stream_runtime *sruntime;};
struct regmap {unsigned int reg[256];};
struct wcd934x_codec {struct regmap *if_regmap;struct slim_device *sdev;struct wcd_slim_codec_dai_data dai[1];};
struct snd_soc_component {struct wcd934x_codec *wcd;};
struct snd_soc_dai {struct snd_soc_component *component;int id;void *dev;};
struct snd_pcm_substream {int unused;};
static struct wcd934x_codec *snd_soc_component_get_drvdata(struct snd_soc_component *c) {return c->wcd;}
static bool of_machine_is_compatible(const char *s) {(void)s;return false;}
#define dev_info(...) do {} while(0)
static int regmap_update_bits(struct regmap *m,unsigned int r,unsigned int mask,unsigned int v) {
 int e=io();if(e)return e;m->reg[r]=(m->reg[r]&~mask)|(v&mask);return 0;
}
static int regmap_write(struct regmap *m,unsigned int r,unsigned int v) {int e=io();if(!e)m->reg[r]=v;return e;}
static int slim_stream_prepare(struct slim_stream_runtime *r,struct slim_stream_config *c) {
 (void)c;int e=io();if(e)return e;r->ports=calloc(2,sizeof(*r->ports));assert(r->ports);r->num_ports=2;return 0;
}
static int slim_stream_enable(struct slim_stream_runtime *r) {(void)r;return io();}
'''
tests = r'''
static struct slim_device dev;
static struct slim_stream_runtime rt;
static struct regmap map;
static struct wcd934x_codec wcd;
static struct snd_soc_component component;
static struct snd_soc_dai dai;
static void reset(bool allocated) {
 if(rt.ports)free(rt.ports);
 memset(&ngdc,0,sizeof(ngdc));memset(&dev,0,sizeof(dev));memset(&rt,0,sizeof(rt));memset(&map,0,sizeof(map));
 ngdc.ctrl.is_online=qcom_slim_ngd_is_online;ngdc.state=QCOM_SLIM_NGD_CTRL_AWAKE;ngdc.registered=true;ngdc.qmi.handle=(void *)1;
 dev.ctrl=&ngdc.ctrl;dev.status=SLIM_DEVICE_STATUS_UP;dev.is_laddr_valid=true;rt.dev=&dev;
 if(allocated){rt.ports=calloc(2,sizeof(*rt.ports));assert(rt.ports);rt.num_ports=2;}
 wcd.if_regmap=&map;wcd.sdev=&dev;wcd.dai[0].sruntime=&rt;wcd.dai[0].sconfig.port_mask=(1UL<<5)|(1UL<<16);
 component.wcd=&wcd;dai.component=&component;dai.id=0;hw_calls=0;fail_op=drop_op=freed=0;fail_errno=-101;
}
static void offline(int reason) {
 if(reason==0)dev.status=SLIM_DEVICE_STATUS_DOWN;
 if(reason==1)dev.is_laddr_valid=false;
 if(reason==2)dev.ctrl=NULL;
 if(reason==3)ngdc.qmi.handle=NULL;
 if(reason==4)ngdc.state=QCOM_SLIM_NGD_CTRL_DOWN;
 if(reason==5)ngdc.registered=false;
}
static int query_count;
static bool reconnect(struct slim_controller *c) {(void)c;return ++query_count>1;}
int main(void) {
 int cases=0;
 /* Including device UP/address-valid while QMI is gone, before report_absent. */
 for(int reason=0;reason<6;reason++)for(int cmd=0;cmd<=5;cmd++) {
  reset(true);offline(reason);assert(!slim_device_is_online(&dev));
  int e=wcd934x_trigger(NULL,cmd,&dai);
  if(cmd==0||cmd==4||cmd==5) {assert(e==0);assert(!rt.ports&&!rt.num_ports&&freed==1);}
  else {assert(e==-ENOTCONN);assert(rt.ports&&rt.num_ports==2&&freed==0);}
  assert(hw_calls==0);cases++;
 }
 /* Asleep is reachable via runtime resume and must use ordinary hardware stop. */
 for(int mode=0;mode<3;mode++) {
  reset(true);if(mode==1)ngdc.state=QCOM_SLIM_NGD_CTRL_ASLEEP;if(mode==2)ngdc.ctrl.is_online=NULL;
  assert(slim_device_is_online(&dev));assert(slim_stream_abort(&rt)==-EBUSY);assert(rt.ports&&freed==0);
  assert(wcd934x_trigger(NULL,SNDRV_PCM_TRIGGER_STOP,&dai)==0);assert(hw_calls==10&&freed==1&&!rt.ports);cases++;
 }
 reset(true);offline(3);assert(slim_stream_abort(&rt)==0);assert(slim_stream_abort(&rt)==0);
 assert(freed==1&&hw_calls==0&&!rt.ports&&!rt.num_ports);cases++;
 /* Every ordinary live transport failure remains visible; no blanket errno suppression. */
 for(int op=1;op<=10;op++)for(int error=0;error<2;error++) {
  reset(true);fail_op=op;fail_errno=error?-ENOTCONN:-101;
  int e=wcd934x_trigger(NULL,SNDRV_PCM_TRIGGER_STOP,&dai);
  /* Existing stream helpers ignore per-port deactivate/disconnect errors. */
  if(op==4||op==5||op==7||op==8)assert(e==0);else assert(e==fail_errno);
  assert(!rt.ports&&freed==1&&slim_device_is_online(&dev));cases++;
 }
 /* Transport can disappear after the initial snapshot, at IRQ mask or disable. */
 for(int op=1;op<=3;op++) {
  reset(true);drop_op=op;assert(wcd934x_trigger(NULL,SNDRV_PCM_TRIGGER_STOP,&dai)==0);
  assert(!rt.ports&&freed==1);assert(hw_calls==(op==1?2:op));cases++;
 }
 /* A distinct first live error is preserved even if a later operation loses transport. */
 reset(true);fail_op=1;fail_errno=-101;drop_op=3;
 assert(wcd934x_trigger(NULL,SNDRV_PCM_TRIGGER_STOP,&dai)==-101);assert(freed==1&&!rt.ports);cases++;
 /* Snapshot changed back online: abort must not silently discard a live stream. */
 reset(true);query_count=0;ngdc.ctrl.is_online=reconnect;
 assert(wcd934x_trigger(NULL,SNDRV_PCM_TRIGGER_STOP,&dai)==-EBUSY);assert(rt.ports&&freed==0);cases++;
 /* Normal start/resume/pause-release still allocate and enable then clean up. */
 for(int cmd=1;cmd<=3;cmd++) {
  reset(false);assert(wcd934x_trigger(NULL,cmd,&dai)==0);assert(rt.ports&&rt.num_ports==2);
  assert(wcd934x_trigger(NULL,SNDRV_PCM_TRIGGER_STOP,&dai)==0);assert(freed==1&&!rt.ports);cases++;
 }
 reset(false);assert(wcd934x_trigger(NULL,99,&dai)==-EINVAL);assert(hw_calls==0);cases++;
 reset(false);printf("%d actual-function scenarios passed\n",cases);return 0;
}
'''
code = prefix + ngd + online + abort + disable + unprepare + codec + tests
def run(label, text, expect=True):
    path = out / (label + '-host-private.c'); path.write_text(text)
    binary = path.with_suffix('.bin')
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-g', str(path), '-o', str(binary)], check=True)
    p = subprocess.run([str(binary)], capture_output=True)
    (out / (label + '-host-private.log')).write_bytes(p.stdout + p.stderr)
    assert (p.returncode == 0) == expect, (label, p.stdout.decode(), p.stderr.decode()[:1000])
    return p.stdout.decode().strip()
result = run('offline-stream', code)
mutants = {
    'ignore-qmi-loss': code.replace('READ_ONCE(ctrl->registered) && READ_ONCE(ctrl->qmi.handle)', 'READ_ONCE(ctrl->registered)'),
    'asleep-is-offline': code.replace('READ_ONCE(ctrl->state) != QCOM_SLIM_NGD_CTRL_DOWN', 'READ_ONCE(ctrl->state) == QCOM_SLIM_NGD_CTRL_AWAKE'),
    'live-abort-allowed': code.replace('if (slim_device_is_online(stream->dev))', 'if (false)'),
    'abort-leaks-ports': code.replace(abort, abort.replace('\tkfree(stream->ports);', '\t(void)stream;')),
    'offline-stop-touches-bus': code.replace('\tif (!slim_device_is_online(wcd->sdev))\n\t\tgoto abort;', '\tif (false)\n\t\tgoto abort;'),
    'live-error-swallowed': code.replace(codec, codec.replace('\treturn ret;\nabort:', '\treturn 0;\nabort:')),
}
for label, mutant in mutants.items():
    assert mutant != code
    run(label, mutant, False)
report = dict(stage=183, all_passed=True, result=result, negative_control_count=len(mutants),
              negative_controls=list(mutants), actual_functions=['slim_device_is_online', 'qcom_slim_ngd_is_online',
              'slim_stream_abort', 'slim_stream_disable', 'slim_stream_unprepare', 'wcd934x_slim_port_interrupts',
              'wcd934x_slim_port_clear', 'wcd934x_slim_stop', 'wcd934x_trigger'],
              actual_source_sha256=manifest['source_sha256'], sanitizer='AddressSanitizer and UndefinedBehaviorSanitizer',
              transport_regmap_allocator_and_start_enable_adapters=True,
              offline_stop_has_no_bus_messages_and_frees_ports=True, asleep_live_io_and_real_errors_preserved=True,
              existing_per_port_disable_unprepare_error_handling_not_expanded=True,
              hardware_playback_crash_retest_still_pending=True)
(ref / 'host-tests-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(result=result, negative_controls=len(mutants), all_passed=True)))
