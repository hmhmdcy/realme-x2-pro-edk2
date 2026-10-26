"""Extend the existing actual-function harness to metadata survival and partial start failure."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
import host
ROOT=Path(__file__).resolve().parent;D=Path('/home/cy122/x2pro-linux/camera279-isp-kernel/drivers/media/platform/qcom/camss')
common=(D/'camss-vfe.c').read_text()
def function(text,name):
 m=re.search(r'(?:static )?(?:int|void|bool) '+name+r'\(.*?\n\}',text,re.S);assert m,name;return m[0]
parent='--parent' in sys.argv
s=(host.PRIVATE/'stats-tests-private.c').read_text()
s=s.replace('struct camss_video{struct vb2_queue','struct camss_video{enum v4l2_buf_type type;struct vb2_queue')
s=s.replace('struct camss_buffer{u64 addr[2];int id;};','struct camss_buffer{u64 addr[2];int id;char queue;bool sof_valid;};')
s=s.replace('struct vfe_output{struct vfe_line*line;','struct vfe_output{char pending_bufs;struct vfe_line*line;')
s=s.replace('struct vfe_line{struct vfe_device*owner;','struct media_entity{int dummy;};struct media_pad{struct media_entity*entity;};struct v4l2_subdev{struct media_entity entity;};\nstruct vfe_line{struct v4l2_subdev subdev;struct vfe_device*owner;')
s=s.replace('void(*reg_update)(struct vfe_device*,unsigned);','void(*reg_update_clear)(struct vfe_device*,unsigned);void(*reg_update)(struct vfe_device*,unsigned);')
s=s.replace('static int prepare_error;','static int prepare_error;static int prepare_target=-1;')
s=s.replace('return prepare_error?prepare_error:vfe_output_prepare_175(v,o);','return prepare_error&&(prepare_target<0||(int)o->pad==prepare_target)?prepare_error:vfe_output_prepare_175(v,o);')
s=s.replace('starts++;vfe_175_stats_start(v,o);','starts++;if(o->pad==MSM_VFE_PAD_SRC_STATS)vfe_175_stats_start(v,o);')
s=s.replace('stops++;vfe_175_stats_stop(v,o);','stops++;if(o->pad==MSM_VFE_PAD_SRC_STATS)vfe_175_stats_stop(v,o);')
s=s.replace('updates++;vfe_175_stats_update(v,o);','updates++;if(o->pad==MSM_VFE_PAD_SRC_STATS)vfe_175_stats_update(v,o);')
s=s.replace('.reg_update=reg_update};','.reg_update_clear=reg_update,.reg_update=reg_update};')
helper=r'''
static __attribute__((unused)) void pending_head(struct vfe_output*o,struct camss_buffer*b){assert(o->pending_count<8);memmove(o->pending+1,o->pending,o->pending_count*sizeof(o->pending[0]));o->pending[0]=b;o->pending_count++;}
#define list_add(n,h) pending_head(container_of(h,struct vfe_output,pending_bufs),container_of(n,struct camss_buffer,queue))
static struct media_pad *camss_find_sensor_pad(struct media_entity*e){(void)e;return NULL;}
static struct v4l2_subdev *media_entity_to_v4l2_subdev(struct media_entity*e){return container_of(e,struct v4l2_subdev,entity);}
#define v4l2_subdev_call(sd,ops,fn,p) ((void)(sd),(void)(p))
#define VFE_FRAME_DROP_VAL 30
'''
needle='static void reset_trace(void)';i=s.index(needle);s=s[:i]+helper+s[i:]
functions=[]
if 'static void vfe_requeue_active_buffers(' in common:functions.append(function(common,'vfe_requeue_active_buffers'))
if 'static void vfe_stop_one_output(' in common:functions.append(function(common,'vfe_stop_one_output'))
functions += [function(common,n) for n in ['vfe_output_wanted','vfe_enable_output_v2','vfe_disable_output']]
# Helpers must precede the actual metadata callback bodies that may use them.
location=s.index('static int vfe_enable_one_output(')
s=s[:location]+'\n'.join(functions[:len(functions)-3])+'\n'+s[location:]
location=s.index('static void start_output(')
s=s[:location]+'\n'.join(functions[-3:])+'\n'+s[location:]
extra=r'''
 /* Image stop must leave every outstanding stats buffer available on reopen. */
 full->state=VFE_OUTPUT_ON;o->state=VFE_OUTPUT_ON;o->video_out.type=V4L2_BUF_TYPE_META_CAPTURE;
 o->buf[0]=&buffers[0];o->buf[1]=&buffers[1];o->gen2.active_num=2;queue(o,&buffers[2],1);
 o->buf[0]->sof_valid=o->buf[1]->sof_valid=true;
 vfe_disable_output(&l);
 assert(!o->buf[0]&&!o->buf[1]&&!o->gen2.active_num&&o->pending_count==3);
 assert(o->pending[0]==&buffers[0]&&o->pending[1]==&buffers[1]&&o->pending[2]==&buffers[2]);
 assert(!buffers[0].sof_valid&&!buffers[1].sof_valid);
 /* A failed auxiliary output must stop and requeue the primary already started. */
 struct camss_buffer image_buffers[3]={{.id=3},{.id=4},{.id=5}};
 full->state=VFE_OUTPUT_OFF;o->state=VFE_OUTPUT_OFF;full->gen2.active_num=0;full->buf[0]=full->buf[1]=NULL;
 queue(full,image_buffers,3);queue(o,buffers,3);o->video_out.vb2_q.streaming=true;
 unsigned before_stops=stops;prepare_error=-EIO;prepare_target=MSM_VFE_PAD_SRC_STATS;
 assert(vfe_enable_output_v2(&l)==-EIO);
 assert(stops==before_stops+1&&full->state!=VFE_OUTPUT_ON&&!full->gen2.active_num);
 assert(!full->buf[0]&&!full->buf[1]&&full->pending_count==3&&full->pending[0]==&image_buffers[0]&&full->pending[1]==&image_buffers[1]);
 assert(o->pending_count==3&&!o->gen2.active_num);prepare_error=0;prepare_target=-1;
 assert(!vfe_enable_output_v2(&l)&&full->state==VFE_OUTPUT_ON&&o->state==VFE_OUTPUT_ON);
 vfe_disable_output(&l);
'''
if '--partial-only' in sys.argv:
 start=extra.index(' full->state=VFE_OUTPUT_ON;');end=extra.index(' /* A failed auxiliary output');extra=extra[:start]+extra[end:]
needle=' free(p);free(short_disable);';assert needle in s;s=s.replace(needle,extra+needle)
label=('parent-partial' if '--partial-only' in sys.argv else 'parent-restart') if parent else 'fixed-restart'
p=host.PRIVATE/(label+'-metadata-tests-private.c');p.write_text(s);binary=p.with_suffix('')
flags=['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-D__EXPORTED_HEADERS__','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi']
if parent:
 flags.append('-Wno-maybe-uninitialized')
 first=host.PRIVATE/(label+'-first-compile-private.log');current=host.PRIVATE/(label+'-compile-private.log')
 if current.exists() and not first.exists():first.write_bytes(current.read_bytes())
q=subprocess.run(flags+[str(p),'-o',str(binary)],capture_output=True);(host.PRIVATE/(label+'-compile-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary)],capture_output=True,timeout=30);(host.PRIVATE/(label+'-run-private.log')).write_bytes(q.stdout+q.stderr)
if parent:assert q.returncode!=0
else:assert q.returncode==0,q.stderr.decode()
report=dict(stage=295,actual_functions=True,asan_ubsan=True,parent_negative_control=parent,expected_failure_observed=parent,
 image_restart_preserves_all_stats_buffers=not parent,partial_output_start_unwind_verified=not parent,
 all_prior_stats_tests_retained=True,harness_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),exit=q.returncode)
(ROOT/(label+'-metadata-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
