"""Build a standard metadata-output WB lifecycle probe on the verified telephoto path."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel291/samurai-tele-pattern-pix.c').read_text().replace('samurai-k290+','samurai-k292+').replace('"#290 "','"#292 "')
s=s.replace('#include <linux/media.h>','#include <linux/media.h>\n#include <linux/qcom-camss-config.h>')
extra=r'''
static int params_fd=-1;static void *params_map;static size_t params_size;static bool params_streaming;
static enum v4l2_buf_type params_type=V4L2_BUF_TYPE_META_OUTPUT;
struct params_envelope {uint32_t version,data_size;};
_Static_assert(sizeof(struct params_envelope)==sizeof(struct v4l2_isp_buffer),"ISP envelope ABI");
static size_t make_packet(void *memory,unsigned int phase) {
 struct camss_params_wb_gain wb={.header={CAMSS_PARAMS_WB_GAIN,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(wb)},.g_gain=1024,.b_gain=1024,.r_gain=1024};
 if(phase==1||phase==5||phase==6)wb.r_gain=256;
 if(phase==2)wb.b_gain=256;if(phase==3)wb.g_gain=256;
 if(phase==5)wb.header.flags=0;
 if(phase==4){wb.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;wb.header.size=sizeof(wb.header);}
 struct params_envelope envelope={V4L2_ISP_VERSION_V1,wb.header.size};
 memset(memory,0,params_size);memcpy(memory,&envelope,sizeof(envelope));memcpy((char*)memory+sizeof(envelope),&wb,wb.header.size);
 return sizeof(envelope)+wb.header.size;
}
static int queue_params(unsigned int phase,bool corrupt_after) {
 size_t size=make_packet(params_map,phase);
 struct v4l2_buffer b={.index=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP,.bytesused=size};
 if(call(params_fd,VIDIOC_QBUF,&b))return -1;
 /* What was validated and queued must be independent of later userspace writes. */
 if(corrupt_after)memset(params_map,0,params_size);
 printf("PARAM_Q phase=%u bytes=%zu mutate_after_qbuf=%u\n",phase,size,corrupt_after);fflush(stdout);return 0;
}
static int dequeue_params(unsigned int phase) {
 struct pollfd p={.fd=params_fd,.events=POLLOUT};int ready=poll(&p,1,3000);
 if(ready<=0||!(p.revents&POLLOUT)){errno=ETIMEDOUT;return -1;}
 struct v4l2_buffer b={.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP};
 if(call(params_fd,VIDIOC_DQBUF,&b))return -1;
 if(b.index||b.flags&V4L2_BUF_FLAG_ERROR){errno=EIO;return -1;}
 printf("PARAM_DQ phase=%u sequence=%u bytes=%u timestamp_us=%" PRId64 "\n",phase,b.sequence,b.bytesused,(int64_t)b.timestamp.tv_sec*1000000+b.timestamp.tv_usec);fflush(stdout);return 0;
}
static int reject_invalid_params(void) {
 for(unsigned int test=0;test<10;test++){
  size_t size=make_packet(params_map,0);struct params_envelope *e=params_map;
  struct camss_params_wb_gain *w=(void*)((char*)params_map+sizeof(*e));
  switch(test){case 0:e->version=99;break;case 1:e->data_size++;break;case 2:w->header.type=CAMSS_PARAMS_AEC_BHIST;break;case 3:w->header.flags=3;break;case 4:w->g_gain=32768;break;case 5:w->r_sub=1;break;case 6:w->_pad[0]=1;break;case 7:w->header.size=sizeof(w->header);break;case 8:size=sizeof(*e)-1;break;case 9:w->header.flags=4;break;}
  struct v4l2_buffer b={.index=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP,.bytesused=size};
  errno=0;if(!call(params_fd,VIDIOC_QBUF,&b)||errno!=EINVAL){fprintf(stderr,"INVALID_PARAM_UNEXPECTED test=%u errno=%d\n",test,errno);errno=EPROTO;return -1;}
  printf("PARAM_REJECT test=%u errno=%d\n",test,errno);
 }return 0;
}
static int open_params(const struct media_entity_desc *entity) {
 char path[128];if(device_path(entity,false,path,sizeof(path)))return -1;
 params_fd=open(path,O_RDWR|O_NONBLOCK|O_CLOEXEC);if(params_fd<0)return -1;
 struct v4l2_capability caps={0};if(call(params_fd,VIDIOC_QUERYCAP,&caps))return -1;
 if(!(caps.device_caps&V4L2_CAP_META_OUTPUT)){errno=ENOTTY;return -1;}
 struct v4l2_format f={.type=V4L2_BUF_TYPE_META_OUTPUT};if(call(params_fd,VIDIOC_G_FMT,&f))return -1;
 if(f.fmt.meta.dataformat!=V4L2_META_FMT_QCOM_ISP_PARAMS||f.fmt.meta.buffersize<sizeof(struct params_envelope)+sizeof(struct camss_params_wb_gain)||f.fmt.meta.buffersize>4096){errno=ERANGE;return -1;}
 struct v4l2_requestbuffers r={.count=1,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP};if(call(params_fd,VIDIOC_REQBUFS,&r)||r.count!=1)return -1;
 struct v4l2_buffer b={.index=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP};if(call(params_fd,VIDIOC_QUERYBUF,&b)||b.length<f.fmt.meta.buffersize||b.length>65536)return -1;
 params_size=b.length;params_map=mmap(NULL,params_size,PROT_READ|PROT_WRITE,MAP_SHARED,params_fd,b.m.offset);if(params_map==MAP_FAILED){params_map=NULL;return -1;}
 printf("PARAM_NODE path=%s capacity=%u map_size=%zu\n",path,f.fmt.meta.buffersize,params_size);
 if(reject_invalid_params()||queue_params(0,true)||call(params_fd,VIDIOC_STREAMON,&params_type))return -1;params_streaming=true;return 0;
}
'''
needle='struct format_save {';assert s.count(needle)==1;s=s.replace(needle,extra+'\n'+needle)
s=s.replace('capture={0},s={0},p={0};','capture={0},s={0},p={0},parameters={0};')
needle='   if(!strcmp(item.name,"msm_vfe0_video3"))capture=item;';assert needle in s;s=s.replace(needle,needle+'\n   if(!strcmp(item.name,"msm_vfe0_params"))parameters=item;')
s=s.replace('if(c.id&&v.id&&capture.id&&s.id)break;','if(c.id&&v.id&&capture.id&&s.id&&parameters.id)break;')
s=s.replace(' phase="streamon";',' phase="params-open";if(open_params(&parameters))goto cleanup;\n phase="streamon";')
s=s.replace(' puts("STREAMON_OK");fflush(stdout);',' puts("STREAMON_OK");fflush(stdout);if(dequeue_params(0))goto cleanup;')
start=s.index(' for(unsigned frame=0;frame<18;frame++){');end=s.index('  struct pollfd p={.fd=video',start)
s=s[:start]+r'''
 for(unsigned frame=0;frame<81;frame++){
  unsigned int wb_phase=frame/9;
  if(frame&&frame%9==0){
   if(wb_phase<7){if(queue_params(wb_phase,true)||dequeue_params(wb_phase))goto cleanup;}
   else if(wb_phase==7){if(call(params_fd,VIDIOC_STREAMOFF,&params_type))goto cleanup;params_streaming=false;puts("PARAM_STREAMOFF_IMAGE_CONTINUES");}
   else if(wb_phase==8){
    if(call(video,VIDIOC_STREAMOFF,&type))goto cleanup;streaming=false;
    for(unsigned n=0;n<buffers;n++){
     struct v4l2_plane planes[VIDEO_MAX_PLANES]={0};planes[0].length=sizes[n];
     struct v4l2_buffer b={.index=n,.type=type,.memory=V4L2_MEMORY_MMAP,.length=1,.m.planes=planes};
     if(call(video,VIDIOC_QBUF,&b))goto cleanup;
    }
    if(call(video,VIDIOC_STREAMON,&type))goto cleanup;streaming=true;last_sequence=0;last_time=0;puts("IMAGE_REOPEN_WITHOUT_PARAMS");
   }
  }
'''+s[end:]
s=s.replace('if(active_changed<103680||timestamp<=0||(frame&&(buffer.sequence<=last_sequence||timestamp<=last_time)))','if(active_changed<103680||timestamp<=0||((frame%72)&&(buffer.sequence<=last_sequence||timestamp<=last_time)))')
s=s.replace('if(frame==5||frame==11||frame==17){','if(frame%9==8){')
needle=' if(vfe>=0)close(vfe);';assert needle in s
s=s.replace(needle,''' if(params_streaming&&call(params_fd,VIDIOC_STREAMOFF,&params_type)){perror("params STREAMOFF");result=1;}
 if(params_map)munmap(params_map,params_size);
 if(params_fd>=0){struct v4l2_requestbuffers r={.count=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP};if(call(params_fd,VIDIOC_REQBUFS,&r)){perror("params release");result=1;}close(params_fd);}
'''+needle)
# Release the metadata PM reference before restoring links, formats and controls.
block=s[s.index(' if(params_streaming&&'):s.index(' if(vfe>=0)close(vfe);')]
s=s.replace(block,'');needle=' if(settings_changed){';assert needle in s;s=s.replace(needle,block+needle)
source=ROOT/'samurai-wb-params.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'wb-params-aarch64-private';assert not binary.exists()
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'wb-params-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/wrong-kernel-wb-params'],capture_output=True,timeout=10).returncode==3
report=dict(stage=292,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
 qemu_self_test_pass=True,wrong_kernel_guard_passed=True,planned_frames=81,planned_negative_parameter_cases=10,typed_metadata_output=True,
 copied_buffer_mutation_test=True,params_stop_and_image_reopen=True,no_userspace_mmio=True,no_cpu_isp=True,sensor_pattern=2,csid_pattern=0,not_run_on_phone=True)
(ROOT/'wb-params-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
