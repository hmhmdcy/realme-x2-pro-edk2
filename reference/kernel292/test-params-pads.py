"""Exercise actual pad guards and VFE175 output declarations with ASan/UBSan."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
common=(TREE/'drivers/media/platform/qcom/camss/camss-vfe.c').read_text()
hw=(TREE/'drivers/media/platform/qcom/camss/camss-vfe-17x.c').read_text()
def function(source,signature):
 start=source.index(signature);return source[start:source.index('\n}',start)+2]
parts=[function(common,'static bool vfe_pad_supported(')]
parts.append('static struct v4l2_mbus_framefmt *\n'+function(common,'__vfe_get_format('))
for name in ['vfe_enum_mbus_code','vfe_enum_frame_size','vfe_get_format']:
 parts.append(function(common,'static int '+name+'('))
for name in ['vfe_add_output','vfe_add_yuv','vfe_add_params','vfe_set_pix']:
 parts.append(function(common,'void '+name+'('))
parts.append(function(hw,'static void vfe_subdev_init_175('))
prelude=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <linux/media-bus-format.h>
#include <linux/v4l2-subdev.h>
typedef uint8_t u8;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define MSM_VFE_PAD_SINK 0
#define MSM_VFE_PAD_SRC 1
#define MSM_VFE_PAD_SRC_DS4 2
#define MSM_VFE_PAD_SRC_DS16 3
#define MSM_VFE_PAD_SRC_STATS 4
#define MSM_VFE_PAD_SINK_PARAMS 5
#define MSM_VFE_PAD_NUM_PIX 6
#define VFE_LINE_PIX 3
#define V4L2_BUF_TYPE_META_OUTPUT 14
struct vfe_device;
struct device {int unused;};
struct vfe_wm {u8 bus_client,plane;};
struct camss_video {bool streaming;};
struct vfe_output {unsigned int pad,comp_group,wm_num;struct vfe_wm wm[3];struct camss_video video_out;};
struct fmt_entry {uint32_t code;};
struct vfe_line {bool is_pix;unsigned int num_pads,num_outputs,nformats;struct fmt_entry formats[1];struct vfe_output output[5];struct v4l2_mbus_framefmt fmt[6];struct vfe_device *owner;};
struct v4l2_subdev {struct vfe_line *line;};
struct v4l2_subdev_state {struct v4l2_mbus_framefmt fmt[6];};
struct resources {bool is_lite;unsigned int line_num;};
struct video_ops {unsigned int id;};
struct isr_ops {void (*comp_done)(struct vfe_device*,unsigned int);};
struct vfe_device {const struct resources *res;struct vfe_line line[4];struct video_ops video_ops;struct isr_ops isr_ops;};
#define v4l2_get_subdevdata(sd) ((sd)->line)
#define to_vfe(line) ((line)->owner)
#define vb2_is_streaming(q) ((q)->streaming)
static unsigned int try_calls,state_calls,base_init_calls;
static struct v4l2_mbus_framefmt *v4l2_subdev_state_get_format(struct v4l2_subdev_state *state,unsigned int pad) {assert(state&&pad<6);state_calls++;return &state->fmt[pad];}
static uint32_t vfe_src_pad_code(struct vfe_line *line,uint32_t sink,unsigned int index,uint32_t unused) {(void)line;(void)sink;(void)unused;return index?0:MEDIA_BUS_FMT_UYVY8_1_5X8;}
static void vfe_try_format(struct vfe_line *line,struct v4l2_subdev_state *state,unsigned int pad,struct v4l2_mbus_framefmt *fmt,enum v4l2_subdev_format_whence which) {
 (void)line;(void)state;(void)which;try_calls++;
 if(pad>=4){memset(fmt,0,sizeof(*fmt));fmt->code=MEDIA_BUS_FMT_METADATA_FIXED;return;}
 fmt->code=MEDIA_BUS_FMT_UYVY8_1_5X8;fmt->width=320;fmt->height=240;
}
static const struct video_ops vfe_video_ops_175={175};
static void vfe_175_comp_done(struct vfe_device *v,unsigned int n) {(void)v;(void)n;assert(0);}
static void vfe_subdev_init(struct device *dev,struct vfe_device *v) {
 (void)dev;base_init_calls++;for(unsigned int i=0;i<4;i++){v->line[i].owner=v;v->line[i].num_pads=2;v->line[i].num_outputs=1;v->line[i].output[0].pad=1;v->line[i].output[0].wm_num=1;v->line[i].output[0].wm[0].bus_client=i;}
}
'''
tests=r'''
int main(void) {
 struct vfe_line line={.num_pads=6,.nformats=1,.formats={{MEDIA_BUS_FMT_SRGGB10_1X10}}};
 struct v4l2_subdev sd={&line};struct v4l2_subdev_state state={0};
 line.fmt[0].code=MEDIA_BUS_FMT_SRGGB10_1X10;line.fmt[1].code=MEDIA_BUS_FMT_UYVY8_1_5X8;
 for(unsigned int mask=0;mask<16;mask++) {
  memset(line.output,0,sizeof(line.output));line.is_pix=true;line.num_outputs=1;line.num_pads=6;
  for(unsigned int bit=0;bit<4;bit++)if(mask&(1u<<bit))line.output[line.num_outputs++].pad=bit+2;
  for(unsigned int pad=0;pad<100;pad++)for(unsigned int which=0;which<2;which++) {
   bool supported=pad<2||(pad<6&&(mask&(1u<<(pad-2))));unsigned int before=try_calls,prior_state=state_calls;
   assert(vfe_pad_supported(&line,pad)==supported);
   struct v4l2_subdev_format format={.pad=pad,.which=which};
   assert(vfe_get_format(&sd,&state,&format)==(supported?0:-EINVAL));
   struct v4l2_subdev_mbus_code_enum code={.pad=pad,.which=which};
   assert(vfe_enum_mbus_code(&sd,&state,&code)==(supported?0:-EINVAL));
   struct v4l2_subdev_frame_size_enum size={.pad=pad,.which=which,.code=MEDIA_BUS_FMT_UYVY8_1_5X8};
   assert(vfe_enum_frame_size(&sd,&state,&size)==(!supported?-EINVAL:pad>=4?-ENOTTY:0));
   if(!supported)assert(before==try_calls&&prior_state==state_calls);
  }
  assert(!vfe_pad_supported(&line,UINT_MAX));
 }
 /* A real RDI line accepts only sink/source even when PIX roles exist elsewhere. */
 line.num_pads=2;line.num_outputs=1;line.is_pix=false;
 for(unsigned int pad=0;pad<8;pad++)assert(vfe_pad_supported(&line,pad)==(pad<2));
 for(unsigned int lite=0;lite<2;lite++)for(unsigned int count=3;count<=4;count++) {
  struct resources res={lite,count};struct vfe_device v={.res=&res};vfe_subdev_init_175(NULL,&v);
  struct vfe_line *pix=&v.line[3];assert(v.video_ops.id==175&&v.isr_ops.comp_done==vfe_175_comp_done);
  if(!lite&&count==4){
   assert(pix->is_pix&&pix->num_outputs==2&&pix->num_pads==6);
   assert(pix->output[0].wm_num==2&&pix->output[0].wm[0].bus_client==3&&pix->output[0].wm[1].bus_client==4);
   assert(pix->output[1].pad==5&&!pix->output[1].wm_num);
   for(unsigned int p=0;p<6;p++)assert(vfe_pad_supported(pix,p)==(p==0||p==1||p==5));
  }else assert(!pix->is_pix&&pix->num_outputs==1&&pix->num_pads==2);
  for(unsigned int n=0;n<3;n++)assert(!v.line[n].is_pix&&v.line[n].num_outputs==1&&v.line[n].output[0].wm_num==1);
 }
 assert(base_init_calls==4);
 puts("PASS: actual sparse pad guards, TRY/ACTIVE, enum/get bounds, declared metadata, VFE175 FULL/params and lite/RDI isolation");
 return 0;
}
'''
harness=prelude+'\n\n'.join(parts)+tests
p=host.PRIVATE/'pad-params-tests-private.c';p.write_text(harness);binary=p.with_suffix('')
q=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(p),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'pad-params-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary)],capture_output=True,timeout=20);(host.PRIVATE/'pad-params-tests-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
report=dict(stage=292,asan_ubsan=True,actual_pad_and_initialization_functions=True,capability_masks=16,pad_indices_checked=100,try_and_active=True,
 no_format_or_state_access_for_unsupported_pad=True,metadata_zero_dma=True,full_clients_3_4_preserved=True,lite_and_rdi_isolation=True,
 harness_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),output=q.stdout.decode().strip(),not_deployed=True)
(ROOT/'pad-params-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
