"""Compile actual format/selection/video/descriptor functions against exported UAPI."""
from pathlib import Path
import hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel288')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
D = TREE/'drivers/media/platform/qcom/camss'
export = PRIVATE/'host-uapi'
(export/'scripts').mkdir(parents=True,exist_ok=True)
(export/'include/linux').mkdir(parents=True,exist_ok=True)
if not (export/'scripts/unifdef').exists():
    subprocess.run(['gcc',str(TREE/'scripts/unifdef.c'),'-o',str(export/'scripts/unifdef')],check=True)
for n in ['videodev2.h','v4l2-subdev.h']:
    subprocess.run(['sh',str(TREE/'scripts/headers_install.sh'),str(TREE/'include/uapi/linux'/n),str(export/'include/linux'/n)],cwd=export,check=True)
files = {n:(D/n).read_text() for n in ['camss-vfe.c','camss-video.c','camss-vfe-17x.c','camss-vfe-175-output.c','camss-vfe-175-mnds.c','camss-format.c']}
def function(source, name):
    match = re.search(r'^(?:static )?(?:int|u32|void|unsigned int|struct v4l2_mbus_framefmt \*|struct v4l2_rect \*)\s*\n?'+name+r'\([^;]*?\)\n\{',source,re.M)
    assert match, name
    return source[match.start():source.index('\n}', match.start())+2]+'\n'

