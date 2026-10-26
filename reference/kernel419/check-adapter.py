"""Exercise actual work/ownership code and actual vb2 done-list precedence."""
from pathlib import Path
import ast,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
old=ast.parse((HERE.parent/'kernel393/check-adapter.py').read_text())
strings={n.targets[0].id:ast.literal_eval(n.value) for n in old.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['prefix','core']}
prefix=strings['prefix'];core=strings['core']
prelude='''#include <stdlib.h>
#include <linux/qcom-ipe-a5.h>
#define GFP_KERNEL 0
#define kzalloc(n,f) calloc(1,n)
#define kfree(p) free(p)
#define WRITE_ONCE(x,v) ((x)=(v))
#define current ((void *)1)
#define dprintk(...) ((void)0)
#define list_empty(p) ((p)->empty)
#define wait_event_interruptible(w,c) (-EINTR)
struct mutex;
struct vb2_queue {int waiting_in_dqbuf,streaming,error,last_buffer_dequeued,done_wq;struct {int empty;}done_list;struct mutex *lock;};
static struct vb2_queue source_queue,capture_queue;
'''
prefix=prefix.replace('struct camss_a5{void *dev;};','struct camss_a5{void *dev;struct {void *cpu;}request,image_input,image_output,firmware;struct {struct dma_buf *buffer;}dma_input,dma_output;bool ipe_dma_pending,request_fw_mapped;};')
prefix=prefix.replace('struct vb2_buffer{struct{u32 data_offset;}planes[1];};','struct media_request{int dummy;};\nstruct vb2_buffer{struct{u32 data_offset;}planes[1];struct{struct media_request *req;}req_obj;};')
prefix=prefix.replace('struct work_struct work;struct camss_a5_m2m *dev;','struct work_struct work;int controls;void *control_task;struct qcom_ipe_a5_frame_params *pending_params;bool params_written;struct camss_a5_m2m *dev;')
prefix=prefix.replace('done_state=s;}\nstatic void *v4l2_m2m_get_src_vq','done_state=s;source_queue.done_list.empty=capture_queue.done_list.empty=0;}\nstatic void *v4l2_m2m_get_src_vq')
prefix=prefix.replace('static void *v4l2_m2m_get_src_vq(void *p){return p;}','static void *v4l2_m2m_get_src_vq(void *p){assert(p==active);return &source_queue;}')
prefix=prefix.replace('static void *v4l2_m2m_get_dst_vq(void *p){return p;}','static void *v4l2_m2m_get_dst_vq(void *p){assert(p==active);return &capture_queue;}')
prefix=prefix.replace('static void vb2_queue_error(void *p){assert(p==active);++queue_errors;}','static void vb2_queue_error(void *p){assert(p==&source_queue || p==&capture_queue);((struct vb2_queue *)p)->error=1;++queue_errors;}')
prefix=prefix.replace('++stops;return 0;}','++stops;return scenario==10?-EIO:0;}')
prefix+='''
static int v4l2_ctrl_request_setup(struct media_request *r,void *h){(void)r;(void)h;assert(0);return -EINVAL;}
static void v4l2_ctrl_request_complete(struct media_request *r,void *h){(void)h;assert(!r);}
static int camss_a5_ipe_frame_params_check(const struct qcom_ipe_a5_frame_params *p){(void)p;assert(0);return -EINVAL;}
'''
core=core.replace('++submits;','++submits;\n if(scenario==10){active->dev->a5->request.cpu=(void*)1;active->dev->a5->dma_input.buffer=&in;active->dev->a5->dma_output.buffer=&out;active->dev->a5->ipe_dma_pending=true;++in.refs;++out.refs;}')
core=core.replace('scenario==1?CAMSS_A5_IPE_RESET_REQUIRED','scenario==1 || scenario==10?CAMSS_A5_IPE_RESET_REQUIRED').replace('scenario<=1?-EINVAL','scenario<=1 || scenario==10?-EINVAL')
extra='''
static int frame_params_run(struct ipe_context *ctx,const struct camss_a5_ipe_job *j,const struct qcom_ipe_a5_frame_params *p,enum camss_a5_ipe_result *r){assert(!p);return camss_a5_ipe_run_status(ctx->dev->a5,&ctx->session,j,r);}
'''
source=(P/'camss-icp-a5-m2m.c.proposed').read_text();work=re.search(r'static void device_work\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert work
header='\n'.join(l for l in (P/'camss-icp-a5-ipe.h.proposed').read_text().splitlines() if not l.startswith('#include'))
import importlib.util
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
kernel=storage.mounted_build().parent/'source354'
vb2=(kernel/'drivers/media/common/videobuf2/videobuf2-core.c').read_text();native_wait=re.search(r'static int __vb2_wait_for_done_vb\([^;]+?\n\{.*?^\}\n',vb2,re.S|re.M);assert native_wait
tests=r'''
int main(void){
 unsigned cases=0;
 for(scenario=0;scenario<11;scenario++){
  stops=queue_errors=finishes=done_state=images=put_count=submits=0;memset(&in,0,sizeof(in));memset(&out,0,sizeof(out));
  source_queue=(struct vb2_queue){.streaming=1,.done_list={.empty=1}};capture_queue=source_queue;
  struct camss_a5 a={0};struct camss_a5_m2m d={.a5=&a,.bound=bound};struct ipe_context c={.dev=&d};active=&c;c.fh.m2m_ctx=&c;c.format.plane_fmt[0].sizeimage=460800;
  if(scenario==6)c.aborting=true;
  device_work(&c.work);
  bool failed=scenario<=3 || scenario>=7,reset=scenario==1 || scenario==7 || scenario==10,cancelled=scenario==5 || scenario==6,unsafe=scenario==10;
  assert(d.jobs==1 && d.failed==failed && d.cancelled==cancelled && d.completed==(!failed && !cancelled) && d.direct_completed==d.completed);
  assert(stops==reset && d.fatal==reset && queue_errors==(unsafe?2U:0U));
  assert(finishes==1 && done_state==(failed || cancelled?VB2_BUF_STATE_ERROR:VB2_BUF_STATE_DONE));
  assert(in.refs==unsafe && out.refs==unsafe && !d.hw_lock.locked);
  assert(__vb2_wait_for_done_vb(&source_queue,1)==(unsafe?-EIO:0));
  assert(__vb2_wait_for_done_vb(&capture_queue,1)==(unsafe?-EIO:0));
  if(unsafe){assert(image_transfer_owned(&a));dma_buf_put(&in);dma_buf_put(&out);}
  cases++;
 }
 for(unsigned field=0;field<7;field++){
  struct camss_a5 a={0};a.firmware.cpu=(void*)1;assert(!image_transfer_owned(&a));
  if(field==0)a.ipe_dma_pending=true;if(field==1)a.request_fw_mapped=true;
  if(field==2)a.request.cpu=(void*)1;if(field==3)a.image_input.cpu=(void*)1;if(field==4)a.image_output.cpu=(void*)1;
  if(field==5)a.dma_input.buffer=&in;if(field==6)a.dma_output.buffer=&out;
  assert(image_transfer_owned(&a));cases++;
 }
 struct vb2_queue q={.streaming=1,.done_list={.empty=0}};
 assert(__vb2_wait_for_done_vb(&q,1)==0);q.error=1;assert(__vb2_wait_for_done_vb(&q,1)==-EIO);cases+=2;
 q.error=0;q.done_list.empty=1;assert(__vb2_wait_for_done_vb(&q,1)==-EAGAIN);q.last_buffer_dequeued=1;assert(__vb2_wait_for_done_vb(&q,1)==-EPIPE);cases+=2;
 q.streaming=0;assert(__vb2_wait_for_done_vb(&q,1)==-EINVAL);q.waiting_in_dqbuf=1;assert(__vb2_wait_for_done_vb(&q,1)==-EBUSY);cases+=2;
 printf("ADAPTER_ERROR_MODEL cases=%u passed=1\n",cases);return 0;
}
'''
inc=P/'model-include/linux';inc.mkdir(parents=True,exist_ok=True);(inc/'qcom-ipe-a5.h').write_bytes((HERE.parent/'kernel417/qcom-ipe-a5.h').read_bytes())
model=P/'adapter-model.c';model.write_text(prelude+prefix+'\nstruct camss_a5_ipe_cc;struct camss_a5_ipe_colour;struct camss_a5_ipe_gamma;struct camss_a5_ipe_ltm;\n'+header+'\n'+native_wait[0]+core+extra+(HERE/'error-buffer-tail.c').read_text()+work[0]+tests)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined','-no-pie','-I'+str(inc.parent),str(model),'-o',str(P/'adapter-model')],capture_output=True)
(P/'adapter-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-5000:]
q=subprocess.run([str(P/'adapter-model')],capture_output=True);(P/'adapter-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-5000:]
assert q.stdout==b'ADAPTER_ERROR_MODEL cases=24 passed=1\n'
r=dict(stage=419,actual_adapter_work_function=True,actual_vb2_wait_function=True,asan_ubsan=True,cases=24,
    done_error_buffers_remain_dequeueable_after_proven_quiesce=True,unsafe_transfer_queue_poison_and_extra_image_references_preserved=True,
    global_engine_fatal_gate_and_stop_unchanged=True,all_seven_transfer_ownership_fields_checked=True,
    queued_request_path_verified_separately_on_hardware=True,provider_not_hardware_concurrency_proof=True,passed=True)
(HERE/'adapter-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
