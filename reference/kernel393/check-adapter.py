"""Run the actual adapter work function against deterministic core outcomes."""
from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(P/'camss-icp-a5-m2m.c.proposed').read_text();m=re.search(r'static void device_work\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert m
header='\n'.join(l for l in (P/'camss-icp-a5-ipe.h.proposed').read_text().splitlines() if not l.startswith('#include'))
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <linux/videodev2.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;
struct camss_a5{void *dev;};struct camss_a5_session{int dummy;};struct camss_a5_ipe_io;
struct dma_buf{unsigned refs;};struct work_struct{int dummy;};struct mutex{bool locked;};
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define READ_ONCE(x) (x)
#define IS_ERR(x) ((uintptr_t)(x)>=(uintptr_t)-4095)
#define PTR_ERR(x) ((int)(intptr_t)(x))
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define dev_info(...) ((void)0)
#define VB2_BUF_STATE_ERROR 1
#define VB2_BUF_STATE_DONE 2
struct vb2_buffer{struct{u32 data_offset;}planes[1];};
struct vb2_v4l2_buffer{struct vb2_buffer vb2_buf;u32 sequence;};
struct camss_a5_m2m{struct camss_a5 *a5;struct mutex hw_lock;void *scheduler;bool fatal;int first_error;bool(*bound)(void*);u64 jobs,completed,direct_completed,cancelled,failed;};
struct ipe_context{struct work_struct work;struct camss_a5_m2m *dev;struct{void *m2m_ctx;}fh;struct camss_a5_session session;struct v4l2_pix_format_mplane format;u32 sequence;bool aborting;};
static unsigned scenario,stops,queue_errors,finishes,done_state,images,put_count,submits;
static struct ipe_context *active;
static struct vb2_v4l2_buffer src,dst;
static struct dma_buf in,out;
static void mutex_lock(struct mutex *m){assert(!m->locked);m->locked=true;}
static void mutex_unlock(struct mutex *m){assert(m->locked);m->locked=false;}
static bool bound(void *d){(void)d;return true;}
static struct vb2_v4l2_buffer *v4l2_m2m_next_src_buf(void *p){assert(p==active);return &src;}
static struct vb2_v4l2_buffer *v4l2_m2m_next_dst_buf(void *p){assert(p==active);return &dst;}
static struct vb2_v4l2_buffer *v4l2_m2m_src_buf_remove(void *p){return v4l2_m2m_next_src_buf(p);}
static struct vb2_v4l2_buffer *v4l2_m2m_dst_buf_remove(void *p){return v4l2_m2m_next_dst_buf(p);}
static void v4l2_m2m_buf_done(struct vb2_v4l2_buffer *b,unsigned s){(void)b;done_state=s;}
static void v4l2_m2m_job_finish(void *d,void *p){(void)d;assert(p==active);++finishes;}
static void v4l2_m2m_buf_done_and_job_finish(void *d,void *p,unsigned s){v4l2_m2m_job_finish(d,p);done_state=s;}
static void *v4l2_m2m_get_src_vq(void *p){return p;}
static void *v4l2_m2m_get_dst_vq(void *p){return p;}
static void vb2_queue_error(void *p){assert(p==active);++queue_errors;}
static void v4l2_m2m_buf_copy_metadata(struct vb2_v4l2_buffer *s,struct vb2_v4l2_buffer *d){assert(s==&src && d==&dst);}
static struct dma_buf *image_buffer(struct vb2_buffer *b){
 ++images;if(scenario==8 && b==&src.vb2_buf)return ERR_PTR(-ENOMEM);
 if(scenario==9 && b==&dst.vb2_buf)return ERR_PTR(-ENOMEM);
 struct dma_buf *d=b==&src.vb2_buf?&in:&out;++d->refs;return d;
}
static void dma_buf_put(struct dma_buf *d){assert(d->refs);--d->refs;++put_count;}
static int ensure_session(struct ipe_context *c){assert(c==active);return scenario==7?-ENOMEM:0;}
static int stop_backend(struct camss_a5_m2m *d){assert(d==active->dev && d->fatal);++stops;return 0;}
'''
core=r'''
int camss_a5_ipe_run_status(struct camss_a5 *a,struct camss_a5_session *s,const struct camss_a5_ipe_job *j,enum camss_a5_ipe_result *r){
 assert(a==active->dev->a5 && s==&active->session && j->input_dma==&in && j->output_dma==&out && a && active->dev->hw_lock.locked);++submits;
 if(scenario==5)active->aborting=true;
 *r=scenario==0 || scenario==2 || scenario==3?CAMSS_A5_IPE_REJECTED:scenario==1?CAMSS_A5_IPE_RESET_REQUIRED:CAMSS_A5_IPE_COMPLETE;
 return scenario<=1?-EINVAL:scenario==2?-ENOMEM:scenario==3?-ETIMEDOUT:0;
}
'''
tests=r'''
int main(void){
 for(scenario=0;scenario<10;++scenario){
  stops=queue_errors=finishes=done_state=images=put_count=submits=0;memset(&in,0,sizeof(in));memset(&out,0,sizeof(out));
  struct camss_a5 a={0};struct camss_a5_m2m d={.a5=&a,.bound=bound};struct ipe_context c={.dev=&d};active=&c;c.fh.m2m_ctx=&c;c.format.plane_fmt[0].sizeimage=460800;
  if(scenario==6)c.aborting=true;
  device_work(&c.work);
  bool failed=scenario<=3 || scenario>=7,reset=scenario==1 || scenario==7,cancelled=scenario==5 || scenario==6;
  assert(d.jobs==1 && d.failed==failed && d.cancelled==cancelled && d.completed==(!failed && !cancelled) && d.direct_completed==d.completed);
  assert(stops==reset && d.fatal==reset && queue_errors==(failed?2U:0U));
  assert(finishes==1 && done_state==(failed || cancelled?VB2_BUF_STATE_ERROR:VB2_BUF_STATE_DONE));
  assert(!in.refs && !out.refs && !d.hw_lock.locked && put_count==(scenario==6 || scenario==8?0U:scenario==9?1U:2U));
 }
 printf("ADAPTER_MODEL cases=10 passed=1\n");return 0;
}
'''
model=P/'adapter-model.c';model.write_text(prefix+header+core+m.group()+tests)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(model),'-o',str(P/'adapter-model')],capture_output=True)
(P/'adapter-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
q=subprocess.run([str(P/'adapter-model')],capture_output=True);(P/'adapter-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
r=dict(stage=393,actual_device_work_function=True,asan_ubsan=True,cases=10,same_errno_result_class_changes_recovery_scope=True,preflight_timeout_not_globally_fatal=True,startup_failure_still_globally_fatal=True,buffer_put_and_scheduler_finish_balanced=True,cancel_before_and_after_core_kept=True,hardware_concurrency_not_claimed=True,passed=True)
(HERE/'adapter-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
