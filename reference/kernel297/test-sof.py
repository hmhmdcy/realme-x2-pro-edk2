"""Exercise extracted IRQ/queue/completion functions, including late and missing SOFs."""
from pathlib import Path
import hashlib, json, re, resource, subprocess, sys
import host
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
HERE = Path(__file__).resolve().parent
D = Path('/home/cy122/x2pro-linux/camera279-isp-kernel/drivers/media/platform/qcom/camss')
parent = '--parent' in sys.argv
source_dir = host.PRIVATE / 'source-before297' if parent else D
core = (source_dir / 'camss-vfe.c').read_text()
backend = (source_dir / 'camss-vfe-17x.c').read_text()
def function(text, name):
    m = re.search(r'(?:static )?(?:int|void|u32|struct (?:camss_buffer|vfe_output) \*)\s*' + name + r'\(.*?\n\}', text, re.S)
    assert m, name
    return m[0]
prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32; typedef uint64_t u64; typedef uint8_t u8;
#define BIT(n) (1U << (n))
#define CAMSS_8150 8150
#define CAMSS_INIT_BUF_COUNT 2
#define MSM_VFE_NUM_OUTPUTS 5
#define MSM_VFE_PAD_SRC_STATS 4
#define MSM_VFE_PAD_SINK_PARAMS 5
#define VFE_LINE_NONE -1
#define VFE_OUTPUT_ON 2
#define V4L2_EVENT_FRAME_SYNC 4
enum vfe_line_id { VFE_LINE_PIX };
enum vb2_buffer_state { VB2_BUF_STATE_DONE = 2, VB2_BUF_STATE_ERROR = 3 };
struct vb2_buffer { u64 timestamp; unsigned done, state; };
struct camss_buffer { struct {struct vb2_buffer vb2_buf; u32 sequence;} vb; bool sof_valid; void *meta; u64 addr[2]; };
struct camss_video { int unused; };
struct vfe_device; struct vfe_line; struct vfe_output;
struct vfe_hw_ops {
 void (*vfe_output_update)(struct vfe_device *,struct vfe_output *,struct camss_buffer *);
 void (*vfe_wm_update)(struct vfe_device *,u8,u32,struct vfe_line *);
 void (*vfe_params_apply)(struct vfe_device *,struct vfe_line *,void *);
 void (*reg_update)(struct vfe_device *,unsigned);
};
struct vfe_output {
 unsigned pad,wm_num,state,comp_group,sequence,sof_sequence;
 struct {unsigned bus_client;} wm[2]; struct camss_buffer *buf[2], *pending[32]; unsigned pending_count;
 struct {unsigned active_num;} gen2; struct vfe_line *line; struct camss_video video_out;
};
struct vfe_line { struct vfe_device *owner; bool is_pix; unsigned id,num_outputs; struct vfe_output output[5]; int subdev; };
struct camss { struct {int version;} *res; void *dev; };
struct vfe_device { struct camss *camss; struct {const struct vfe_hw_ops *hw_ops;} *res; struct vfe_line line[1]; int wm_output_map[1],output_lock; };
struct camss_buf_done_info { u32 status; };
struct v4l2_event { unsigned type; union {struct {u32 frame_sequence;} frame_sync;} u; };
static unsigned locked,notifications,last_event,errors,updates,reg_updates,applied,stats_filled;
static u64 now;
#define spin_lock_irqsave(l,f) do {(void)(l); (f)=0; assert(!locked); locked=1;} while(0)
#define spin_unlock_irqrestore(l,f) do {(void)(l); (void)(f); assert(locked); locked=0;} while(0)
#define dev_err_ratelimited(...) ((void)errors++)
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
static u64 ktime_get_ns(void) { return ++now; }
static struct vfe_device *to_vfe(struct vfe_line *l) { return l->owner; }
static void vb2_buffer_done(struct vb2_buffer *b,enum vb2_buffer_state s) {assert(!locked);b->done++;b->state=s;}
static void v4l2_subdev_notify_event(int *s,struct v4l2_event *e) {(void)s;assert(!locked);notifications++;last_event=e->u.frame_sync.frame_sequence;}
static struct camss_buffer *vfe_buf_get_pending(struct vfe_output *o) {
 if(!o->pending_count)return NULL;struct camss_buffer *b=o->pending[0];
 memmove(o->pending,o->pending+1,--o->pending_count*sizeof(o->pending[0]));return b;
}
static void vfe_buf_add_pending(struct vfe_output *o,struct camss_buffer *b) {assert(o->pending_count<32);o->pending[o->pending_count++]=b;}
static void vfe_stats_fill(struct vfe_device *v,struct vfe_output *o,struct camss_buffer *b) {(void)v;(void)o;(void)b;stats_filled++;}
static void update(struct vfe_device *v,struct vfe_output *o,struct camss_buffer *b) {(void)v;(void)o;(void)b;updates++;}
static void reg_update(struct vfe_device *v,unsigned l) {(void)v;(void)l;reg_updates++;}
static void apply(struct vfe_device *v,struct vfe_line *l,void *p) {(void)v;(void)l;(void)p;applied++;}
'''
functions = '\n\n'.join([function(core, 'vfe_params_output'), function(core, 'vfe_params_apply_next'),
                            function(core, 'vfe_output_done'), function(core, 'vfe_buf_done'),
                            function(core, 'vfe_queue_buffer_v2'), function(backend, 'vfe_isr_sof')])
tests = r'''
static struct vfe_device v;
static struct camss c;
static typeof(*c.res) cr;
static typeof(*v.res) vr;
static const struct vfe_hw_ops ops={.vfe_output_update=update,.reg_update=reg_update,.vfe_params_apply=apply};
static struct camss_buffer image[8],stats[8],params;
static struct vfe_output *im,*st,*pa;
static void setup(void) {
 memset(&v,0,sizeof(v));memset(image,0,sizeof(image));memset(stats,0,sizeof(stats));memset(&params,0,sizeof(params));
 errors=notifications=updates=reg_updates=applied=stats_filled=locked=0;
 cr.version=CAMSS_8150;c.res=&cr;vr.hw_ops=&ops;v.res=&vr;v.camss=&c;
 struct vfe_line *l=&v.line[0];l->owner=&v;l->is_pix=true;l->num_outputs=3;
 for(unsigned i=0;i<3;i++) {l->output[i].line=l;l->output[i].state=VFE_OUTPUT_ON;}
 im=&l->output[0];pa=&l->output[1];st=&l->output[2];
 im->wm_num=2;st->wm_num=1;st->pad=MSM_VFE_PAD_SRC_STATS;st->comp_group=1;pa->pad=MSM_VFE_PAD_SINK_PARAMS;pa->state=0;
 im->buf[0]=&image[0];im->buf[1]=&image[1];im->gen2.active_num=2;
 st->buf[0]=&stats[0];st->buf[1]=&stats[1];st->gen2.active_num=2;
}
static void done(unsigned mask) {struct camss_buf_done_info info={.status=mask};vfe_buf_done(&v,0,&info);}
static void queue(struct vfe_output *o,struct camss_buffer *b) {assert(!vfe_queue_buffer_v2(&o->video_out,b));}
static void normal(void) {
 setup();vfe_isr_sof(&v,0);assert(image[0].sof_valid&&stats[0].sof_valid);
 assert(image[0].vb.sequence==0&&stats[0].vb.sequence==0);done(3);
 assert(image[0].vb.vb2_buf.state==VB2_BUF_STATE_DONE&&stats[0].vb.vb2_buf.state==VB2_BUF_STATE_DONE);
 assert(im->sequence==1&&st->sequence==1&&notifications==1&&last_event==0);
}
static void coalesced(void) {
 setup();vfe_isr_sof(&v,0);vfe_isr_sof(&v,0);
 assert(image[0].vb.sequence==0&&stats[0].vb.sequence==0);
 assert(image[1].vb.sequence==1&&stats[1].vb.sequence==1);
 done(1);done(2);assert(image[0].vb.sequence==0&&stats[0].vb.sequence==0);
 done(3);assert(image[1].vb.sequence==1&&stats[1].vb.sequence==1);
 assert(!errors);
}
static void late_and_gap(void) {
 setup();im->sof_sequence=42;im->sequence=40;st->sequence=0;
 vfe_isr_sof(&v,0);done(3);assert(image[0].vb.sequence==42&&stats[0].vb.sequence==42);
 vfe_isr_sof(&v,0);done(3);assert(image[1].vb.sequence==43&&stats[1].vb.sequence==43);
 for(unsigned i=0;i<4;i++){vfe_isr_sof(&v,0);done(2);}
 assert(im->sof_sequence==48&&st->gen2.active_num==0);
 queue(st,&stats[2]);vfe_isr_sof(&v,0);done(2);
 assert(stats[2].vb.sequence==48&&stats[2].vb.vb2_buf.state==VB2_BUF_STATE_DONE);
 assert(st->sequence==49);
}
static void missing_sof(void) {
 setup();done(2);assert(stats[0].vb.vb2_buf.state==VB2_BUF_STATE_ERROR&&errors==1);
 assert(!stats[0].sof_valid);assert(!image[0].vb.vb2_buf.done);
}
static void params_after_new_sof(void) {
 setup();queue(pa,&params);vfe_isr_sof(&v,0);vfe_isr_sof(&v,0);done(1);
 assert(params.vb.vb2_buf.done==1&&params.vb.sequence==2&&applied==1);
}
static void guard_and_wrap(void) {
 setup();cr.version=780;vfe_isr_sof(&v,0);assert(!notifications);done(3);
 assert(image[0].vb.vb2_buf.state==VB2_BUF_STATE_DONE&&stats[0].vb.vb2_buf.state==VB2_BUF_STATE_DONE);
 setup();im->sof_sequence=UINT32_MAX;vfe_isr_sof(&v,0);done(3);
 assert(image[0].vb.sequence==UINT32_MAX&&stats[0].vb.sequence==UINT32_MAX&&im->sequence==0);
 vfe_isr_sof(&v,0);done(3);assert(!image[1].vb.sequence&&!stats[1].vb.sequence);
 setup();im->state=0;vfe_isr_sof(&v,0);assert(!notifications&&!stats[0].sof_valid);
}
static void repeated_requeue(void) {
 for(unsigned trial=0;trial<1000;trial++) {
  setup();im->sof_sequence=trial*31;unsigned held=0;
  for(unsigned frame=0;frame<6;frame++) {
   if(frame>=2)queue(im,&image[frame]);
   if(frame==5){queue(st,&stats[2]);queue(st,&stats[3]);}
   vfe_isr_sof(&v,0);struct camss_buffer *ib=im->buf[0],*sb=st->buf[0];
   done(3);assert(ib&&ib->vb.sequence==trial*31+frame&&ib->vb.vb2_buf.state==VB2_BUF_STATE_DONE);
   if(sb){assert(sb->vb.sequence==ib->vb.sequence&&sb->vb.vb2_buf.state==VB2_BUF_STATE_DONE);held++;}
  }
  assert(held==3&&!errors);
 }
}
int main(void) {normal();coalesced();late_and_gap();missing_sof();params_after_new_sof();guard_and_wrap();repeated_requeue();puts("SOF_TAG_CONTRACTS_PASSED");}
'''
tag = 'parent' if parent else 'fixed'
source = host.PRIVATE / f'sof-{tag}-host-private.c'
source.write_text(prefix + functions + tests)
binary = host.PRIVATE / f'sof-{tag}-host-private'
q = subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(source), '-o', str(binary)], capture_output=True)
(host.PRIVATE / f'sof-{tag}-compile-private.log').write_bytes(q.stdout + q.stderr)
assert q.returncode == 0, (q.stdout + q.stderr).decode()
q = subprocess.run([str(binary)], capture_output=True)
(host.PRIVATE / f'sof-{tag}-run-private.log').write_bytes(q.stdout + q.stderr)
if parent:
    assert q.returncode != 0 and b'Assertion' in q.stderr
else:
    assert q.returncode == 0 and b'SOF_TAG_CONTRACTS_PASSED' in q.stdout, (q.stdout + q.stderr).decode()
report = dict(stage=297, parent_negative_control=parent, expected_outcome_observed=True, exit_code=q.returncode,
              actual_irq_queue_and_completion_functions=True, harness_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              normal_and_late_shared_sequence=not parent, missing_sof_reported_error=not parent,
              adjacent_sof_before_done_preserves_old_tag=not parent, statistics_starvation_gap_preserved=not parent,
              parameters_after_new_sof_report_future_sequence=not parent, other_version_guard_and_u32_wrap=not parent,
              repeated_requeue_trials=0 if parent else 1000, asan_ubsan=True,
              multiple_unobserved_sof_edges_not_tested=True, physical_validation_pending=True)
(HERE / f'sof-{tag}-host-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
