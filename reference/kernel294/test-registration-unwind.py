from pathlib import Path
import hashlib,json,re,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel');p=TREE/'drivers/media/platform/qcom/camss/camss-vfe.c';actual=p.read_text()
def function(text,name):
 m=re.search(r'(?:static )?(?:int|void) '+name+r'\(.*?\n\}',text,re.S);assert m,name;return m[0]
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <linux/qcom-camss-config.h>
#include <linux/videodev2.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof(a[0]))
#define MSM_VFE_PAD_SINK 0
#define MSM_VFE_PAD_SRC 1
#define MSM_VFE_PAD_SRC_DS4 2
#define MSM_VFE_PAD_SRC_DS16 3
#define MSM_VFE_PAD_SRC_STATS 4
#define MSM_VFE_PAD_SINK_PARAMS 5
#define MSM_VFE_PAD_NUM_PIX 6
#define MSM_VFE_NAME "msm_vfe"
#define CAMSS_8150 8150
#define V4L2_SUBDEV_FL_HAS_DEVNODE 1
#define V4L2_SUBDEV_FL_HAS_EVENTS 2
#define MEDIA_PAD_FL_SINK 1
#define MEDIA_PAD_FL_SOURCE 2
#define MEDIA_ENT_F_PROC_VIDEO_PIXEL_FORMATTER 1
#define MEDIA_LNK_FL_IMMUTABLE 1
#define MEDIA_LNK_FL_ENABLED 2
#define dev_err(dev,...) ((void)(dev))
#define mutex_destroy(p) ((void)(p))
#define v4l2_isp_buffer_size(s) (sizeof(struct v4l2_isp_buffer)+(s))
struct device{int x;};struct v4l2_device{int x;};struct media_pad{unsigned flags;};
struct media_entity{char name[64];int function;void*ops;bool initialized;};
struct video_device{struct media_entity entity;bool registered;};
struct v4l2_subdev{char name[64];void*internal_ops;unsigned flags;struct media_entity entity;bool registered;void*data;};
struct camss_video_ops{int x;};struct camss_video{enum v4l2_buf_type type;struct v4l2_format active_fmt;struct video_device vdev;const struct camss_video_ops*ops;unsigned bpl_alignment,line_based,nformats;void*formats;void*frame_sizes;};
struct vfe_output{unsigned pad,wm_num;void*dma_vaddr;struct camss_video video_out;};
struct vfe_line{bool is_pix;unsigned num_pads,num_outputs,nformats;void*formats;struct vfe_output output[5];struct v4l2_subdev subdev;struct media_pad pads[6];};
struct hw_ops{void(*vfe_params_apply)(void);};static void apply(void){}static const struct hw_ops vfe_ops_170={0},vfe_ops_175={.vfe_params_apply=apply};
struct resource{int line_num;const struct hw_ops*hw_ops;struct{unsigned nformats;void*formats;}*formats_pix_out;void*pix_frame_sizes;};
struct camss{struct device*dev;struct{int version;}*res;};struct vfe_device{struct camss*camss;struct resource*res;unsigned id;struct vfe_line line[4];struct camss_video_ops video_ops;int power_lock,stream_lock;};
static unsigned operation,fail_at,videos,subdevs,entities,unregistered_videos;
static bool fail(void){return ++operation==fail_at;}
static int vfe_v4l2_ops,vfe_v4l2_internal_ops,vfe_media_ops;
static void v4l2_subdev_init(struct v4l2_subdev*s,void*ops){(void)ops;assert(!s->registered);}
static void v4l2_set_subdevdata(struct v4l2_subdev*s,void*d){s->data=d;}
static int vfe_init_formats(struct v4l2_subdev*s,void*d){(void)s;(void)d;return fail()?-EINVAL:0;}
static int media_entity_pads_init(struct media_entity*e,unsigned n,struct media_pad*p){(void)n;(void)p;if(fail())return -EINVAL;assert(!e->initialized);e->initialized=true;entities++;return 0;}
static void media_entity_cleanup(struct media_entity*e){assert(e->initialized);e->initialized=false;entities--;}
static int v4l2_device_register_subdev(struct v4l2_device*d,struct v4l2_subdev*s){(void)d;if(fail())return -EINVAL;assert(!s->registered);s->registered=true;subdevs++;return 0;}
static void v4l2_device_unregister_subdev(struct v4l2_subdev*s){assert(s->registered);s->registered=false;subdevs--;}
static int msm_video_register(struct camss_video*v,struct v4l2_device*d,const char*n){(void)d;if(fail())return -EINVAL;assert(!v->vdev.registered&&!v->vdev.entity.initialized);v->vdev.registered=true;v->vdev.entity.initialized=true;snprintf(v->vdev.entity.name,64,"%s",n);videos++;entities++;return 0;}
static void msm_video_unregister(struct camss_video*v){assert(v->vdev.registered&&v->vdev.entity.initialized);v->vdev.registered=false;v->vdev.entity.initialized=false;videos--;entities--;unregistered_videos++;}
static bool video_is_registered(struct video_device*v){return v->registered;}
static int media_create_pad_link(struct media_entity*a,unsigned p,struct media_entity*b,unsigned q,unsigned flags){(void)p;(void)q;(void)flags;assert(a->initialized&&b->initialized);return fail()?-EINVAL:0;}
static int vfe_alloc_stats(struct vfe_device*v,struct vfe_output*o){(void)v;if(fail())return -ENOMEM;o->dma_vaddr=malloc(4096);assert(o->dma_vaddr);return 0;}
static int vfe_bpl_align_pix(struct vfe_device*v){(void)v;return 16;}static bool vfe_pix_line_based(struct vfe_device*v){(void)v;return false;}static int vfe_bpl_align_rdi(struct vfe_device*v){(void)v;return 16;}
'''
shared=function(actual,'vfe_register_meta_nodes')+'\n'+function(actual,'vfe_unregister_meta_nodes')+'\n'
parent=subprocess.check_output(['git','-C',str(TREE),'show','1aa1955077c977b611c722eca0bc467c3bf052ed:drivers/media/platform/qcom/camss/camss-vfe.c'],text=True)
main=r'''
static struct device dev;static struct{int version;}cres={CAMSS_8150};static struct camss camss;
static void init(struct vfe_device*v,struct resource*r){memset(v,0,sizeof(*v));operation=videos=subdevs=entities=unregistered_videos=0;camss.dev=&dev;camss.res=(void*)&cres;v->camss=&camss;v->res=r;
 for(unsigned i=0;i<4;i++){struct vfe_line*l=&v->line[i];l->is_pix=i>=2;l->num_pads=l->is_pix?6:2;l->num_outputs=l->is_pix?3:1;l->output[0].pad=1;l->output[0].wm_num=l->is_pix?2:1;if(l->is_pix){l->output[1].pad=5;l->output[2].pad=4;l->output[2].wm_num=1;}}
}
static void free_managed(struct vfe_device*v){for(unsigned i=0;i<4;i++)for(unsigned o=0;o<5;o++)free(v->line[i].output[o].dma_vaddr);}
int main(void){struct resource r={.line_num=4,.hw_ops=&vfe_ops_175};struct vfe_device v;struct v4l2_device d;
 fail_at=0;init(&v,&r);assert(!msm_vfe_register_entities(&v,&d));unsigned total=operation;assert(videos==8&&subdevs==4);msm_vfe_unregister_entities(&v);assert(!videos&&!subdevs&&!entities);free_managed(&v);
 for(unsigned n=1;n<=total;n++){init(&v,&r);fail_at=n;assert(msm_vfe_register_entities(&v,&d)<0);assert(!videos&&!subdevs&&!entities);free_managed(&v);}
 printf("PASS: actual registration/unwind with %u allocation, format, entity, video and link failure points\n",total);return 0;}
'''
flags=['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-D__EXPORTED_HEADERS__','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I'+str(TREE/'include/uapi')]
for label,text in [('parent',parent),('fixed',actual)]:
 s=prefix+shared+function(text,'msm_vfe_register_entities')+'\n'+function(actual,'msm_vfe_unregister_entities')+main
 p=host.PRIVATE/(label+'-registration-test-private.c');p.write_text(s);binary=p.with_suffix('')
 q=subprocess.run(flags+[str(p),'-o',str(binary)],capture_output=True);(host.PRIVATE/(label+'-registration-compile-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
 q=subprocess.run([str(binary)],capture_output=True,timeout=20);(host.PRIVATE/(label+'-registration-test-private.log')).write_bytes(q.stdout+q.stderr)
 if label=='parent':assert q.returncode!=0
 else:assert q.returncode==0,q.stderr.decode()
report=dict(stage=294,actual_registration_and_unwind_functions=True,asan_ubsan=True,parent_leaks_metadata_on_current_line_failure=True,
 all_allocation_format_entity_video_and_link_failure_points_clean=True,output=q.stdout.decode().strip(),not_hardware_validated=True)
(ROOT/'registration-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
