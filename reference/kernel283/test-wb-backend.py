"""Test actual VFE175 WB and the existing common parser with exact buffers."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel283')
STAGE = PRIVATE / 'wb-candidate'
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
source = (STAGE / 'camss-vfe-175-pixel.c').read_text()
header = (STAGE / 'camss-vfe-175-pixel.h').read_text()
parser_path = TREE / 'drivers/media/v4l2-core/v4l2-isp.c'
parser = parser_path.read_text().split('int v4l2_isp_params_validate_buffer_size(')[1]
parser = 'int v4l2_isp_params_validate_buffer_size(' + parser.split('EXPORT_SYMBOL_GPL(v4l2_isp_params_validate_buffer);')[0]
parser = re.sub(r'EXPORT_SYMBOL_GPL\([^;]+;', '', parser)
state = re.search(r'struct vfe_175_pixel_state \{.*?\};', header, re.S)[0]
body = '\n'.join(l for l in source.splitlines() if not l.startswith('#include'))
common = (STAGE/'camss-vfe.c').read_text()
def function(name):
    match = re.search(r'(?:static )?(?:struct camss_buffer \*|struct vfe_output \*|void )'+name+r'\(', common)
    assert match, name
    end = common.index('\n}', match.start())+2
    return common[match.start():end]
queue_helpers = '\n'.join(function(name) for name in ['vfe_params_output','vfe_params_apply_next','vfe_params_apply_queued'])
enable = (STAGE/'camss-vfe-17x.c').read_text().split('static int vfe_enable(struct vfe_line *line)')[1].split('\n}')[0]
assert enable.index('vfe_line_prepare(line)') < enable.index('vfe_params_apply_queued(vfe, line)') < enable.index('vfe_enable_output_v2(line)')
prelude = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <errno.h>
#define __counted_by(x)
#include <linux/qcom-camss-config.h>
_Static_assert(CAMSS_PARAMS_IFE_MAX_PAYLOAD >= sizeof(struct camss_params_wb_gain) + sizeof(struct v4l2_isp_block_header), "IFE metadata capacity must cover WB plus a short DISABLE");
typedef uint32_t u32;
typedef uint16_t u16;
#define GENMASK(h,l) ((UINT32_MAX >> (31-(h))) & (UINT32_MAX << (l)))
#define FIELD_PREP(mask,val) (((u32)(val) << __builtin_ctz(mask)) & (mask))
#define min_t(type,a,b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define dev_dbg(...) ((void)0)
struct device { int unused; };
struct vb2_buffer { size_t payload; uint64_t timestamp; bool done; };
static size_t vb2_get_plane_payload(struct vb2_buffer *vb, unsigned int i)
{ assert(i == 0); return vb->payload; }
struct v4l2_isp_params_block_type_info {
 size_t size;
 int (*block_validate)(struct device *, const struct v4l2_isp_block_header *);
};
'''
mocks = r'''
struct vfe_device;
struct camss_buffer { struct v4l2_isp_buffer *meta; struct { struct vb2_buffer vb2_buf; u32 sequence; } vb; };
struct vfe_output { unsigned int pad; struct camss_buffer *pending[4]; unsigned int next,count; };
struct vfe_line { bool is_pix; struct vfe_device *owner; unsigned int num_outputs; struct vfe_output output[2]; };
struct vfe_hw_ops { void (*vfe_params_apply)(struct vfe_device *, struct vfe_line *, const struct v4l2_isp_buffer *); };
struct resources { const struct vfe_hw_ops *hw_ops; };
struct vfe_device { unsigned char *base; struct vfe_175_pixel_state pixel175; const struct resources *res; unsigned int output_lock; };
#define to_vfe(line) ((line)->owner)
#define MSM_VFE_PAD_SINK_PARAMS 5
#define VB2_BUF_STATE_DONE 0
static unsigned int locked,completed;
#define spin_lock_irqsave(lock,flags) do { (void)(lock);(flags)=0; assert(!locked);locked=1; } while(0)
#define spin_unlock_irqrestore(lock,flags) do { (void)(lock);(void)(flags);assert(locked);locked=0; } while(0)
static struct camss_buffer *vfe_buf_get_pending(struct vfe_output *o)
{ assert(locked);return o->next<o->count ? o->pending[o->next++] : NULL; }
static uint64_t ktime_get_ns(void) { static uint64_t tick;return ++tick; }
static void vb2_buffer_done(struct vb2_buffer *b, int state)
{ assert(!locked && !b->done && state==VB2_BUF_STATE_DONE);b->done=true;completed++; }
static unsigned char bank[0x1000];
static unsigned int writes;
static u32 readl_relaxed(const void *p)
{ u32 v; assert((const unsigned char *)p >= bank && (const unsigned char *)p <= bank+sizeof(bank)-4); memcpy(&v,p,4); return v; }
static void writel_relaxed(u32 v, void *p)
{ assert((unsigned char *)p >= bank && (unsigned char *)p <= bank+sizeof(bank)-4); memcpy(p,&v,4); writes++; }
'''
tests = r'''
static int submit(struct vfe_device *v, struct vfe_line *line,
                  const void *block, size_t size, bool apply)
{
 size_t n = sizeof(struct v4l2_isp_buffer)+size;
 struct v4l2_isp_buffer *p = malloc(n);
 struct vb2_buffer vb = { .payload=n };
 assert(p); p->version=1; p->data_size=size;
 memcpy(p->data,block,size);
 int ret = v4l2_isp_params_validate_buffer_size(NULL,&vb,sizeof(*p)+CAMSS_PARAMS_IFE_MAX_PAYLOAD);
 if (!ret) ret = v4l2_isp_params_validate_buffer(NULL,&vb,p,vfe_175_params_info,2);
 if (!ret && apply) vfe_175_params_apply(v,line,p);
 free(p); return ret;
}
static u32 get(unsigned int address) { return readl_relaxed(bank+address); }
static void expect(unsigned int g,unsigned int b,unsigned int r)
{
 assert((get(0x6fc)&0x0fff0fff)==(g|(b<<16)));
 assert((get(0x700)&0x00000fff)==r);
 assert((get(0x704)&0x7fff7fff)==0);
 assert((get(0x708)&0x00007fff)==0);
}
int main(void)
{
 struct vfe_device v={.base=bank};
 struct vfe_line pix={.is_pix=true,.owner=&v},rdi={.is_pix=false,.owner=&v};
 struct camss_params_wb_gain w={.header={CAMSS_PARAMS_WB_GAIN,0,sizeof(w)},
                              .g_gain=1024,.b_gain=2048,.r_gain=3072};
 memset(bank,0xa5,sizeof(bank));
 vfe_175_pixel_prepare(&rdi); assert(writes==0);
 vfe_175_pixel_prepare(&pix); assert(writes==4); expect(128,128,128);
 assert(submit(&v,&pix,&w,sizeof(w),true)==0); expect(128,256,384);
 assert((get(0x6fc)&0xf000f000)==0xa000a000);
 assert((get(0x700)&0xfffff000)==0xa5a5a000);
 assert((get(0x704)&0x80008000)==0x80008000);
 assert((get(0x708)&0xffff8000)==0xa5a58000);
 /* Exhaustively compare all input gains against independent integer rounding. */
 for (unsigned int g=0;g<=32767;g++) {
  w.g_gain=g; w.b_gain=32767-g; w.r_gain=(g*97)%32768;
  assert(submit(&v,&pix,&w,sizeof(w),true)==0);
  unsigned int eg=(w.g_gain+4)/8,eb=(w.b_gain+4)/8,er=(w.r_gain+4)/8;
  expect(eg>4095?4095:eg,eb>4095?4095:eb,er>4095?4095:er);
 }
 struct v4l2_isp_block_header disable={CAMSS_PARAMS_WB_GAIN,V4L2_ISP_PARAMS_FL_BLOCK_DISABLE,sizeof(disable)};
 assert(submit(&v,&pix,&disable,sizeof(disable),true)==0); expect(128,128,128);
 assert(!v.pixel175.wb_enabled);
 w.g_gain=1024;w.b_gain=2048;w.r_gain=3072;
 assert(submit(&v,&pix,&w,sizeof(w),true)==0); expect(128,128,128);
 assert(!v.pixel175.wb_enabled && v.pixel175.r_gain==3072);
 w.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;
 assert(submit(&v,&pix,&w,sizeof(w),true)==0); expect(128,256,384);
 assert(v.pixel175.wb_enabled);
 unsigned int before=writes;
 assert(submit(&v,&rdi,&w,sizeof(w),true)==0); assert(before==writes);
 /* Invalid inputs pass through the actual common parser and never reach MMIO. */
 for (unsigned int channel=0;channel<3;channel++) {
  u16 *gain[]={&w.g_gain,&w.b_gain,&w.r_gain};
  for (unsigned int g=32768;g<=65535;g++) {
   *gain[channel]=g; assert(submit(&v,&pix,&w,sizeof(w),true)==-EINVAL);
  }
  *gain[channel]=1024;
 }
 w.g_gain=1024;
 u16 *unsupported[]={&w.g_sub,&w.b_sub,&w.r_sub,&w.g_add,&w.b_add,&w.r_add,
                    &w._pad[0],&w._pad[1],&w._pad[2]};
 for (unsigned int i=0;i<sizeof(unsupported)/sizeof(unsupported[0]);i++) {
  *unsupported[i]=1; assert(submit(&v,&pix,&w,sizeof(w),true)==-EINVAL); *unsupported[i]=0;
 }
 w.header.flags=3; assert(submit(&v,&pix,&w,sizeof(w),true)==-EINVAL);
 w.header.flags=4; assert(submit(&v,&pix,&w,sizeof(w),true)==-EINVAL);
 w.header.flags=0;
 for (unsigned int type=0;type<=6;type++) if (type!=1) {
  w.header.type=type; assert(submit(&v,&pix,&w,sizeof(w),true)==-EINVAL);
 }
 w.header.type=1;
 for (unsigned int n=0;n<sizeof(w);n++) {
  w.header.size=n; assert(submit(&v,&pix,&w,n,true)==(n==0?0:-EINVAL));
 }
 w.header.size=sizeof(w); assert(writes==before);
 /* Mixed header-only/full blocks preserve FIFO order and exact allocations. */
 unsigned char blocks[sizeof(disable)+sizeof(w)];
 memcpy(blocks,&disable,sizeof(disable));memcpy(blocks+sizeof(disable),&w,sizeof(w));
 assert(submit(&v,&pix,blocks,sizeof(blocks),true)==0);expect(128,128,128);
 assert(!v.pixel175.wb_enabled);
 vfe_175_pixel_prepare(&pix);expect(128,128,128);assert(v.pixel175.wb_enabled);
 /* The real common FIFO helpers apply initial params and release before DONE. */
 const struct vfe_hw_ops ops={.vfe_params_apply=vfe_175_params_apply};
 const struct resources resources={.hw_ops=&ops};v.res=&resources;
 pix.num_outputs=2;pix.output[1].pad=MSM_VFE_PAD_SINK_PARAMS;
 struct camss_buffer pending[2]={0};
 w.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;
 for (unsigned int i=0;i<2;i++) {
  size_t size=i?sizeof(disable):sizeof(w);
  pending[i].meta=malloc(sizeof(struct v4l2_isp_buffer)+size);assert(pending[i].meta);
  pending[i].meta->version=1;pending[i].meta->data_size=size;
  memcpy(pending[i].meta->data,i?(const void *)&disable:(const void *)&w,size);
  pix.output[1].pending[i]=&pending[i];
 }
 pix.output[1].count=2;
 vfe_params_apply_queued(&v,&pix);expect(128,128,128);
 assert(completed==2 && !locked && !v.pixel175.wb_enabled);
 assert(pending[0].vb.sequence==0 && pending[1].vb.sequence==0);
 assert(pending[0].vb.vb2_buf.timestamp<pending[1].vb.vb2_buf.timestamp);
 before=writes;vfe_params_apply_queued(&v,&pix);assert(before==writes && completed==2);
 for (unsigned int i=0;i<2;i++) free(pending[i].meta);
 puts("PASS: exhaustive Q10/Q7, channel mapping, masks, parser bounds, bypass state, FIFO and RDI isolation");
}
'''
harness = prelude + state + mocks + body + queue_helpers + parser + tests
path = PRIVATE / 'wb-host-tests-private.c'
path.write_text(harness)
command = ['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-D__EXPORTED_HEADERS__',
           '-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',
           '-I'+str(PRIVATE/'wb-uapi'),'-I'+str(TREE/'include/uapi'),str(path),'-o',str(PRIVATE/'wb-host-tests-private')]
subprocess.run(command,check=True)
result = subprocess.run([str(PRIVATE/'wb-host-tests-private')],text=True,capture_output=True)
(PRIVATE/'wb-host-tests-private.log').write_text(result.stdout+result.stderr)
assert result.returncode == 0, result.stdout+result.stderr
report = dict(stage=283,exit=0,asan_ubsan=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
              parser_sha256=hashlib.sha256(parser_path.read_bytes()).hexdigest(),
              harness_sha256=hashlib.sha256(harness.encode()).hexdigest(),
              exhaustive_valid_gains=32768,exhaustive_out_of_range_gains_per_channel=32768,
              metadata_capacity_checks=True,
              actual_initial_queue_helpers_tested=True,done_after_unlock=True,
              output=result.stdout.strip(),hardware_mmio_simulated=True,not_deployed=True)
(ROOT/'wb-host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
