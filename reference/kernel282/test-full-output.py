"""Test actual VFE175 transport, capture preparation and group buffer completion."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import host

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
D=TREE/'drivers/media/platform/qcom/camss'
output=(D/'camss-vfe-175-output.c').read_text()
shared=(D/'camss-vfe.c').read_text()
irq=(D/'camss-vfe-17x.c').read_text()
video=(D/'camss-video.c').read_text()
pin=json.loads((ROOT.parent/'kernel281/oem-programming-sources.json').read_text())['sources']
row=next(v for k,v in pin.items() if k.endswith('/cam_vfe175.h'))
data=(Path('/mnt/e/edk2-samurai-out/kernel281')/row['local_name']).read_bytes()
assert hashlib.sha256(data).hexdigest()==row['sha256']
oem=data.decode()
fields={'CFG':'cfg','IMAGE_ADDR':'image_addr','IMAGE_OFFSET':'image_addr_offset',
        'WIDTH':'buffer_width_cfg','HEIGHT':'buffer_height_cfg','PACKER':'packer_cfg',
        'STRIDE':'stride','IRQ_PERIOD':'irq_subsample_period','IRQ_PATTERN':'irq_subsample_pattern',
        'DROP_PERIOD':'framedrop_period','DROP_PATTERN':'framedrop_pattern','FRAME_INC':'frame_inc',
        'BURST_LIMIT':'burst_limit'}
checks=[]
for client in [3,4]:
    block=oem[oem.index('/* BUS Client %d */'%client):oem.index('/* BUS Client %d */'%(client+1))]
    for suffix,field in fields.items():
        macro=re.search(r'#define VFE_175_WM_'+suffix+r'\(n\)\s+\((0x[0-9a-f]+) \+ \(n\) \* (0x[0-9a-f]+)\)',output)
        assert macro,suffix
        actual=int(macro[1],16)+client*int(macro[2],16)
        expected=int(re.search(r'\.'+field+r'\s*=\s*(0x[0-9a-fA-F]+)',block)[1],16)
        assert actual==expected,(client,field)
        checks.append([client,field,actual])
full=oem[oem.index('.vfe_out_type  = CAM_VFE_BUS_VER2_VFE_OUT_FULL,'):]
assert int(re.search(r'\.max_width\s*=\s*(\d+)',full)[1])==4096
assert int(re.search(r'\.max_height\s*=\s*(\d+)',full)[1])==4096
bus=(Path('/mnt/e/edk2-samurai-out/kernel281')/'oem-cam_vfe_bus_ver2.c').read_text()
assert re.search(r'PACKER_FMT_PLAIN_8_LSB_MSB_10\s*=\s*0xE',bus)
assert '.comp_mask                    = 0x00002010' in oem


def function(source,signature):
    start=source.index(signature)
    return source[start:source.index('\n}\n',start)+3]


defines=irq[irq.index('#define VFE_GLOBAL_RESET_CMD'):irq.index('static inline void vfe_reg_set')]
functions=re.sub(r'^#include.*\n','',output,flags=re.M)+defines
functions+=''.join(function(irq,s) for s in ['static u32 vfe_reg_update_mask(',
    'static void vfe_reg_update(','static irqreturn_t vfe_isr(','static int vfe_prepare_dma_175(',
    'static void vfe_wm_start(', 'static void vfe_wm_stop(', 'static void vfe_wm_update(',
    'static void vfe_output_start_175(', 'static void vfe_output_stop_175(', 'static void vfe_output_update_175('])
functions+=''.join(function(shared,s) for s in ['static struct camss_buffer *vfe_output_done(',
    'void vfe_buf_done('])
functions+=function(video,'static int video_buf_prepare(')
functions+=function(shared,'static bool vfe_pix_line_based(')
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;typedef uint32_t u32;typedef uint64_t u64;typedef uint64_t dma_addr_t;typedef int irqreturn_t;
#define BIT(n) (1u<<(n))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define IS_ALIGNED(a,n) (!((a)&((n)-1)))
#define U16_MAX UINT16_MAX
#define U32_MAX UINT32_MAX
#define IRQ_HANDLED 1
#define MSM_VFE_PAD_SRC 1
#define MSM_VFE_PAD_SRC_STATS 4
#define MSM_VFE_NUM_OUTPUTS 5
#define V4L2_PIX_FMT_NV12 0x3231564e
#define V4L2_PIX_FMT_NV21 0x3132564e
#define V4L2_FIELD_NONE 1
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define VB2_BUF_STATE_ACTIVE 1
#define VB2_BUF_STATE_DONE 2
enum vfe_line_id {VFE_LINE_NONE=-1,VFE_LINE_RDI0=0,VFE_LINE_RDI1,VFE_LINE_RDI2,VFE_LINE_PIX};
enum vfe_output_state {VFE_OUTPUT_OFF=0,VFE_OUTPUT_ON=6};
struct vfe_device;struct vfe_line;struct camss_buffer;struct camss_video;struct vfe_output;
struct plane_format {u32 bytesperline,sizeimage;};
struct v4l2_pix_format_mplane {u32 pixelformat,width,height,num_planes;struct plane_format plane_fmt[3];};
struct format {struct {struct v4l2_pix_format_mplane pix_mp;}fmt;};
struct vb2_buffer {u64 timestamp;unsigned int state,done_count;size_t allocated[3],payload[3];void*vb2_queue;};
struct vb2_v4l2_buffer {struct vb2_buffer vb2_buf;unsigned int sequence,field;};
struct camss_buffer {struct vb2_v4l2_buffer vb;dma_addr_t addr[3];};
struct camss_video_ops {int(*prepare_dma_buffer)(struct camss_video*,struct camss_buffer*);};
struct camss_video {struct format active_fmt;const struct camss_video_ops *ops;};
struct vfe_wm {u8 bus_client,plane;};
struct vfe_output {u8 pad,comp_group,wm_num;struct vfe_wm wm[3];struct camss_buffer *buf[2];
 unsigned int sequence;enum vfe_output_state state;struct {int active_num;}gen2;
 struct vfe_line *line;struct camss_video video_out;struct camss_buffer *pending[8];unsigned int pending_count,pending_index;};
struct vfe_line {int id;bool is_pix;unsigned int num_outputs;struct vfe_output output[5];struct vfe_device *vfe;};
#define to_vfe(l) ((l)->vfe)
struct camss_buf_done_info {int hw_id,port_id;u32 status;};
struct vfe_hw_ops {void(*vfe_output_update)(struct vfe_device*,struct vfe_output*,struct camss_buffer*);
 void(*vfe_wm_update)(struct vfe_device*,u8,u32,struct vfe_line*);void(*reg_update)(struct vfe_device*,enum vfe_line_id);};
struct resources {unsigned int line_num;const struct vfe_hw_ops *hw_ops;};
struct isr_ops {void(*reset_ack)(struct vfe_device*);void(*reg_update)(struct vfe_device*,int);
 void(*sof)(struct vfe_device*,int);void(*comp_done)(struct vfe_device*,u8);void(*wm_done)(struct vfe_device*,u8);};
#define CAMSS_8150 8150
#define CAMSS_8650 8650
struct camss_resources {unsigned int version;};
struct camss {void *dev;struct camss_resources *res;};
struct vfe_device {unsigned char*base;struct resources*res;struct camss*camss;struct vfe_line line[4];
 int wm_output_map[7];u32 reg_update;pthread_mutex_t output_lock;struct isr_ops isr_ops;};
void vfe_buf_done(struct vfe_device*,int,struct camss_buf_done_info*);
void vfe_175_full_update(struct vfe_device*,struct vfe_output*,const struct camss_buffer*);
static void vfe_reg_update(struct vfe_device*,enum vfe_line_id);
static unsigned char mmio[0x4000];
static struct {u32 address,value;} writes[4096];static unsigned int nwrites,nreads,barriers;
static unsigned int errors,update_calls,params_calls,dma_prepare_calls,init_calls,wm_irq[24],stats_calls;
static int init_result;
static u64 clock_ns;
static u32 rd(const void*addr){size_t n=(const unsigned char*)addr-mmio;assert(n<sizeof(mmio)&&!(n&3));nreads++;return *(u32*)(mmio+n);}
static void wr(u32 v,void*addr){size_t n=(unsigned char*)addr-mmio;assert(n<sizeof(mmio)&&!(n&3)&&nwrites<ARRAY_SIZE(writes));writes[nwrites].address=n;writes[nwrites++].value=v;*(u32*)(mmio+n)=v;}
#define readl_relaxed rd
#define writel_relaxed wr
#define wmb() do{barriers++;}while(0)
#define spin_lock_irqsave(m,f) do{(f)=0;assert(!pthread_mutex_lock(m));}while(0)
#define spin_unlock_irqrestore(m,f) do{(void)(f);assert(!pthread_mutex_unlock(m));}while(0)
#define dev_err_ratelimited(dev,...) do{(void)(dev);errors++;}while(0)
static struct camss_buffer*vfe_buf_get_pending(struct vfe_output*o){return o->pending_index<o->pending_count?o->pending[o->pending_index++]:NULL;}
static void vfe_stats_fill(struct vfe_device*v,struct vfe_output*o,struct camss_buffer*b){(void)v;(void)o;(void)b;stats_calls++;}
static struct camss_buffer*vfe_params_apply_next(struct vfe_device*v,struct vfe_line*l,unsigned int n){(void)v;(void)l;(void)n;params_calls++;return NULL;}
static u64 ktime_get_ns(void){return ++clock_ns;}
static void vb2_buffer_done(struct vb2_buffer*b,int state){assert(b->state==VB2_BUF_STATE_ACTIVE);assert(++b->done_count==1);b->state=state;}
static void update_cb(struct vfe_device*v,struct vfe_output*o,struct camss_buffer*b){update_calls++;vfe_175_full_update(v,o,b);}
static void rdi_update(struct vfe_device*v,u8 wm,u32 addr,struct vfe_line*l){(void)v;(void)wm;(void)addr;(void)l;assert(!"PIX used legacy RDI updater");}
static void reset_cb(struct vfe_device*v){(void)v;}
static void ack_cb(struct vfe_device*v,int n){(void)v;assert(n>=0&&n<4);}
static void wm_cb(struct vfe_device*v,u8 n){(void)v;assert(n<24);wm_irq[n]++;}
static struct vb2_v4l2_buffer*to_vb2_v4l2_buffer(struct vb2_buffer*b){return container_of(b,struct vb2_v4l2_buffer,vb2_buf);}
static void*vb2_get_drv_priv(void*queue){return queue;}
static int video_buf_init(struct vb2_buffer*b){(void)b;init_calls++;return init_result;}
static size_t vb2_plane_size(struct vb2_buffer*b,unsigned int p){assert(p<3);return b->allocated[p];}
static void vb2_set_plane_payload(struct vb2_buffer*b,unsigned int p,size_t n){assert(p<3);b->payload[p]=n;}
'''
tests=r'''
static int capture_validate(struct camss_video*v,struct camss_buffer*b){dma_prepare_calls++;return vfe_prepare_dma_175(v,b);}
static void clear_io(void){memset(mmio,0,sizeof(mmio));nwrites=nreads=barriers=0;}
static void invalid_output(struct vfe_output*o){clear_io();assert(vfe_175_validate_output(o)==-EINVAL);assert(!nwrites&&!nreads);}
int main(void){
 struct vfe_hw_ops ops={update_cb,rdi_update,vfe_reg_update};struct resources res={4,&ops};struct camss camss={0};
 struct vfe_device vfe={.base=mmio,.res=&res,.camss=&camss};assert(!pthread_mutex_init(&vfe.output_lock,NULL));
 for(unsigned int i=0;i<4;i++){vfe.line[i].id=i;vfe.line[i].vfe=&vfe;vfe.line[i].num_outputs=1;}
 for(unsigned int i=0;i<7;i++)vfe.wm_output_map[i]=VFE_LINE_NONE;
 vfe.isr_ops=(struct isr_ops){reset_cb,ack_cb,ack_cb,vfe_175_comp_done,wm_cb};
 struct vfe_line*line=&vfe.line[3];line->is_pix=true;
 struct vfe_output*o=&line->output[0];o->line=line;o->pad=1;o->wm_num=2;o->comp_group=0;
 o->wm[0]=(struct vfe_wm){3,0};o->wm[1]=(struct vfe_wm){4,1};
 struct v4l2_pix_format_mplane*pix=&o->video_out.active_fmt.fmt.pix_mp;
 *pix=(struct v4l2_pix_format_mplane){.pixelformat=V4L2_PIX_FMT_NV12,.width=2048,.height=1536,.num_planes=1,
  .plane_fmt={{2048,2048*1536*3/2}}};
 const struct v4l2_pix_format_mplane saved=*pix;
 assert(!vfe_175_validate_output(o));
 const u32 bad_sizes[]={0,1,4097,UINT32_MAX};
 for(unsigned int i=0;i<ARRAY_SIZE(bad_sizes);i++){
  pix->width=bad_sizes[i];invalid_output(o);*pix=saved;
  pix->height=bad_sizes[i];invalid_output(o);*pix=saved;
 }
 const u32 bad_stride[]={0,1024,2049,65536,UINT32_MAX};
 for(unsigned int i=0;i<ARRAY_SIZE(bad_stride);i++){pix->plane_fmt[0].bytesperline=bad_stride[i];invalid_output(o);*pix=saved;}
 pix->pixelformat=V4L2_PIX_FMT_NV21;invalid_output(o);*pix=saved;
 pix->num_planes=2;invalid_output(o);*pix=saved;
 pix->plane_fmt[0].sizeimage--;invalid_output(o);*pix=saved;
 o->wm[1].bus_client=3;invalid_output(o);o->wm[1].bus_client=4;
 o->wm[1].plane=0;invalid_output(o);o->wm[1].plane=1;
 o->comp_group=1;invalid_output(o);o->comp_group=0;
 o->wm_num=1;invalid_output(o);o->wm_num=2;
 o->pad=4;invalid_output(o);o->pad=1;
 line->num_outputs=2;invalid_output(o);line->num_outputs=1;
 line->is_pix=false;invalid_output(o);line->is_pix=true;
 pix->width=pix->height=4096;pix->plane_fmt[0].bytesperline=4096;pix->plane_fmt[0].sizeimage=4096*4096*3/2;
 assert(!vfe_175_validate_output(o));*pix=saved;
 struct camss_buffer buffers[4]={0};u64 luma=(u64)2048*1536,size=luma*3/2;
 for(unsigned int i=0;i<4;i++){
  buffers[i].addr[0]=0x1000000+i*0x1000000;buffers[i].addr[1]=buffers[i].addr[0]+luma;
  buffers[i].vb.vb2_buf.state=VB2_BUF_STATE_ACTIVE;buffers[i].vb.vb2_buf.allocated[0]=size;
  buffers[i].vb.vb2_buf.vb2_queue=&o->video_out;
  assert(!vfe_175_validate_buffer(o,&buffers[i]));
 }
 struct camss_buffer boundary=buffers[0];boundary.addr[0]=(u64)UINT32_MAX-size+1;boundary.addr[1]=boundary.addr[0]+luma;
 assert(!vfe_175_validate_buffer(o,&boundary));boundary.addr[0]+=16;boundary.addr[1]+=16;
 assert(vfe_175_validate_buffer(o,&boundary)==-ERANGE);
 boundary.addr[0]=(u64)UINT32_MAX+1;boundary.addr[1]=boundary.addr[0]+luma;assert(vfe_175_validate_buffer(o,&boundary)==-ERANGE);
 boundary=buffers[0];boundary.addr[0]++;boundary.addr[1]++;assert(vfe_175_validate_buffer(o,&boundary)==-EINVAL);
 boundary=buffers[0];boundary.addr[1]+=16;assert(vfe_175_validate_buffer(o,&boundary)==-EINVAL);
 assert(!nwrites&&!nreads);
 struct camss_video_ops vidops={capture_validate};o->video_out.ops=&vidops;
 buffers[0].vb.field=99;assert(!video_buf_prepare(&buffers[0].vb.vb2_buf));
 assert(init_calls==1&&dma_prepare_calls==1&&buffers[0].vb.field==V4L2_FIELD_NONE);
 assert(buffers[0].vb.vb2_buf.payload[0]==size);
 init_result=-EIO;assert(video_buf_prepare(&buffers[0].vb.vb2_buf)==-EIO&&dma_prepare_calls==1);init_result=0;
 buffers[0].vb.vb2_buf.allocated[0]=size-1;assert(video_buf_prepare(&buffers[0].vb.vb2_buf)==-EINVAL&&dma_prepare_calls==1);
 buffers[0].vb.vb2_buf.allocated[0]=size;buffers[0].addr[1]+=16;
 assert(video_buf_prepare(&buffers[0].vb.vb2_buf)==-EINVAL&&dma_prepare_calls==2);buffers[0].addr[1]-=16;
 clear_io();*(u32*)(mmio+0x200c)=BIT(20);*(u32*)(mmio+0x2084)=BIT(2);*(u32*)(mmio+0x2010)=BIT(13);
 *(u32*)(mmio+0x2544)=0xa5;*(u32*)(mmio+0x2644)=0x5b;*(u32*)(mmio+0x2408)=3;
 vfe_175_full_start(&vfe,o);
 assert(*(u32*)(mmio+0x200c)==(BIT(20)|BIT(3)|BIT(4)));
 assert(*(u32*)(mmio+0x2084)==(BIT(2)|BIT(3)|BIT(4))&&*(u32*)(mmio+0x2010)==(BIT(13)|BIT(3)|BIT(4)));
 for(unsigned int i=0;i<2;i++){
  u32 base=0x2500+i*0x100;
  assert(*(u32*)(mmio+base+0x08)==1&&*(u32*)(mmio+base+0x1c)==2048);
  assert(*(u32*)(mmio+base+0x20)==(1536u>>i)&&*(u32*)(mmio+base+0x24)==14);
  assert(*(u32*)(mmio+base+0x28)==2048&&*(u32*)(mmio+base+0x58)==(2048u*(1536u>>i)));
  assert(*(u32*)(mmio+base+0x48)==0&&*(u32*)(mmio+base+0x4c)==1);
  assert(*(u32*)(mmio+base+0x50)==0&&*(u32*)(mmio+base+0x54)==1&&*(u32*)(mmio+base+0x5c)==15);
 }
 assert(*(u32*)(mmio+0x2544)==0xa4&&*(u32*)(mmio+0x2644)==0x5a);
 for(unsigned int i=0;i<nwrites;i++)assert(writes[i].address!=0x2514&&writes[i].address!=0x2614&&writes[i].address!=0x4ac);
 vfe_175_full_update(&vfe,o,&buffers[0]);assert(*(u32*)(mmio+0x2514)==buffers[0].addr[0]&&*(u32*)(mmio+0x2614)==buffers[0].addr[1]);
 vfe_175_full_stop(&vfe,o);assert(!*(u32*)(mmio+0x2508)&&!*(u32*)(mmio+0x2608));
 assert(*(u32*)(mmio+0x2010)==BIT(13)&&*(u32*)(mmio+0x2408)==3);
 clear_io();o->state=VFE_OUTPUT_ON;o->buf[0]=&buffers[0];o->buf[1]=&buffers[1];o->gen2.active_num=2;
 o->pending[0]=&buffers[2];o->pending_count=1;vfe.wm_output_map[3]=3;
 *(u32*)(mmio+0x205c)=BIT(5);*(u32*)(mmio+0x2060)=BIT(3)|BIT(4);
 assert(vfe_isr(0,&vfe)==IRQ_HANDLED);
 assert(buffers[0].vb.vb2_buf.done_count==1&&buffers[1].vb.vb2_buf.done_count==0);
 assert(!wm_irq[3]&&!wm_irq[4]&&update_calls==1&&params_calls==1&&o->buf[0]==&buffers[1]&&o->buf[1]==&buffers[2]);
 assert(*(u32*)(mmio+0x2514)==buffers[2].addr[0]&&*(u32*)(mmio+0x2614)==buffers[2].addr[1]&&*(u32*)(mmio+0x4ac)==1);
 *(u32*)(mmio+0x205c)=0;vfe_isr(0,&vfe);assert(!buffers[1].vb.vb2_buf.done_count&&params_calls==1);
 *(u32*)(mmio+0x205c)=BIT(5);*(u32*)(mmio+0x2060)=BIT(0)|BIT(3)|BIT(4);vfe_isr(0,&vfe);
 assert(buffers[1].vb.vb2_buf.done_count==1&&wm_irq[0]==1&&o->gen2.active_num==1);
 vfe_isr(0,&vfe);assert(buffers[2].vb.vb2_buf.done_count==1&&!o->gen2.active_num&&params_calls==3);
 unsigned int old_errors=errors;vfe_isr(0,&vfe);assert(errors==old_errors+1&&params_calls==3);
 assert(buffers[0].vb.vb2_buf.timestamp<buffers[1].vb.vb2_buf.timestamp&&buffers[1].vb.vb2_buf.timestamp<buffers[2].vb.vb2_buf.timestamp);
 *(u32*)(mmio+0x205c)=BIT(10);*(u32*)(mmio+0x2060)=0;vfe_isr(0,&vfe);assert(params_calls==3);
 vfe_175_comp_done(&vfe,6);vfe_175_comp_done(&vfe,255);assert(params_calls==3);
 res.line_num=3;vfe_175_comp_done(&vfe,0);assert(params_calls==3);
 res.line_num=4;line->is_pix=false;*(u32*)(mmio+0x205c)=0;*(u32*)(mmio+0x2060)=BIT(3);vfe_isr(0,&vfe);assert(wm_irq[3]==1);
 line->is_pix=true;o->state=VFE_OUTPUT_OFF;*(u32*)(mmio+0x205c)=BIT(5);*(u32*)(mmio+0x2060)=BIT(3)|BIT(4);
 vfe_isr(0,&vfe);assert(params_calls==3&&wm_irq[3]==1&&!wm_irq[4]);
 assert(!stats_calls);assert(!pthread_mutex_destroy(&vfe.output_lock));
 /* New output callbacks must preserve the exact RDI register write sequence. */
 struct vfe_output*rdi=&vfe.line[2].output[0];rdi->line=&vfe.line[2];rdi->wm_num=1;rdi->wm[0].bus_client=2;
 rdi->video_out.active_fmt.fmt.pix_mp.height=1080;rdi->video_out.active_fmt.fmt.pix_mp.plane_fmt[0].bytesperline=2400;
 unsigned char expected_mmio[sizeof(mmio)];typeof(writes) expected_writes;unsigned int expected_count;
 clear_io();vfe_wm_start(&vfe,2,rdi->line);memcpy(expected_mmio,mmio,sizeof(mmio));
 memcpy(expected_writes,writes,sizeof(writes));expected_count=nwrites;
 clear_io();vfe_output_start_175(&vfe,rdi);
 assert(nwrites==expected_count&&!memcmp(expected_mmio,mmio,sizeof(mmio))&&!memcmp(expected_writes,writes,nwrites*sizeof(writes[0])));
 clear_io();vfe_wm_update(&vfe,2,buffers[0].addr[0],rdi->line);memcpy(expected_mmio,mmio,sizeof(mmio));
 memcpy(expected_writes,writes,sizeof(writes));expected_count=nwrites;
 clear_io();vfe_output_update_175(&vfe,rdi,&buffers[0]);
 assert(nwrites==expected_count&&!memcmp(expected_mmio,mmio,sizeof(mmio))&&!memcmp(expected_writes,writes,nwrites*sizeof(writes[0])));
 clear_io();vfe_wm_stop(&vfe,2,rdi->line);memcpy(expected_mmio,mmio,sizeof(mmio));expected_count=nwrites;
 clear_io();vfe_output_stop_175(&vfe,rdi);assert(nwrites==expected_count&&!memcmp(expected_mmio,mmio,sizeof(mmio)));
 clear_io();assert(!vfe_prepare_dma_175(&rdi->video_out,&boundary)&&!nwrites&&!nreads);
 struct camss_resources caps={CAMSS_8150};camss.res=&caps;assert(!vfe_pix_line_based(&vfe));
 caps.version=CAMSS_8650;assert(!vfe_pix_line_based(&vfe));caps.version=845;assert(vfe_pix_line_based(&vfe));
 puts("PASS: OEM FULL DMA; layout/32-bit boundaries; capture hook; paired completion/refill/starvation; no plane double completion; Lite RDI3; exact RDI adapter writes; height policy");
 return 0;
}
'''
harness=prefix+functions+tests
path=host.PRIVATE/'full-output-host-private.c';binary=path.with_suffix('')
path.write_text(harness)
build=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
    '-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-pthread',str(path),'-o',str(binary)],capture_output=True,text=True)
(host.PRIVATE/'full-output-host-build-private.log').write_text(build.stdout+build.stderr)
assert build.returncode==0,build.stderr
run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=15)
report=dict(stage=282,source_sha256=hashlib.sha256(functions.encode()).hexdigest(),
    harness_sha256=hashlib.sha256(harness.encode()).hexdigest(),oem_client_register_oracles=checks,
    full_max_dimensions=[4096,4096],nv12_packer=14,exit=run.returncode,stdout=run.stdout,stderr=run.stderr,
    actual_capture_prepare_and_buffer_retirement_functions=True,mock_mmio_only=True,
    no_hardware_nv12_or_image_quality_test=True)
(ROOT/'full-output-host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
assert run.returncode==0 and not run.stderr,report
print(json.dumps({k:v for k,v in report.items() if k!='oem_client_register_oracles'},indent=2))
