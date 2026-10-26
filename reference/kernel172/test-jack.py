from pathlib import Path
import hashlib, json, re, subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel172')

def function(s, name):
    hit = re.search(r'^(?:static )?(?:int|void) ' + name + r'\([^;{]*\)\n\{', s, re.M)
    assert hit, name
    a = s.index('{', hit.start()); b = a + 1; depth = 1
    while depth:
        depth += (s[b] == '{') - (s[b] == '}'); b += 1
    return s[hit.start():b] + '\n'

def run(label, code):
    source = out / (label + '-private.c'); source.write_text(code)
    binary = out / (label + '-private')
    p = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                        '-Wno-sign-compare', '-Wno-unused-function', '-g', '-fsanitize=address,undefined',
                        str(source), '-o', str(binary)], capture_output=True)
    (out / (label + '-build-private.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, p.stderr.decode()
    p = subprocess.run([str(binary)], capture_output=True)
    (out / (label + '-run-private.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0 and not p.stderr, (label, p.stderr.decode())
    return p.stdout.decode().strip()

codec = (k / 'sound/soc/codecs/wcd934x.c').read_text()
mbhc = (k / 'sound/soc/codecs/wcd-mbhc-v2.c').read_text()
old_codec = (out / 'before-private/sound/soc/codecs/wcd934x.c').read_text()
old_mbhc = (out / 'before-private/sound/soc/codecs/wcd-mbhc-v2.c').read_text()
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define ENOTSUPP 524
typedef uint32_t u32;
#define dev_info(...) ((void)0)
#define dev_dbg(...) ((void)0)
#define dev_err(...) ((void)0)
#define WCD_MBHC_DEF_BUTTONS 4
#define MIC_BIAS_2 2
#define WCD934X_ANA_MICB1 1
#define WCD934X_ANA_MICB2 2
#define WCD934X_ANA_MICB3 3
#define WCD934X_ANA_MICB4 4
#define WCD934X_TEST_DEBUG_PAD_DRVCTL_0 5
#define WCD934X_MICB_VAL_MASK 0xff
#define WCD934X_MCLK_CLK_9P6MHZ 9600000
#define WCD9XXX_DMIC_SAMPLE_RATE_4P8MHZ 4800000
#define WCD9XXX_DMIC_SAMPLE_RATE_4P096MHZ 4096000
struct device_node { int unused; };
struct device { struct device_node *of_node; };
struct snd_soc_jack { int id; };
struct wcd_mbhc_config { unsigned int hs_thr, hph_thr, micb_mv, btn_high[4]; bool hphl_swh, gnd_swh; };
struct wcd_mbhc { struct wcd_mbhc_config *cfg; struct snd_soc_jack *jack; };
struct common { unsigned int micb_mv[4], micb_vout[4]; };
struct wcd934x_codec { bool mbhc_started; struct snd_soc_jack *mbhc_jack;
 struct wcd_mbhc *mbhc; struct wcd_mbhc_config mbhc_cfg; struct common common;
 unsigned int rate, dmic_sample_rate; };
struct snd_soc_component { struct device *dev; struct wcd934x_codec *data; };
static int start_result, starts, stops, parses, parse_result, updates, update_fail;
static bool array_present;
static struct wcd934x_codec *dev_get_drvdata(struct device *d);
static struct wcd934x_codec *current;
static struct wcd934x_codec *dev_get_drvdata(struct device *d) { return current; }
static struct wcd934x_codec *snd_soc_component_get_drvdata(struct snd_soc_component *c) { return c->data; }
static bool of_machine_is_compatible(const char *s) { return true; }
static int wcd_mbhc_initialise(struct wcd_mbhc *m) { starts++; return start_result; }
static void wcd_mbhc_stop(struct wcd_mbhc *m) { stops++; }
static int wcd_dt_parse_micbias_info(struct common *c) {
 parses++; if (parse_result) return parse_result;
 for (int i=0; i<4; i++) { c->micb_mv[i]=2700; c->micb_vout[i]=17; } return 0;
}
static int snd_soc_component_update_bits(struct snd_soc_component *c, int reg, int mask, int v) {
 updates++; return updates == update_fail ? -EIO : 1;
}
static bool of_property_read_bool(struct device_node *n, const char *s) { return false; }
static int of_property_read_u32(struct device_node *n, const char *s, int *value) {
 *value = strstr(s, "headset") ? 1700000 : 100000; return 0;
}
static int of_property_read_u32_array(struct device_node *n, const char *s, unsigned int *values, int count) {
 if (!array_present) return -ENOENT;
 for (int i=0; i<count; i++) { values[i]=(i+1)*100000; } return 0;
}
'''
codec_tests = r'''
int main(void) {
 struct device_node node={0}; struct device dev={.of_node=&node};
 struct wcd_mbhc m={0}; struct wcd934x_codec w={.mbhc=&m};
 struct snd_soc_component comp={.dev=&dev,.data=&w}; struct snd_soc_jack a={1}, b={2}; current=&w;
 w.mbhc_cfg.hs_thr=1700; w.mbhc_cfg.hph_thr=100;
 assert(wcd934x_init_dmic(&comp)==0); assert(parses==1 && updates==5 && w.mbhc_cfg.micb_mv==2700);
 parse_result=-EINVAL; updates=0; assert(wcd934x_init_dmic(&comp)==-EINVAL && updates==0); parse_result=0;
 for (int i=1;i<=5;i++) { updates=0; update_fail=i; assert(wcd934x_init_dmic(&comp)==-EIO && updates==i); }
 update_fail=0;
 assert(wcd_mbhc_start(NULL,&w.mbhc_cfg,&a)==-EINVAL);
 assert(wcd_mbhc_start(&m,NULL,&a)==-EINVAL);
 assert(wcd_mbhc_start(&m,&w.mbhc_cfg,NULL)==-EINVAL);
 w.mbhc_cfg.micb_mv=0; assert(wcd_mbhc_start(&m,&w.mbhc_cfg,&a)==-EINVAL && starts==0 && m.cfg==NULL);
 w.mbhc_cfg.micb_mv=2700;
 start_result=-EIO; assert(wcd934x_codec_set_jack(&comp,&a,NULL)==-EIO);
 assert(!w.mbhc_started && w.mbhc_jack==NULL && starts==1 && stops==0);
 start_result=0; assert(wcd934x_codec_set_jack(&comp,&a,NULL)==0);
 assert(w.mbhc_started && w.mbhc_jack==&a && starts==2);
 assert(wcd934x_codec_set_jack(&comp,&a,NULL)==0 && starts==2 && stops==0 && w.mbhc_started);
 assert(wcd934x_codec_set_jack(&comp,&b,NULL)==-EBUSY && starts==2 && stops==0 && w.mbhc_jack==&a);
 assert(wcd934x_codec_set_jack(&comp,NULL,NULL)==0 && stops==1 && !w.mbhc_started && w.mbhc_jack==NULL);
 assert(wcd934x_codec_set_jack(&comp,NULL,NULL)==0 && stops==1);
 struct wcd_mbhc_config cfg={0}; assert(wcd_dt_parse_mbhc_data(&dev,&cfg)==0);
 assert(cfg.hs_thr==1700 && cfg.hph_thr==100);
 for (int i=0;i<4;i++) assert(cfg.btn_high[i]==500);
 array_present=true; assert(wcd_dt_parse_mbhc_data(&dev,&cfg)==0);
 for (int i=0;i<4;i++) assert(cfg.btn_high[i]==(i+1)*100);
 puts("codec: 18 fault/state/unit scenarios passed"); return 0;
}
'''
code = prefix + function(mbhc, 'wcd_mbhc_start') + function(codec, 'wcd934x_codec_set_jack')
code += function(codec, 'wcd934x_init_dmic') + function(mbhc, 'wcd_dt_parse_mbhc_data') + codec_tests
codec_result = run('codec-jack', code)
# The same detector must demonstrate the baseline failures, not merely exercise stubs.
negative_tests = r'''
int main(void) {
 struct device_node node={0}; struct device dev={.of_node=&node};
 struct wcd_mbhc m={0}; struct wcd934x_codec w={.mbhc=&m};
 struct snd_soc_component comp={.dev=&dev,.data=&w}; struct snd_soc_jack a={1}; current=&w;
 w.mbhc_cfg.micb_mv=w.common.micb_mv[1]; assert(wcd934x_init_dmic(&comp)==0);
 assert(w.mbhc_cfg.micb_mv==0 && w.common.micb_mv[1]==2700);
 start_result=-EIO; assert(wcd934x_codec_set_jack(&comp,&a,NULL)==-EIO && w.mbhc_started);
 w.mbhc_started=false; start_result=0; assert(wcd934x_codec_set_jack(&comp,&a,NULL)==0);
 assert(wcd934x_codec_set_jack(&comp,&a,NULL)==0 && !w.mbhc_started && stops==1);
 struct wcd_mbhc_config cfg={0}; assert(wcd_dt_parse_mbhc_data(&dev,&cfg)==0 && cfg.btn_high[0]==500000);
 puts("baseline: zero bias, failed-start flag, repeated-bind stop, default-unit defects reproduced"); return 0;
}
'''
negative_result = run('codec-baseline', prefix + function(old_mbhc, 'wcd_mbhc_start') +
                      function(old_codec, 'wcd934x_codec_set_jack') + function(old_codec, 'wcd934x_init_dmic') +
                      function(old_mbhc, 'wcd_dt_parse_mbhc_data') + negative_tests)

machine = (k / 'sound/soc/qcom/samurai-audio.c').read_text()
data = machine[machine.index('struct samurai_audio_data {'):machine.index('static int samurai_setup_jack')]
machine_prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define SND_JACK_HEADPHONE 1
#define SND_JACK_MICROPHONE 2
#define SND_JACK_HEADSET 3
#define SND_JACK_BTN_0 4
#define SND_JACK_BTN_1 8
#define SND_JACK_BTN_2 16
#define SND_JACK_BTN_3 32
#define KEY_PLAYPAUSE 1
#define KEY_VOICECOMMAND 2
#define KEY_VOLUMEUP 3
#define KEY_VOLUMEDOWN 4
#define SLIMBUS_0_RX 1
#define SLIMBUS_0_TX 2
#define QUATERNARY_MI2S_RX 3
#define SNDRV_PCM_STREAM_PLAYBACK 0
#define dev_info(...) ((void)0)
struct snd_soc_component { int id; };
struct snd_soc_jack { void *jack; };
struct snd_soc_jack_pin { const char *pin; int mask, invert; };
struct snd_soc_card { void *data; void *dev; };
struct snd_soc_dai { struct snd_soc_component *component; };
struct snd_soc_dai_link { int id; };
struct snd_soc_pcm_runtime { struct snd_soc_card *card; struct snd_soc_dai_link *dai_link; struct snd_soc_dai **codecs; int ncodecs; };
#define for_each_rtd_codec_dais(rtd,i,c) for ((i)=0;(i)<(rtd)->ncodecs && ((c)=(rtd)->codecs[i],1);(i)++)
static int creates, key_calls, clock_calls, binds, maps, create_ret, key_fail, clock_ret, bind_ret, map_ret;
static void *snd_soc_card_get_drvdata(struct snd_soc_card *c) { return c->data; }
static int snd_soc_card_jack_new_pins(struct snd_soc_card *c,const char *s,int type,struct snd_soc_jack *j,struct snd_soc_jack_pin *p,int n) {
 creates++; assert(n==5 && type==63); j->jack=j; return create_ret;
}
static int snd_jack_set_key(void *j,unsigned int b,unsigned int key) { key_calls++; return key_calls==key_fail ? -ENOMEM : 0; }
static int snd_soc_dai_set_sysclk(struct snd_soc_dai *d,int id,int rate,int dir) { clock_calls++; assert(rate==9600000); return clock_ret; }
static int snd_soc_component_set_jack(struct snd_soc_component *c,struct snd_soc_jack *j,void *data) { binds++; return bind_ret; }
static int snd_soc_dai_set_channel_map(struct snd_soc_dai *d,int ntx,unsigned int *tx,int nrx,unsigned int *rx) {
 maps++; assert(ntx==16 && nrx==13 && tx[0]==128 && tx[15]==143 && rx[0]==144 && rx[12]==156); return map_ret;
}
'''
machine_tests = r'''
int main(void) {
 struct samurai_audio_data data={0}; struct snd_soc_card card={.data=&data}; struct snd_soc_component c={1}, other={2};
 struct snd_soc_dai dai={.component=&c}; struct snd_soc_dai *ds[]={&dai}; struct snd_soc_dai_link link={.id=SLIMBUS_0_RX};
 struct snd_soc_pcm_runtime r={.card=&card,.dai_link=&link,.codecs=ds,.ncodecs=1};
 create_ret=-ENOMEM; assert(samurai_init(&r)==-ENOMEM && binds==0 && !data.jack_created);
 create_ret=0; key_fail=2; assert(samurai_init(&r)==-ENOMEM && binds==0 && !data.jack_created);
 key_fail=0; key_calls=0; clock_ret=-EIO; assert(samurai_init(&r)==-EIO && binds==0 && data.jack_created && !data.jack_component);
 clock_ret=0; bind_ret=-EIO; assert(samurai_init(&r)==-EIO && !data.jack_component);
 bind_ret=0; assert(samurai_init(&r)==0 && data.jack_component==&c && maps==5 && binds==2);
 int clock_before=clock_calls, key_before=key_calls, create_before=creates;
 link.id=SLIMBUS_0_TX; assert(samurai_init(&r)==0 && maps==6 && binds==2 && clock_calls==clock_before && creates==create_before && key_calls==key_before);
 link.id=QUATERNARY_MI2S_RX; assert(samurai_init(&r)==0 && maps==6 && binds==2);
 link.id=SLIMBUS_0_TX; map_ret=-EIO; assert(samurai_init(&r)==-EIO && binds==2); map_ret=0;
 dai.component=&other; assert(samurai_init(&r)==-EINVAL && binds==2 && data.jack_component==&c);
 puts("machine: 9 runtime and failure scenarios passed; RX/TX maps both retained"); return 0;
}
'''
machine_result = run('machine-jack', machine_prefix + data + function(machine, 'samurai_setup_jack') + function(machine, 'samurai_init') + machine_tests)
report = dict(stage=172, extracted_actual_functions=True, sanitizers=['address','undefined'],
              codec_scenarios=18, machine_scenarios=9, baseline_negative_control_defects=4,
              codec_result=codec_result, baseline_result=negative_result, machine_result=machine_result,
              physical_detection_and_sound_not_tested=True, all_passed=True)
(ref / 'host-tests-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'host-tests-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
