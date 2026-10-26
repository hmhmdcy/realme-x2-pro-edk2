"""Exercise actual CAMIF/17x functions with pinned OEM register and IRQ oracles."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel281')
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
directory = TREE / 'drivers/media/platform/qcom/camss'
camif = (directory / 'camss-vfe-175-camif.c').read_text()
common = (directory / 'camss-vfe-17x.c').read_text()
pins = json.loads((ROOT / 'oem-programming-sources.json').read_text())['sources']
pin = next(v for k,v in pins.items() if k.endswith('/cam_vfe175.h'))
oem_bytes = (PRIVATE / pin['local_name']).read_bytes()
assert hashlib.sha256(oem_bytes).hexdigest() == pin['sha256']
oem = oem_bytes.decode()
mapping = dict(VFE_175_CORE_CFG='core_cfg', VFE_175_CAMIF_CMD='camif_cmd',
    VFE_175_CAMIF_CONFIG='camif_config', VFE_175_CAMIF_LINE_SKIP='line_skip_pattern',
    VFE_175_CAMIF_PIXEL_SKIP='pixel_skip_pattern', VFE_175_CAMIF_SKIP_PERIOD='skip_period',
    VFE_175_CAMIF_IRQ_SUBSAMPLE='irq_subsample_pattern', VFE_175_CAMIF_EPOCH='epoch_irq',
    VFE_175_RAW_CROP_WIDTH='raw_crop_width_cfg', VFE_175_RAW_CROP_HEIGHT='raw_crop_height_cfg')
for macro, field in mapping.items():
    actual = int(re.search(r'#define\s+' + macro + r'\s+(0x[0-9a-fA-F]+)', camif)[1], 0)
    expected = int(re.search(r'\.' + field + r'\s*=\s*(0x[0-9a-fA-F]+|\d+)', oem)[1], 0)
    assert actual == expected, (macro, field)
for field, expected in [('pixel_pattern_shift', 0), ('pixel_pattern_mask', 7),
                        ('reg_update_cmd_data', 1), ('reg_update_irq_mask', 16),
                        ('sof_irq_mask', 1), ('epoch_line_cfg', 0x140014)]:
    assert int(re.search(r'\.' + field + r'\s*=\s*(0x[0-9a-fA-F]+|\d+)', oem)[1], 0) == expected


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}\n', start) + 3]


defines = common[common.index('#define VFE_GLOBAL_RESET_CMD'):common.index('static inline void vfe_reg_set')]
functions = re.sub(r'^#include.*\n', '', camif, flags=re.M)
functions += defines + ''.join(function(common, signature) for signature in [
    'static u32 vfe_reg_update_mask(', 'static void vfe_reg_update(',
    'static inline void vfe_reg_update_clear(', 'static irqreturn_t vfe_isr(',
    'static int vfe_enable('])
functions += function((directory / 'camss-vfe.c').read_text(), 'int vfe_enable_v2(')
mbus = (TREE / 'include/uapi/linux/media-bus-format.h').read_text()
media_defines = '\n'.join(line for line in mbus.splitlines() if line.startswith('#define MEDIA_BUS_FMT_'))
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef int irqreturn_t;
#define BIT(n) (1u << (n))
#define GENMASK(h,l) ((UINT32_MAX >> (31 - (h))) & (UINT32_MAX << (l)))
#define FIELD_MAX(m) ((m) >> __builtin_ctz(m))
#define FIELD_PREP(m,v) (((u32)(v) << __builtin_ctz(m)) & (m))
#define min_t(t,a,b) ((t)(a) < (t)(b) ? (t)(a) : (t)(b))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define CAMSS_8150 8150
#define MSM_VFE_PAD_SINK 0
#define MSM_VFE_COMPOSITE_IRQ_NUM 4
#define MSM_VFE_IMAGE_MASTERS_NUM 7
#define IRQ_HANDLED 1
enum vfe_line_id { VFE_LINE_RDI0=0, VFE_LINE_RDI1, VFE_LINE_RDI2, VFE_LINE_PIX };
struct vfe_device;
struct v4l2_mbus_framefmt { u32 code,width,height; };
struct vfe_line { bool is_pix; struct vfe_device *vfe; struct v4l2_mbus_framefmt fmt[1]; };
#define to_vfe(l) ((l)->vfe)
struct vfe_hw_ops { int (*vfe_line_prepare)(struct vfe_line *); void (*enable_irq)(struct vfe_device *); };
struct resources { bool is_lite; unsigned int line_num; const struct vfe_hw_ops *hw_ops; };
struct camss_resources { int version; };
struct camss { const struct camss_resources *res; };
struct isr_ops {
 void (*reset_ack)(struct vfe_device *);
 void (*reg_update)(struct vfe_device *, int);
 void (*sof)(struct vfe_device *, int);
 void (*comp_done)(struct vfe_device *, int);
 void (*wm_done)(struct vfe_device *, int);
};
struct vfe_device {
 unsigned char *base;
 struct resources *res;
 struct camss *camss;
 struct vfe_line line[4];
 struct isr_ops isr_ops;
 u32 reg_update;
 int stream_lock,stream_count,was_streaming;
};
static unsigned char mmio[0x4000];
static struct {u32 address,value;} writes[1024];
static unsigned int nwrites,nreads,barriers;
static unsigned int reset_ack,update_ack[4],sof_ack[4],wm_ack[24],comp_ack[6];
static unsigned int irq_enables,get_calls,put_calls,output_enables,prepare_calls,params_calls;
static int get_result,prepare_result,output_result;
static u32 rd(const void *address) {
 size_t offset=(const unsigned char *)address-mmio;
 assert(offset<sizeof(mmio) && !(offset&3)); nreads++;
 return *(const u32 *)(mmio+offset);
}
static void wr(u32 value,void *address) {
 size_t offset=(unsigned char *)address-mmio;
 assert(offset<sizeof(mmio) && !(offset&3) && nwrites<ARRAY_SIZE(writes));
 writes[nwrites].address=offset;writes[nwrites++].value=value;
 *(u32 *)(mmio+offset)=value;
}
#define readl_relaxed rd
#define writel_relaxed wr
#define wmb() do {barriers++;} while(0)
#define mutex_lock(p) do {assert(*(p)==0);(*(p))++;} while(0)
#define mutex_unlock(p) do {assert(*(p)==1);(*(p))--;} while(0)
static void vfe_enable_irq_common(struct vfe_device *vfe) {(void)vfe;irq_enables++;}
static int vfe_get_output_v2(struct vfe_line *line) {(void)line;get_calls++;return get_result;}
static int vfe_put_output(struct vfe_line *line) {(void)line;put_calls++;return 0;}
static int vfe_enable_output_v2(struct vfe_line *line) {(void)line;output_enables++;return output_result;}
static int prepare_mock(struct vfe_line *line) {(void)line;prepare_calls++;return prepare_result;}
static void vfe_params_apply_queued(struct vfe_device *vfe,struct vfe_line *line) {(void)vfe;(void)line;params_calls++;}
static void reset_cb(struct vfe_device *vfe) {(void)vfe;reset_ack++;}
static void update_cb(struct vfe_device *vfe,int id) {(void)vfe;assert(id>=0&&id<4);update_ack[id]++;}
static void sof_cb(struct vfe_device *vfe,int id) {(void)vfe;assert(id>=0&&id<4);sof_ack[id]++;}
static void wm_cb(struct vfe_device *vfe,int id) {(void)vfe;assert(id>=0&&id<24);wm_ack[id]++;}
static void comp_cb(struct vfe_device *vfe,int id) {(void)vfe;assert(id>=0&&id<6);comp_ack[id]++;}
'''
tests = r'''
static void clear_mmio(void) {
 memset(mmio,0,sizeof(mmio));nwrites=nreads=barriers=0;
 memset(update_ack,0,sizeof(update_ack));memset(sof_ack,0,sizeof(sof_ack));
 memset(wm_ack,0,sizeof(wm_ack));memset(comp_ack,0,sizeof(comp_ack));reset_ack=0;
}
static void clear_enable(void) {
 irq_enables=get_calls=put_calls=output_enables=prepare_calls=params_calls=0;
 get_result=prepare_result=output_result=0;
}
int main(void) {
 const u32 codes[4][4]={
  {MEDIA_BUS_FMT_SRGGB8_1X8,MEDIA_BUS_FMT_SRGGB10_1X10,MEDIA_BUS_FMT_SRGGB12_1X12,MEDIA_BUS_FMT_SRGGB14_1X14},
  {MEDIA_BUS_FMT_SGRBG8_1X8,MEDIA_BUS_FMT_SGRBG10_1X10,MEDIA_BUS_FMT_SGRBG12_1X12,MEDIA_BUS_FMT_SGRBG14_1X14},
  {MEDIA_BUS_FMT_SBGGR8_1X8,MEDIA_BUS_FMT_SBGGR10_1X10,MEDIA_BUS_FMT_SBGGR12_1X12,MEDIA_BUS_FMT_SBGGR14_1X14},
  {MEDIA_BUS_FMT_SGBRG8_1X8,MEDIA_BUS_FMT_SGBRG10_1X10,MEDIA_BUS_FMT_SGBRG12_1X12,MEDIA_BUS_FMT_SGBRG14_1X14}};
 struct camss_resources cr={.version=CAMSS_8150};struct camss camss={.res=&cr};
 struct vfe_hw_ops ops={.vfe_line_prepare=vfe_175_camif_prepare};
 struct resources res={.line_num=3,.hw_ops=&ops};
 struct vfe_device vfe={.base=mmio,.res=&res,.camss=&camss,
  .isr_ops={reset_cb,update_cb,sof_cb,comp_cb,wm_cb}};
 for (unsigned int i=0;i<4;i++)vfe.line[i].vfe=&vfe;
 struct vfe_line *line=&vfe.line[3];line->is_pix=true;
 line->fmt[0]=(struct v4l2_mbus_framefmt){.width=4608,.height=3456};
 for (unsigned int pattern=0;pattern<4;pattern++)for(unsigned int depth=0;depth<4;depth++) {
  clear_mmio();line->fmt[0].code=codes[pattern][depth];*(u32 *)(mmio+0x50)=UINT32_MAX;
  assert(vfe_175_camif_prepare(line)==0);
  assert(nreads==1 && nwrites==10);
  assert(*(u32 *)(mmio+0x50)==((UINT32_MAX & ~0x80007fU)|pattern));
  assert(*(u32 *)(mmio+0x478)==4 && *(u32 *)(mmio+0x47c)==0x4000c0);
  assert(*(u32 *)(mmio+0x488)==0xffff && *(u32 *)(mmio+0x48c)==0xffff);
  assert(*(u32 *)(mmio+0x490)==0xf0f && *(u32 *)(mmio+0x49c)==1);
  assert(*(u32 *)(mmio+0xce4)==4607 && *(u32 *)(mmio+0xce8)==3455);
  assert(*(u32 *)(mmio+0x4a0)==0x06bf0014);
  for(unsigned int i=0;i<nwrites;i++)assert(writes[i].address!=0x4ac && writes[i].address<0x2000);
 }
 const u32 invalid[]={0,MEDIA_BUS_FMT_UYVY8_2X8,MEDIA_BUS_FMT_SRGGB16_1X16,MEDIA_BUS_FMT_SBGGR10_2X8_PADHI_LE};
 for(unsigned int i=0;i<ARRAY_SIZE(invalid);i++) {
  clear_mmio();line->fmt[0].code=invalid[i];assert(vfe_175_camif_prepare(line)==-EINVAL);assert(!nwrites&&!nreads);
 }
 line->fmt[0].code=MEDIA_BUS_FMT_SRGGB10_1X10;
 const u32 invalid_size[]={0,0x4001,UINT32_MAX};
 for(unsigned int i=0;i<ARRAY_SIZE(invalid_size);i++)for(unsigned int axis=0;axis<2;axis++) {
  clear_mmio();line->fmt[0].width=4608;line->fmt[0].height=3456;
  if(axis)line->fmt[0].height=invalid_size[i];else line->fmt[0].width=invalid_size[i];
  assert(vfe_175_camif_prepare(line)==-EINVAL);assert(!nwrites&&!nreads);
 }
 for(unsigned int extent=1;extent<=0x4000;extent+=0x3fff) {
  clear_mmio();line->fmt[0].width=line->fmt[0].height=extent;
  assert(vfe_175_camif_prepare(line)==0);
  assert(*(u32 *)(mmio+0xce4)==extent-1 && *(u32 *)(mmio+0xce8)==extent-1);
  assert((*(u32 *)(mmio+0x4a0)&0xffff)<=extent-1);
 }
 clear_mmio();res.is_lite=true;assert(vfe_175_camif_prepare(line)==-EINVAL);assert(!nwrites&&!nreads);
 res.is_lite=false;cr.version=845;assert(vfe_175_camif_prepare(line)==-EINVAL);assert(!nwrites&&!nreads);cr.version=CAMSS_8150;
 line->is_pix=false;line->fmt[0].code=0;assert(vfe_175_camif_prepare(line)==0);assert(!nwrites&&!nreads);
 line->is_pix=true;
 clear_mmio();vfe.reg_update=0;
 vfe_reg_update(&vfe,VFE_LINE_PIX);assert(*(u32 *)(mmio+0x4ac)==1 && barriers==2);
 for(int i=0;i<3;i++){vfe_reg_update(&vfe,i);assert(vfe.reg_update==(BIT(i+2)-1));}
 vfe_reg_update_clear(&vfe,VFE_LINE_PIX);assert(vfe.reg_update==14);
 for(int i=0;i<3;i++)vfe_reg_update_clear(&vfe,i);
 assert(!vfe.reg_update);
 line->is_pix=false;assert(vfe_reg_update_mask(&vfe,VFE_LINE_PIX)==16);line->is_pix=true;
 res.line_num=4;clear_mmio();
 *(u32 *)(mmio+0x6c)=BIT(31)|BIT(0)|BIT(4)|BIT(5)|BIT(6)|BIT(7)|BIT(27)|BIT(28)|BIT(29);
 assert(vfe_isr(0,&vfe)==IRQ_HANDLED && reset_ack==1);
 for(int i=0;i<4;i++)assert(update_ack[i]==1 && sof_ack[i]==1);
 assert(*(u32 *)(mmio+0x58)==1 && *(u32 *)(mmio+0x2068)==1);
 /* A PIX ACK cannot acknowledge Lite RDI3, nor can RDI3's bit8 acknowledge PIX. */
 clear_mmio();*(u32 *)(mmio+0x6c)=BIT(8);vfe_isr(0,&vfe);assert(!update_ack[3]);
 line->is_pix=false;clear_mmio();*(u32 *)(mmio+0x6c)=BIT(4);vfe_isr(0,&vfe);assert(!update_ack[3]);
 clear_mmio();*(u32 *)(mmio+0x6c)=BIT(8)|BIT(30);vfe_isr(0,&vfe);assert(update_ack[3]==1&&sof_ack[3]==1);
 /* Current full resources have only three lines: no fourth callback is delivered. */
 res.line_num=3;clear_mmio();*(u32 *)(mmio+0x6c)=BIT(0)|BIT(4);vfe_isr(0,&vfe);assert(!update_ack[3]&&!sof_ack[3]);
 ops.vfe_line_prepare=prepare_mock;clear_enable();vfe.stream_count=1;
 prepare_result=-EINVAL;assert(vfe_enable(&vfe.line[0])==-EINVAL);
 assert(vfe.stream_count==1 && !vfe.stream_lock && get_calls==1 && put_calls==1 && !output_enables && prepare_calls==1);
 clear_enable();get_result=-EBUSY;vfe.stream_count=0;assert(vfe_enable(&vfe.line[0])==-EBUSY);
 assert(!vfe.stream_count && !put_calls && !prepare_calls && !output_enables && irq_enables==1);
 clear_enable();output_result=-EIO;assert(vfe_enable(&vfe.line[0])==-EIO);
 assert(!vfe.stream_count && put_calls==1 && prepare_calls==1 && output_enables==1);
 clear_enable();assert(vfe_enable(&vfe.line[0])==0);assert(vfe.stream_count==1 && vfe.was_streaming);
 clear_enable();ops.vfe_line_prepare=NULL;assert(vfe_enable(&vfe.line[0])==0);assert(vfe.stream_count==2 && !prepare_calls && !irq_enables);
 /* The common v2 caller must also propagate prepare failures before params/DMA. */
 ops.enable_irq=vfe_enable_irq_common;ops.vfe_line_prepare=prepare_mock;line->is_pix=true;
 clear_enable();vfe.stream_count=1;prepare_result=-EINVAL;
 assert(vfe_enable_v2(line)==-EINVAL && vfe.stream_count==1 && !vfe.stream_lock);
 assert(get_calls==1 && put_calls==1 && prepare_calls==1 && !params_calls && !output_enables);
 clear_enable();get_result=-EBUSY;
 assert(vfe_enable_v2(line)==-EBUSY && vfe.stream_count==1 && !put_calls && !prepare_calls && !params_calls);
 clear_enable();output_result=-EIO;
 assert(vfe_enable_v2(line)==-EIO && vfe.stream_count==1 && put_calls==1 && params_calls==1 && output_enables==1);
 clear_enable();assert(vfe_enable_v2(line)==0 && vfe.stream_count==2 && params_calls==1 && !put_calls);
 clear_enable();line->is_pix=false;ops.vfe_line_prepare=NULL;ops.enable_irq=NULL;
 assert(vfe_enable_v2(line)==0 && vfe.stream_count==3 && !params_calls && !prepare_calls && !irq_enables);
 puts("PASS: 16 Bayer formats, OEM CAMIF, input bounds, no-MMIO rejection, PIX/RDI IRQ+RUP, 17x+common prepare rollback");
 return 0;
}
'''
harness = prefix + media_defines + '\n' + functions + tests
source = PRIVATE / 'vfe175-camif-host-private.c'
binary = PRIVATE / 'vfe175-camif-host-private'
source.write_text(harness)
compile_result = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
    '-Wno-unused-parameter', '-Wno-sign-compare', '-Wno-unused-function',
    '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-g', str(source), '-o', str(binary)], capture_output=True, text=True)
assert compile_result.returncode == 0, compile_result.stderr
result = subprocess.run([str(binary)], capture_output=True, text=True)
record = dict(stage=281, production_functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),
    harness_sha256=hashlib.sha256(harness.encode()).hexdigest(), oem_register_oracles=len(mapping),
    oem_control_field_oracles=6, exit=result.returncode, stdout=result.stdout, stderr=result.stderr,
    mock_mmio_only=True, no_hardware_camif_or_image_processing_test=True)
(ROOT / 'camif-host-tests-validation.json').write_text(json.dumps(record, indent=2) + '\n')
assert result.returncode == 0 and not result.stderr, record
print(json.dumps(record, indent=2))
