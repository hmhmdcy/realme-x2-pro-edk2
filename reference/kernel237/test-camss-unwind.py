"""Compile the actual changed functions with graph/buffer fault harnesses."""
from pathlib import Path
import hashlib,json,os,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel237/camss-function-tests');P.mkdir(mode=0o700)
video=(R/'camss-source/camss-video.c').read_text();vfe=(R/'camss-source/camss-vfe.c').read_text()
def function(text,signature):
 a=text.index(signature);b=text.index('{',a);depth=1;i=b+1
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[a:i]+'\n'
vf='\n'.join(function(video,s) for s in ['static void video_stop_subdevices(', 'static int video_start_streaming(', 'static void video_stop_streaming('])
ff='\n'.join(function(vfe,s) for s in ['static void vfe_buf_flush_pending(', 'int vfe_flush_buffers('])
vh=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <stdbool.h>
#define MEDIA_PAD_FL_SINK 1
#define ENOIOCTLCMD 515
#define VB2_BUF_STATE_QUEUED 1
#define VB2_BUF_STATE_ERROR 2
#define dev_err(...) ((void)0)
struct v4l2_subdev { int id; char name[8]; };
struct media_entity;
struct media_pad { int flags; struct media_entity *entity; struct media_pad *remote; };
struct media_entity { struct media_pad pads[1]; struct v4l2_subdev sd; };
struct video_device { struct media_entity entity; };
struct camss_video;
struct ops { void (*flush_buffers)(struct camss_video *, int); };
struct camss { void *dev; };
struct camss_video { struct video_device vdev; struct ops *ops; struct camss *camss; };
struct vb2_queue { struct camss_video *video; };
static int starts[5],stops[5],start_fail,stop_fail,no_ioctl,alloc_fail,format_fail,pipeline_stops,flush_count,flush_state;
static struct camss_video *vb2_get_drv_priv(struct vb2_queue *q) { return q->video; }
static struct media_pad *media_pad_remote_pad_first(struct media_pad *p) { return p->remote; }
static bool is_media_entity_v4l2_subdev(struct media_entity *e) { return e->sd.id>0; }
static struct v4l2_subdev *media_entity_to_v4l2_subdev(struct media_entity *e) { return &e->sd; }
static int call(struct v4l2_subdev *sd,int on) {
 if(on) { starts[sd->id]++; if(start_fail==sd->id)return -73; }
 else { stops[sd->id]++; if(stop_fail==sd->id)return -84; }
 return no_ioctl==sd->id ? -ENOIOCTLCMD : 0;
}
#define v4l2_subdev_call(sd,group,method,on) call(sd,on)
static int video_device_pipeline_alloc_start(struct video_device *v) { (void)v; return alloc_fail ? -61:0; }
static int video_check_format(struct camss_video *v) { (void)v;return format_fail ? -62:0; }
static void video_device_pipeline_stop(struct video_device *v) { (void)v; pipeline_stops++; }
static void flush(struct camss_video *v,int state) { (void)v;flush_count++;flush_state=state; }
'''
vm=r'''
int main(void) {
 int cases=0;
 for(int fail=0;fail<=4;fail++)for(int stop=0;stop<=4;stop++)for(int nio=0;nio<=4;nio++)for(int early=0;early<=2;early++) {
  memset(starts,0,sizeof(starts));memset(stops,0,sizeof(stops));start_fail=fail;stop_fail=stop;no_ioctl=nio;alloc_fail=early==1;format_fail=early==2;pipeline_stops=flush_count=flush_state=0;
  struct camss_video video={0};struct ops ops={flush};struct camss camss={0};video.ops=&ops;video.camss=&camss;
  struct media_entity nodes[4]={0};struct media_entity *prev=&video.vdev.entity;
  for(int i=0;i<4;i++){nodes[i].sd.id=i+1;prev->pads[0].flags=MEDIA_PAD_FL_SINK;nodes[i].pads[0].entity=&nodes[i];prev->pads[0].remote=&nodes[i].pads[0];prev=&nodes[i];}
  struct vb2_queue q={&video};int ret=video_start_streaming(&q,4);
  if(early){assert(ret==(early==1?-61:-62));assert(flush_count==1&&flush_state==VB2_BUF_STATE_QUEUED);assert(pipeline_stops==(early==2));for(int i=1;i<=4;i++)assert(starts[i]==0&&stops[i]==0);}
  else if(fail&&fail!=nio){assert(ret==-73);assert(flush_count==1&&pipeline_stops==1&&flush_state==VB2_BUF_STATE_QUEUED);for(int i=1;i<=4;i++){assert(starts[i]==(i<=fail));assert(stops[i]==(i<fail));}}
  else if(fail){/* start_fail takes precedence over the optional no-ioctl stub. */assert(ret==-73);for(int i=1;i<=4;i++){assert(starts[i]==(i<=fail));assert(stops[i]==(i<fail));}}
  else {assert(ret==0&&pipeline_stops==0&&flush_count==0);video_stop_streaming(&q);assert(pipeline_stops==1&&flush_count==1&&flush_state==VB2_BUF_STATE_ERROR);for(int i=1;i<=4;i++)assert(starts[i]==1&&stops[i]==1);}
  cases++;
 }
 printf("video_cases=%d\n",cases);return 0;
}
'''
fh=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <stdbool.h>
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
#define spin_lock_irqsave(lock,flags) ((void)(lock),(flags)=0)
#define spin_unlock_irqrestore(lock,flags) ((void)(lock),(void)(flags))
enum vb2_buffer_state { VB2_BUF_STATE_ACTIVE=0, VB2_BUF_STATE_QUEUED=1, VB2_BUF_STATE_ERROR=2 };
struct list_head { struct list_head *next,*prev; };
struct vb2 { enum vb2_buffer_state state;int id,calls; };
struct camss_buffer { struct { struct vb2 vb2_buf; } vb; struct list_head queue; };
struct vfe_output { struct camss_buffer *buf[2],*last_buffer;struct list_head pending_bufs;union { struct { int active_buf,wait_sof; } gen1;struct { int active_num; } gen2; }; };
static struct vfe_output *observed;
static void list_del(struct list_head *p) { p->next->prev=p->prev;p->prev->next=p->next;p->next=p->prev=NULL; }
static void list_add_tail(struct list_head *p,struct list_head *h){p->next=h;p->prev=h->prev;h->prev->next=p;h->prev=p;}
#define list_for_each_entry_safe(pos,tmp,head,member) \
 for(struct list_head *_p=(head)->next,*_n; _p!=(head) && (_n=_p->next,1) && ((pos)=container_of(_p,struct camss_buffer,member),(tmp)=_n==(head)?NULL:container_of(_n,struct camss_buffer,member),1);_p=_n)
static void vb2_buffer_done(struct vb2 *b,enum vb2_buffer_state state) {
 assert(!observed->buf[0]&&!observed->buf[1]&&!observed->last_buffer);
 assert(b->state==VB2_BUF_STATE_ACTIVE&&b->calls==0);b->calls++;b->state=state;
}
struct camss_video { int unused; };
struct vfe_ops { int id; };static struct vfe_ops vfe_ops_170,other_ops;
struct resource { struct vfe_ops *hw_ops; };
struct vfe_device { struct resource *res;int output_lock; };
struct vfe_line { struct camss_video video_out;struct vfe_output output;struct vfe_device *vfe; };
static struct vfe_device *to_vfe(struct vfe_line *line){return line->vfe;}
'''
fm=r'''
int main(void) {
 int cases=0;
 for(int gen=0;gen<2;gen++)for(int a=0;a<4;a++)for(int b=0;b<4;b++)for(int c=0;c<4;c++)for(int active=0;active<8;active++)for(int pending=0;pending<8;pending++) {
  struct resource res={gen?&vfe_ops_170:&other_ops};struct vfe_device vfe={&res,0};struct vfe_line line={0};line.vfe=&vfe;observed=&line.output;
  struct camss_buffer buf[3]={0};struct camss_buffer *ptrs[4]={NULL,&buf[0],&buf[1],&buf[2]};
  observed->buf[0]=ptrs[a];observed->buf[1]=ptrs[b];observed->last_buffer=ptrs[c];observed->gen1.active_buf=7;observed->gen1.wait_sof=23;
  observed->pending_bufs.next=observed->pending_bufs.prev=&observed->pending_bufs;
  for(int i=0;i<3;i++){buf[i].vb.vb2_buf.id=i;buf[i].vb.vb2_buf.state=(active&(1<<i))?VB2_BUF_STATE_ACTIVE:VB2_BUF_STATE_QUEUED;if(pending&(1<<i))list_add_tail(&buf[i].queue,&observed->pending_bufs);}
  assert(vfe_flush_buffers(&line.video_out,VB2_BUF_STATE_ERROR)==0);
  assert(!observed->buf[0]&&!observed->buf[1]&&!observed->last_buffer);
  assert(observed->pending_bufs.next==&observed->pending_bufs&&observed->pending_bufs.prev==&observed->pending_bufs);
  assert(gen ? observed->gen2.active_num==0 : observed->gen1.active_buf==7&&observed->gen1.wait_sof==23);
  for(int i=0;i<3;i++){bool touched=(pending&(1<<i))||a==i+1||b==i+1||c==i+1;assert(buf[i].vb.vb2_buf.calls==((active&(1<<i))&&touched?1:0));}
  cases++;
 }
 printf("buffer_cases=%d\n",cases);return 0;
}
'''
variants={'video-actual':(vh+vf+vm,True),'buffer-actual':(fh+ff+fm,True),
 'negative-no-unwind':(vh+vf.replace('video_stop_subdevices(video, entity);',';')+vm,False),
 'negative-stop-early':(vh+vf.replace('subdev->name, ret);','subdev->name, ret);\n\t\tif (ret < 0 && ret != -ENOIOCTLCMD) return;')+vm,False),
 'negative-stale-pointers':(fh+ff.replace('output->buf[0] = NULL;',';')+fm,False),
 'negative-gen1-overwrite':(fh+ff.replace('if (vfe->res->hw_ops == &vfe_ops_170)','if (1)')+fm,False)}
results={}
for name,(source,expected) in variants.items():
 src=P/(name+'.c');src.write_text(source);binary=P/name
 build=subprocess.run(['gcc','-std=gnu11','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer','-Wno-unused-parameter',str(src),'-o',str(binary)],capture_output=True)
 (P/(name+'-build.log')).write_bytes(build.stdout+build.stderr);assert build.returncode==0,name
 run=subprocess.run([str(binary)],capture_output=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:disable_coredump=1'));(P/(name+'-run.log')).write_bytes(run.stdout+run.stderr)
 passed=run.returncode==0;assert passed==expected,(name,run.returncode)
 results[name]=dict(passed=passed,exit=run.returncode,stdout=run.stdout.decode().strip())
report=dict(stage=237,actual_function_sources_sha256={n:hashlib.sha256((R/'camss-source'/n).read_bytes()).hexdigest() for n in ['camss-video.c','camss-vfe.c']},results=results,video_cases=375,buffer_cases=8192,negative_controls_rejected=4,asan_ubsan=True,not_hardware_irq_or_concurrency_validation=True)
(R/'camss-function-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