names = ['__vfe_get_format','__vfe_get_compose','__vfe_get_crop','__vfe_src_pad_default','vfe_src_pad_code','vfe_try_format','vfe_try_compose','vfe_try_crop','vfe_enum_mbus_code','vfe_get_format','vfe_set_format','vfe_get_selection','vfe_set_selection','vfe_init_formats','vfe_add_output','vfe_add_yuv','vfe_set_pix']
core = ''.join(function(files['camss-vfe.c'], n) for n in names)
video = ''.join(function(files['camss-video.c'],n) for n in ['video_enum_fmt','video_enum_framesizes','__video_try_fmt'])
versions = sorted(set(re.findall(r'CAMSS_[A-Za-z0-9]+', core)) | {'CAMSS_8150'})
tables = files['camss-vfe-175-output.c']
tables = tables[tables.index('/* Input and output format'):tables.index('int vfe_175_validate_output')]
mnds = files['camss-vfe-175-mnds.c']
axis_struct = re.search(r'struct vfe_175_mnds_axis \{.*?\};',mnds,re.S)[0]
config = re.search(r'struct vfe_175_mnds_config \{.*?\};',(D/'camss-vfe-175-mnds.h').read_text(),re.S)[0]
prelude = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <linux/videodev2.h>
#include <linux/v4l2-subdev.h>
#include <linux/media-bus-format.h>
typedef uint8_t u8;typedef uint32_t u32;typedef uint64_t u64;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define clamp_t(t,x,lo,hi) ((t)(x)<(t)(lo)?(t)(lo):(t)(x)>(t)(hi)?(t)(hi):(t)(x))
#define ALIGN(x,a) (((x)+(a)-1)&~((a)-1))
#define roundup(x,a) ((((x)+(a)-1)/(a))*(a))
#define IS_ALIGNED(x,a) (!((x)&((a)-1)))
#define U16_MAX UINT16_MAX
#define BIT(x) (1U<<(x))
#define GENMASK(h,l) ((UINT32_MAX>>(31-(h)))&(UINT32_MAX<<(l)))
#define FIELD_MAX(x) ((x)>>__builtin_ctz(x))
#define div_u64(x,y) ((u64)(x)/(y))
#define SCALER_RATIO_MAX 16
#define MSM_VFE_PAD_SINK 0
#define MSM_VFE_PAD_SRC 1
#define MSM_VFE_PAD_SRC_DS4 2
#define MSM_VFE_PAD_SRC_DS16 3
#define MSM_VFE_PAD_SRC_STATS 4
#define MSM_VFE_PAD_SINK_PARAMS 5
#define MSM_VFE_PAD_NUM_PIX 6
#define MSM_VFE_PAD_NUM_RDI 2
#define VFE_LINE_PIX 3
#define VFE_175_FULL_MAX_WIDTH 4096
#define VFE_175_FULL_MAX_HEIGHT 4096
#define VFE_175_FULL_Y 3
#define VFE_175_FULL_C 4
#define VFE_175_SCALE_PHASE_MULT GENMASK(21,0)
#define CAMSS_FRAME_MIN_WIDTH 1
#define CAMSS_FRAME_MAX_WIDTH 8191
#define CAMSS_FRAME_MIN_HEIGHT 1
#define CAMSS_FRAME_MAX_HEIGHT_RDI 8191
#define CAMSS_FRAME_MAX_HEIGHT_PIX 4096
#define BITS_PER_BYTE 8
static unsigned long lcm_not_zero(unsigned long a,unsigned long b){unsigned long x=a,y=b;while(y){unsigned long t=x%y;x=y;y=t;}return x?a/x*b:0;}
struct vfe_device;struct vfe_line;
struct v4l2_subdev {struct vfe_line *priv;};
struct v4l2_subdev_state {struct v4l2_mbus_framefmt fmt[6];struct v4l2_rect compose,crop;};
struct v4l2_subdev_fh {struct v4l2_subdev_state *state;};
struct file {void *private_data;};
struct device {int unused;};
#define v4l2_get_subdevdata(sd) ((sd)->priv)
#define video_drvdata(f) ((struct camss_video *)(f)->private_data)
#define v4l2_subdev_state_get_format(s,p) (&(s)->fmt[p])
#define v4l2_subdev_state_get_compose(s,p) (&(s)->compose)
#define v4l2_subdev_state_get_crop(s,p) (&(s)->crop)
struct camss_video {struct v4l2_format active_fmt;enum v4l2_buf_type type;unsigned int bpl_alignment,line_based,nformats;const struct camss_format_info *formats;const struct v4l2_frmsize_stepwise *frame_sizes;};
struct vfe_wm {u8 bus_client,plane;};
struct vfe_output {struct vfe_line *line;u8 pad,comp_group,wm_num;struct vfe_wm wm[3];struct camss_video video_out;};
struct vfe_line {bool is_pix;unsigned int nformats,num_pads,num_outputs;const struct camss_format_info *formats;struct v4l2_mbus_framefmt fmt[2];struct v4l2_rect compose,crop;struct vfe_output output[5];struct vfe_device *owner;};
struct resources {bool is_lite,pix_no_crop;unsigned int line_num;const struct camss_formats *formats_pix_out;const struct v4l2_frmsize_stepwise *pix_sink_frame_sizes,*pix_frame_sizes;};
struct platform {int version;};struct camss {struct platform *res;};
struct vfe_device {struct resources *res;struct camss *camss;struct vfe_line line[4];int video_ops;struct {void(*comp_done)(struct vfe_device*,u8);}isr_ops;};
#define to_vfe(l) ((l)->owner)
static const int vfe_video_ops_175=175;
static unsigned int base_init_calls;
static void vfe_subdev_init(struct device *d,struct vfe_device*v){(void)d;(void)v;base_init_calls++;}
static void vfe_175_comp_done(struct vfe_device*v,u8 c){(void)v;(void)c;}
static int vfe_set_selection(struct v4l2_subdev*,struct v4l2_subdev_state*,struct v4l2_subdev_selection*);
'''
prelude += '\nenum { '+','.join(versions)+' };\n'
prelude += '#include "'+str(D/'camss-format.h')+'"\n'
functions = function(files['camss-format.c'],'camss_format_get_bpl_alignment')+function(files['camss-format.c'],'camss_format_find_code')
functions += core+video+function(files['camss-vfe-17x.c'],'vfe_subdev_init_175')
functions += function(files['camss-vfe-175-output.c'],'vfe_175_validate_output')
functions += ''.join(function(mnds,n) for n in ['vfe_175_mnds_axis','vfe_175_mnds_axes','vfe_175_mnds_from_line'])
tests = (ROOT/'pix-negotiation-tests.c').read_text()
source = prelude+tables+axis_struct+'\n'+config+'\n'+functions+tests
path = PRIVATE/'pix-negotiation-host-private.c';path.write_text(source)
for name in ['pix-negotiation-compile-private.log','pix-negotiation-test-private.log']:
    p=PRIVATE/name
    if p.exists():
        i=1
        while (PRIVATE/(name+f'.attempt{i}')).exists():i+=1
        p.rename(PRIVATE/(name+f'.attempt{i}'))
binary = PRIVATE/'pix-negotiation-host-private'
compile = subprocess.run(['gcc','-std=gnu11','-g','-O1','-Wall','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-I'+str(export/'include'),str(path),'-o',str(binary)],text=True,capture_output=True)
(PRIVATE/'pix-negotiation-compile-private.log').write_text(compile.stdout+compile.stderr)
assert compile.returncode==0, compile.stderr[-9000:]
result = subprocess.run([str(binary)],text=True,capture_output=True)
(PRIVATE/'pix-negotiation-test-private.log').write_text(result.stdout+result.stderr)
assert result.returncode==0, result.stdout+result.stderr
resource = (D/'camss.c').read_text()
section = resource[resource.index('static const struct camss_subdev_resources vfe_res_8150[]'):resource.index('static const struct camss_subdev_resources csiphy_res_8250[]')]
assert section.count('.line_num = 4,')==2 and section.count('.pix_no_crop = true')==2
assert section.count('.hw_ops = &vfe_ops_175')==2
report = dict(stage=288, exit=0, asan_ubsan=True, actual_core_selection_and_video_format_functions=True,
              exported_current_kernel_uapi=True, source_sha256={n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in files},
              harness_sha256=hashlib.sha256(source.encode()).hexdigest(), bayer_codes=16,
              capture_dimension_boundary_inputs=65536*8, capture_enum_only_nv12=True,
              actual_descriptor_initialization=True, negotiated_layout_accepted_by_mnds_and_dma=True,
              legacy_and_rdi_format_behavior_checked=True, try_state_isolation=True,
              hardware_not_tested=True, not_deployed=True, output=result.stdout.strip())
(ROOT/'pix-negotiation-host-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
