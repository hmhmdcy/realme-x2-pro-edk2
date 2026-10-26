"""Exercise actual queue-format, CPU mapping, and retained-owner functions."""
from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'m2m-model';work.mkdir(exist_ok=True)
source=(HERE/'camss-icp-a5-m2m.c').read_text()
assert source==(P/'camss-icp-a5-m2m.c.proposed').read_text()
def function(name):
 m=re.search(r'(?:static )?(?:bool|void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',source,re.S|re.M)
 assert m,name
 return m.group()
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <linux/videodev2.h>
typedef uint32_t u32;typedef uint64_t u64;
#define IPE_IMAGE_MAX (64U*1024U*1024U)
#define U32_MAX UINT32_MAX
#define DMA_BIDIRECTIONAL 0
#define min(a,b) ((a)<(b)?(a):(b))
#define min_t(t,a,b) min((t)(a),(t)(b))
#define max_t(t,a,b) ((t)(a)>(t)(b)?(t)(a):(t)(b))
#define clamp_val(x,lo,hi) min(max_t(u32,x,lo),hi)
#define ALIGN(x,a) (((x)+(a)-1)&~((u64)(a)-1))
struct file{int dummy;};
struct list_head{struct list_head *next,*prev;};
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define list_for_each_entry_safe(p,n,h,m) for(p=container_of((h)->next,__typeof__(*p),m),n=container_of(p->m.next,__typeof__(*p),m);&p->m!=(h);p=n,n=container_of(n->m.next,__typeof__(*n),m))
static void init_list(struct list_head *p){p->next=p->prev=p;}
static void list_add_tail(struct list_head *p,struct list_head *h){p->prev=h->prev;p->next=h;h->prev->next=p;h->prev=p;}
static void list_del(struct list_head *p){p->prev->next=p->next;p->next->prev=p->prev;}
static unsigned frees,stop_mode;
static void kfree(void *p){frees++;free(p);}
struct module{unsigned refs;};
static void module_put(struct module *m){assert(m->refs);m->refs--;}
struct camss_a5{bool backing,cpu_enabled,irq_enabled,power_held,ipe_dma_pending,config_fw_mapped,request_fw_mapped;u32 session_count;struct{u32 enabled_groups,held_domains;}resources;};
struct ipe_context{bool closed;struct{struct camss_a5 *a5;u32 handle;}session;struct list_head node;struct v4l2_pix_format_mplane format;};
struct camss_a5_m2m{struct camss_a5 *a5;struct module *owner;struct list_head contexts;bool running,power_pin;u64 stops;};
static struct camss_a5_m2m *active;
static bool camss_a5_backing_owned(const struct camss_a5 *a){return a->backing;}
static int camss_a5_stop(struct camss_a5 *a){if(stop_mode==1)return -ETIMEDOUT;if(stop_mode==2)return 0;struct ipe_context *p,*n;list_for_each_entry_safe(p,n,&active->contexts,node){p->session.a5=NULL;p->session.handle=0;}memset(a,0,sizeof(*a));return 0;}
struct dma_buf{int dummy;};
struct iosys_map{void *vaddr;bool is_iomem;};
static bool iosys_map_is_null(struct iosys_map *m){return !m->vaddr;}
struct vb2_queue{void *priv;};
struct vb2_buffer{struct vb2_queue *vb2_queue;unsigned type;struct{u32 data_offset;unsigned long size,payload;struct dma_buf *dbuf;void *vaddr;}planes[1];};
static void *vb2_get_drv_priv(struct vb2_queue *q){return q->priv;}
static void *vb2_plane_vaddr(struct vb2_buffer *v,unsigned i){return v->planes[i].vaddr;}
static unsigned long vb2_plane_size(struct vb2_buffer *v,unsigned i){return v->planes[i].size;}
static unsigned long vb2_get_plane_payload(struct vb2_buffer *v,unsigned i){return v->planes[i].payload;}
static void vb2_set_plane_payload(struct vb2_buffer *v,unsigned i,unsigned long n){v->planes[i].payload=n;}
static unsigned mode,begins,ends,maps,unmaps;
static unsigned char memory[4096];
static int dma_buf_begin_cpu_access(struct dma_buf *d,int direction){(void)d;(void)direction;if(mode==1)return -EIO;begins++;return 0;}
static int dma_buf_end_cpu_access(struct dma_buf *d,int direction){(void)d;(void)direction;ends++;return mode==5?-EIO:0;}
static int dma_buf_vmap_unlocked(struct dma_buf *d,struct iosys_map *m){(void)d;if(mode==2)return -ENOMEM;maps++;m->vaddr=mode==4?NULL:memory;m->is_iomem=mode==3;return 0;}
static void dma_buf_vunmap_unlocked(struct dma_buf *d,struct iosys_map *m){(void)d;(void)m;unmaps++;}
struct ipe_cpu_buffer{struct dma_buf *dma;struct iosys_map map;void *address;bool access,mapped;};
'''
body='\n'.join(function(n) for n in ['backing_owned','reap_closed','stop_backend','cpu_begin','cpu_end','buffer_prepare','try_format'])
main=r'''
int main(void){
 unsigned values[]={0,1,127,128,129,640,8192,8193,0xffffffff};unsigned formats=0;
 for(unsigned i=0;i<9;i++)for(unsigned j=0;j<9;j++)for(unsigned k=0;k<2;k++){
 struct v4l2_format f={.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE};f.fmt.pix_mp.width=values[i];f.fmt.pix_mp.height=values[j];f.fmt.pix_mp.pixelformat=k?V4L2_PIX_FMT_NV21:0;f.fmt.pix_mp.plane_fmt[0].bytesperline=k?0xffffffff:0;
 assert(!try_format(NULL,NULL,&f));struct v4l2_pix_format_mplane *p=&f.fmt.pix_mp;assert(p->width>=128 && p->width<=8192 && !(p->width&1) && p->height>=128 && p->height<=8192 && !(p->height&1));assert(p->num_planes==1 && p->plane_fmt[0].bytesperline>=p->width && !(p->plane_fmt[0].bytesperline&1) && p->plane_fmt[0].sizeimage<=IPE_IMAGE_MAX && (u64)p->plane_fmt[0].bytesperline*p->height*3/2==p->plane_fmt[0].sizeimage);formats++;
 }
 struct v4l2_format invalid={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE};assert(try_format(NULL,NULL,&invalid)==-EINVAL);
 struct ipe_context ctx={0};ctx.format.plane_fmt[0].sizeimage=1024;struct vb2_queue q={&ctx};struct dma_buf dma={0};
 struct vb2_buffer vb={.vb2_queue=&q,.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE,.planes={{.data_offset=17,.size=2048,.payload=1041,.vaddr=memory}}};
 assert(!buffer_prepare(&vb));vb.planes[0].payload=1040;assert(buffer_prepare(&vb)==-EINVAL);vb.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;assert(!buffer_prepare(&vb) && vb.planes[0].payload==1041);
 vb.planes[0].data_offset=2049;assert(buffer_prepare(&vb)==-EINVAL);vb.planes[0].data_offset=1025;assert(buffer_prepare(&vb)==-EINVAL);
 vb.planes[0].size=(1ULL<<32)+4096;vb.planes[0].data_offset=0xfffffffe;assert(buffer_prepare(&vb)==-EINVAL);vb.planes[0].data_offset=17;vb.planes[0].size=2048;
 struct ipe_cpu_buffer cpu={0};assert(!cpu_begin(&vb,&cpu) && cpu.address==memory+17 && !cpu_end(&cpu));vb.planes[0].vaddr=NULL;memset(&cpu,0,sizeof(cpu));assert(cpu_begin(&vb,&cpu)==-EFAULT && !cpu_end(&cpu));vb.planes[0].dbuf=&dma;
 for(mode=0;mode<6;mode++){memset(&cpu,0,sizeof(cpu));begins=ends=maps=unmaps=0;int ret=cpu_begin(&vb,&cpu),end=cpu_end(&cpu);assert(ret==(mode==1?-EIO:mode==2?-ENOMEM:mode==3||mode==4?-EOPNOTSUPP:0));assert(end==(mode==5?-EIO:0));assert(begins==ends && maps==unmaps);}
 struct camss_a5 a={.backing=true,.cpu_enabled=true,.session_count=2};struct module owner={1};struct camss_a5_m2m dev={.a5=&a,.owner=&owner,.running=true,.power_pin=true};active=&dev;init_list(&dev.contexts);
 struct ipe_context *closed=calloc(1,sizeof(*closed)),*live=calloc(1,sizeof(*live));assert(closed&&live);closed->closed=true;closed->session.a5=live->session.a5=&a;closed->session.handle=1;live->session.handle=2;list_add_tail(&closed->node,&dev.contexts);list_add_tail(&live->node,&dev.contexts);
 stop_mode=1;assert(stop_backend(&dev)==-ETIMEDOUT && dev.power_pin && owner.refs==1 && !frees && closed->session.a5==&a);
 stop_mode=2;assert(stop_backend(&dev)==-EIO && dev.power_pin && owner.refs==1 && !frees);
 stop_mode=0;assert(!stop_backend(&dev) && !dev.power_pin && !dev.running && !owner.refs && frees==1 && !live->session.a5 && dev.contexts.next==&live->node);
 list_del(&live->node);free(live);
 printf("{\"format_cases\":%u,\"passed\":true}\n",formats);return 0;}
'''
(work/'probe.c').write_text(prefix+body+main)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);(work/'build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(work/'probe')],capture_output=True);(work/'run-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
report=dict(stage=386,**json.loads(q.stdout),actual_m2m_format_buffer_cpu_mapping_retained_session_and_stop_functions=True,
 asan_ubsan=True,offset_and_payload_overflow_checked=True,dmabuf_begin_vmap_iomem_null_and_end_failure_balanced=True,
 failed_or_incomplete_stop_retains_owner_and_linked_closed_session=True,successful_retry_reaps_only_closed_sessions=True,
 v4l2_scheduler_dma_irq_and_module_providers_modelled=True,no_hardware_or_full_queue_lifetime_claim=True)
(HERE/'m2m-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
