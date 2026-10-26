"""Exercise actual BHIST, FULL validation and metadata callbacks under ASan/UBSan."""
from pathlib import Path
import hashlib,json,re,resource,subprocess,sys
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
import host
ROOT=Path(__file__).resolve().parent;D=Path('/home/cy122/x2pro-linux/camera279-isp-kernel/drivers/media/platform/qcom/camss')
def function(text,name):
 m=re.search(r'(?:static )?(?:int|void|u32) '+name+r'\(.*?\n\}',text,re.S);assert m,name;return m[0]
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <linux/qcom-camss-config.h>
#include <linux/videodev2.h>
#include <linux/v4l2-mediabus.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;
#define U16_MAX UINT16_MAX
#define U32_MAX UINT32_MAX
#define BIT(n) (1U<<(n))
#define GENMASK(h,l) ((UINT32_MAX>>(31-(h)))&(~0U<<(l)))
#define FIELD_PREP(mask,v) (((u32)(v)<<__builtin_ctz(mask))&(mask))
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define IS_ALIGNED(x,a) (!((x)&((a)-1)))
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define MSM_VFE_PAD_SINK 0
#define MSM_VFE_PAD_SRC 1
#define MSM_VFE_PAD_SRC_STATS 4
#define MSM_VFE_PAD_SINK_PARAMS 5
#define CAMSS_INIT_BUF_COUNT 2
#define VFE_OUTPUT_OFF 0
#define VFE_OUTPUT_RESERVED 1
#define VFE_OUTPUT_ON 2
#define VFE_175_FULL_Y 3
#define VFE_175_FULL_C 4
#define VFE_175_FULL_MAX_WIDTH 4096
#define VFE_175_FULL_MAX_HEIGHT 4096
#define VB2_BUF_STATE_ERROR 3
#define VB2_BUF_STATE_QUEUED 4
struct device {int dummy;};struct vfe_device;struct vfe_output;struct camss_video;struct camss_buffer;
struct vb2_queue {void *drv_priv;bool streaming;};
struct camss_video_ops{int (*start_metadata)(struct camss_video*);void(*stop_metadata)(struct camss_video*);int(*flush_buffers)(struct camss_video*,int);};
struct camss_video{struct vb2_queue vb2_q;struct v4l2_format active_fmt;const struct camss_video_ops*ops;};
struct camss_buffer{u64 addr[2];int id;};
struct vfe_line;
struct vfe_output{struct vfe_line*line;struct camss_video video_out;unsigned pad,wm_num,comp_group,state,sequence,sof_sequence,wait_reg_update;int reg_update;
 struct{unsigned bus_client,plane;}wm[2];u64 dma_addr;size_t dma_size;void*dma_vaddr;struct camss_buffer*buf[2],*pending[8];unsigned pending_count;struct{unsigned active_num;}gen2;};
struct vfe_line{struct vfe_device*owner;bool is_pix;unsigned num_outputs,id;struct vfe_output output[5];struct v4l2_mbus_framefmt fmt[6];};
struct vfe_175_stats_state{u16 left,top,width,height;bool enabled;};
struct vfe_175_pixel_state{u16 g_gain,b_gain,r_gain;bool wb_enabled;struct vfe_175_stats_state stats;};
struct vfe_hw_ops{int(*vfe_output_prepare)(struct vfe_device*,struct vfe_output*);void(*vfe_output_start)(struct vfe_device*,struct vfe_output*);void(*vfe_output_stop)(struct vfe_device*,struct vfe_output*);void(*vfe_output_update)(struct vfe_device*,struct vfe_output*,struct camss_buffer*);void(*vfe_wm_start)(struct vfe_device*,u8,struct vfe_line*);void(*vfe_wm_stop)(struct vfe_device*,u8,struct vfe_line*);void(*vfe_wm_update)(struct vfe_device*,u8,u32,struct vfe_line*);void(*reg_update)(struct vfe_device*,unsigned);};
struct resource{const struct vfe_hw_ops*hw_ops;};struct camss{struct device*dev;};
struct vfe_device{unsigned char*base;struct vfe_175_pixel_state pixel175;struct resource*res;struct camss*camss;int output_lock;};
static struct vfe_device *to_vfe(struct vfe_line*l){return l->owner;}
static bool vb2_is_streaming(struct vb2_queue*q){return q->streaming;}
static void *vb2_get_drv_priv(struct vb2_queue*q){return q->drv_priv;}
static unsigned locked,starts,stops,updates,reg_updates,flushes,flush_state,writes,stop_reads;static int prepare_error;
struct regwrite{unsigned addr,value;};static struct regwrite trace[4096];static u32 memory[0x4000/4];
static void writel_relaxed(u32 v,void*p){size_t a=(unsigned char*)p-(unsigned char*)memory;assert(a<sizeof(memory)&&!(a&3));if(writes<ARRAY_SIZE(trace))trace[writes]=(struct regwrite){a,v};writes++;*(u32*)p=v;}

static u32 bhist_sram[1024];static unsigned sram_writes;
static __attribute__((unused)) void writel(u32 value,void*p){
 size_t offset=(unsigned char*)p-(unsigned char*)memory;
 if(offset==0xc30){
  assert((memory[0xc24/4]&0x7f)==0x3a);
  assert(!(memory[0xc24/4]&0x1100));
  assert(memory[0x30/4]&0x10);
  unsigned address=memory[0xc28/4];assert(address<1024&&address==sram_writes%1024);
  assert(value==0);bhist_sram[address]=value;sram_writes++;
 }
 writel_relaxed(value,p);
}

static u32 readl_relaxed(void*p){return *(u32*)p;}
static u32 readl(void*p){stop_reads++;return *(u32*)p;}
#define spin_lock_irqsave(l,f) do{(void)(l);(f)=0;assert(!locked);locked=1;}while(0)
#define spin_unlock_irqrestore(l,f) do{(void)(l);(void)(f);assert(locked);locked=0;}while(0)
#define WARN_ON(v) assert(!(v))
#define reinit_completion(c) ((void)(c))
#define dev_err(...) ((void)0)
static struct camss_buffer *vfe_buf_get_pending(struct vfe_output*o){if(!o->pending_count)return NULL;struct camss_buffer*b=o->pending[0];memmove(o->pending,o->pending+1,(--o->pending_count)*sizeof(o->pending[0]));return b;}
static void reset_trace(void){writes=0;stop_reads=0;}
static void random_regs(void){for(unsigned i=0;i<ARRAY_SIZE(memory);i++)memory[i]=0xa5a5a5a5U;reset_trace();}
'''
stats=subprocess.check_output(['git','-C',str(D.parents[4]),'show','d249946aefa1a01d99fd5484825a4458423b7348:drivers/media/platform/qcom/camss/camss-vfe-175-stats.c'],text=True) if '--parent' in sys.argv else (D/'camss-vfe-175-stats.c').read_text();stats='\n'.join(l for l in stats.splitlines() if not l.startswith('#include'))+'\n'
common=(D/'camss-vfe.c').read_text();video=(D/'camss-video.c').read_text();output=(D/'camss-vfe-175-output.c').read_text();backend=(D/'camss-vfe-17x.c').read_text();pixel=(D/'camss-vfe-175-pixel.c').read_text()
parts=[stats,function(output,'vfe_175_validate_output'),function(output,'vfe_175_validate_buffer'),function(backend,'vfe_output_prepare_175')]
parts += [function(common,n) for n in ['vfe_enable_one_output','vfe_start_metadata_v2','vfe_stop_metadata_v2']]
parts += [function(video,n) for n in ['video_meta_start_streaming','video_meta_stop_streaming']]
# Actual WB helpers plus mixed typed dispatch prevent interpreting BHIST as gains.
parts += [l for l in pixel.splitlines() if l.startswith('#define VFE_175_WB')]
parts += [function(pixel,n) for n in ['vfe_175_wb_q7','vfe_175_wb_write','vfe_175_wb_validate','vfe_175_params_apply']]
main=r'''
static void start_output(struct vfe_device*v,struct vfe_output*o){assert(locked);starts++;vfe_175_stats_start(v,o);}
static void stop_output(struct vfe_device*v,struct vfe_output*o){assert(locked);stops++;vfe_175_stats_stop(v,o);}
static void update_output(struct vfe_device*v,struct vfe_output*o,struct camss_buffer*b){(void)b;assert(locked);updates++;vfe_175_stats_update(v,o);}
static int prepare_output(struct vfe_device*v,struct vfe_output*o){assert(locked);return prepare_error?prepare_error:vfe_output_prepare_175(v,o);}
static void reg_update(struct vfe_device*v,unsigned id){(void)v;(void)id;assert(locked);reg_updates++;}
static int flush(struct camss_video*vid,int state){struct vfe_output*o=container_of(vid,struct vfe_output,video_out);if(state==VB2_BUF_STATE_ERROR)assert(o->state!=VFE_OUTPUT_ON);flushes++;flush_state=state;return 0;}
static const struct camss_video_ops video_ops={.start_metadata=vfe_start_metadata_v2,.stop_metadata=vfe_stop_metadata_v2,.flush_buffers=flush};
static const struct vfe_hw_ops hw={.vfe_output_prepare=prepare_output,.vfe_output_start=start_output,.vfe_output_stop=stop_output,.vfe_output_update=update_output,.reg_update=reg_update};
static struct resource resource={.hw_ops=&hw};static struct device dev;static struct camss camss={.dev=&dev};
static u32 rng=0x9e3779b9;static u32 next(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static void queue(struct vfe_output*o,struct camss_buffer*b,unsigned n){o->pending_count=n;for(unsigned i=0;i<n;i++)o->pending[i]=&b[i];}
int main(void){
 for(unsigned i=0;i<1024;i++)bhist_sram[i]=0x6bad0000U+i;
 struct vfe_device v={.base=(void*)memory,.res=&resource,.camss=&camss};struct vfe_line l={.owner=&v,.is_pix=true,.num_outputs=3};
 struct vfe_output*full=&l.output[0],*params=&l.output[1],*o=&l.output[2];
 for(unsigned i=0;i<5;i++){l.output[i].line=&l;l.output[i].video_out.vb2_q.drv_priv=&l.output[i].video_out;}
 full->pad=1;full->wm_num=2;full->wm[0].bus_client=3;full->wm[1].bus_client=4;full->wm[1].plane=1;
 struct v4l2_pix_format_mplane*pix=&full->video_out.active_fmt.fmt.pix_mp;
 pix->pixelformat=V4L2_PIX_FMT_NV12;pix->num_planes=1;pix->width=320;pix->height=240;pix->plane_fmt[0].bytesperline=320;pix->plane_fmt[0].sizeimage=115200;
 params->pad=5;o->pad=4;o->wm_num=1;o->wm[0].bus_client=16;o->comp_group=1;o->dma_size=4096;o->dma_addr=0x400000;o->dma_vaddr=malloc(4096);assert(o->dma_vaddr);o->video_out.ops=&video_ops;
 assert(!vfe_175_validate_output(full)&&!vfe_175_stats_validate_output(o));
 struct camss_buffer image={.addr={0x10000,0x10000+76800}};assert(!vfe_175_validate_buffer(full,&image));
 o->dma_addr++;assert(vfe_175_stats_validate_output(o)==-ERANGE&&vfe_175_validate_output(full)==-EINVAL);o->dma_addr--;
 o->dma_addr=UINT32_MAX-255;assert(vfe_175_stats_validate_output(o)==-ERANGE);o->dma_addr=0x400000;
 o->wm[0].bus_client=15;assert(vfe_175_stats_validate_output(o)==-EINVAL);o->wm[0].bus_client=16;
 o->dma_size=4095;assert(vfe_175_stats_validate_output(o)==-EINVAL);o->dma_size=4096;
 struct camss_params_aec_bhist r={.header={CAMSS_PARAMS_AEC_BHIST,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(r)},.width=640,.height=480};
 for(unsigned flags=0;flags<16;flags++){r.header.flags=flags;assert((!vfe_175_bhist_validate(&dev,&r.header))==(flags==0||flags==1||flags==2));}r.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;
 r.width=2;assert(vfe_175_bhist_validate(&dev,&r.header)==-EINVAL);r.width=640;r.left=1;assert(vfe_175_bhist_validate(&dev,&r.header)==-EINVAL);r.left=0;
 struct v4l2_isp_block_header*short_disable=malloc(sizeof(*short_disable));assert(short_disable);*short_disable=(struct v4l2_isp_block_header){CAMSS_PARAMS_AEC_BHIST,V4L2_ISP_PARAMS_FL_BLOCK_DISABLE,sizeof(*short_disable)};assert(!vfe_175_bhist_validate(&dev,short_disable));
 l.fmt[0].width=1632;l.fmt[0].height=1224;random_regs();assert(!vfe_175_stats_prepare(&l));
 assert(v.pixel175.stats.width==1632&&v.pixel175.stats.height==1224&&v.pixel175.stats.enabled);
 assert(sram_writes==1024);
 for(unsigned i=0;i<1024;i++)assert(!bhist_sram[i]);
 assert(memory[0xc24/4]==0xa5a5a5a5U&&memory[0xc28/4]==0xa5a5a5a5U&&memory[0x30/4]==0xa5a5a5a5U);
 assert((memory[0x44/4]&BIT(5))==(0xa5a5a5a5U&BIT(5)));
 assert(!(memory[0x44/4]&BIT(4)));assert((memory[0xaac/4]&GENMASK(23,21))==0&&(memory[0xaac/4]&BIT(4)));
 assert((memory[0xbe4/4]&~(GENMASK(12,0)|GENMASK(29,16)))==(0xa5a5a5a5U&~(GENMASK(12,0)|GENMASK(29,16))));
 assert((memory[0xbe8/4]&GENMASK(11,0))==815&&((memory[0xbe8/4]>>16)&0x1fff)==611);
 for(unsigned i=0;i<100000;i++){
  l.fmt[0].width=4+(next()%4095)*2;l.fmt[0].height=2+(next()%8192)*2;
  r.left=(next()%4096)*2;r.top=(next()%8192)*2;r.width=4+(next()%4095)*2;r.height=2+(next()%8192)*2;
  assert(!vfe_175_bhist_validate(&dev,&r.header));reset_trace();vfe_175_stats_params(&v,&l,&r.header);
  struct vfe_175_stats_state*s=&v.pixel175.stats;assert(s->width>=4&&s->height>=2&&s->left+s->width<=l.fmt[0].width&&s->top+s->height<=l.fmt[0].height);
  assert(!((s->left|s->top|s->width|s->height)&1)&&writes==4);
  assert((memory[0xbe4/4]&0x1fff)==s->left&&((memory[0xbe4/4]>>16)&0x3fff)==s->top);
  assert((memory[0xbe8/4]&0xfff)==s->width/2-1&&((memory[0xbe8/4]>>16)&0x1fff)==s->height/2-1);
 }
 vfe_175_stats_params(&v,&l,short_disable);assert(!v.pixel175.stats.enabled);
 r.header.flags=0;vfe_175_stats_params(&v,&l,&r.header);assert(!v.pixel175.stats.enabled);r.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;vfe_175_stats_params(&v,&l,&r.header);assert(v.pixel175.stats.enabled);
 o->video_out.vb2_q.streaming=true;l.fmt[0].width=10000;l.fmt[0].height=4000;reset_trace();assert(vfe_175_stats_prepare(&l)==-EINVAL&&!writes);o->video_out.vb2_q.streaming=false;assert(!vfe_175_stats_prepare(&l)&&!v.pixel175.stats.width);
 l.fmt[0].width=1632;l.fmt[0].height=1224;assert(!vfe_175_stats_prepare(&l));
 struct camss_buffer buffers[3]={{.id=0},{.id=1},{.id=2}};queue(o,buffers,3);reset_trace();
 assert(!video_meta_start_streaming(&o->video_out.vb2_q,3)&&!writes&&!starts&&o->pending_count==3);
 full->state=VFE_OUTPUT_ON;full->sequence=42;assert(!video_meta_start_streaming(&o->video_out.vb2_q,3));
 assert(starts==1&&updates==2&&o->state==VFE_OUTPUT_ON&&o->sequence==42&&o->gen2.active_num==2&&o->pending_count==1&&reg_updates==3);
 assert(memory[(0x2200+16*256+8)/4]==3&&memory[(0x2200+16*256+0x24)/4]==0xa&&memory[(0x2200+16*256+0x28)/4]==1);
 assert(memory[(0x2200+16*256+0x14)/4]==0x400000&&(memory[0x2014/4]&BIT(16))&&(memory[0x44/4]&BIT(4)));
 u32 primary_cfg=memory[(0x2200+3*256+8)/4];video_meta_stop_streaming(&o->video_out.vb2_q);
 assert(stops==1&&stop_reads==1&&flushes==1&&flush_state==VB2_BUF_STATE_ERROR&&full->state==VFE_OUTPUT_ON&&primary_cfg==memory[(0x2200+3*256+8)/4]);
 assert(!(memory[0x2014/4]&BIT(16))&&!(memory[0x44/4]&BIT(4))&&memory[(0x2200+16*256+8)/4]==0);
 reset_trace();o->gen2.active_num=0;queue(o,buffers,3);prepare_error=-EINVAL;assert(video_meta_start_streaming(&o->video_out.vb2_q,3)==-EINVAL&&!writes&&flushes==2&&flush_state==VB2_BUF_STATE_QUEUED&&o->state==VFE_OUTPUT_OFF);prepare_error=0;
 assert(!video_meta_start_streaming(&o->video_out.vb2_q,3)&&starts==2);video_meta_stop_streaming(&o->video_out.vb2_q);
 unsigned prior=stops;full->state=VFE_OUTPUT_OFF;reset_trace();video_meta_stop_streaming(&o->video_out.vb2_q);assert(stops==prior&&!writes);
 params->video_out.ops=&video_ops;reset_trace();assert(!video_meta_start_streaming(&params->video_out.vb2_q,1)&&!writes);video_meta_stop_streaming(&params->video_out.vb2_q);assert(!writes);
 /* A mixed buffer must update the named modules independently. */
 size_t bytes=sizeof(struct camss_params_wb_gain)+sizeof(r);struct v4l2_isp_buffer*p=calloc(1,sizeof(*p)+bytes);assert(p);p->version=V4L2_ISP_VERSION_V1;p->data_size=bytes;
 struct camss_params_wb_gain wb={.header={CAMSS_PARAMS_WB_GAIN,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(wb)},.g_gain=1024,.b_gain=1024,.r_gain=256};memcpy(p->data,&wb,sizeof(wb));r.width=320;r.height=240;r.left=0;r.top=0;r.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;memcpy(p->data+sizeof(wb),&r,sizeof(r));
 assert(!vfe_175_wb_validate(&dev,&wb.header));vfe_175_params_apply(&v,&l,p);assert(v.pixel175.r_gain==256&&v.pixel175.stats.width==320&&v.pixel175.stats.height==240);
 p->data_size=sizeof(*short_disable);memcpy(p->data,short_disable,sizeof(*short_disable));vfe_175_params_apply(&v,&l,p);assert(v.pixel175.r_gain==256&&!v.pixel175.stats.enabled);
 free(p);free(short_disable);free(o->dma_vaddr);puts("PASS: actual BHIST ROI 100000 cases, descriptor/DMA bounds, metadata lifecycle and mixed WB dispatch");return 0;
}
'''
source=prefix+'\n'+'\n'.join(parts)+main;p=host.PRIVATE/('parent-init-stats-tests-private.c' if '--parent' in sys.argv else 'stats-tests-private.c');p.write_text(source);binary=p.with_suffix('')
flags=['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-D__EXPORTED_HEADERS__','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi']
q=subprocess.run(flags+[str(p),'-o',str(binary)],capture_output=True);(host.PRIVATE/'stats-tests-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary)],capture_output=True,timeout=30);(host.PRIVATE/'stats-tests-private.log').write_bytes(q.stdout+q.stderr)
if '--parent' in sys.argv:
 assert q.returncode!=0
 (ROOT/'parent-init-validation.json').write_text(json.dumps(dict(stage=296,actual_parent_function=True,independent_sram_initialization_contract=True,expected_failure_observed=True,exit=q.returncode),indent=2)+'\n')
 print('Pinned SRAM initialization contract rejects the actual k295 implementation.');sys.exit(0)
assert q.returncode==0,q.stderr.decode()
report=dict(stage=296,bhist_all_1024_sram_words_cleared=True,dmi_cgc_config_address_restored=True,explicit_indices_and_mode_checked=True,asan_ubsan=True,actual_functions=True,random_roi_cases=100000,header_only_disable_guarded=True,
 descriptor_dma_and_client_validation=True,roi_register_reserved_bits_preserved=True,late_metadata_start_and_stop_without_image_restart=True,
 start_error_returns_queued_buffers=True,stop_before_metadata_flush=True,mixed_wb_bhist_dispatch=True,source_sha256=hashlib.sha256((D/'camss-vfe-175-stats.c').read_bytes()).hexdigest(),harness_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),output=q.stdout.decode().strip(),not_hardware_validated=True)
(ROOT/'stats-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
