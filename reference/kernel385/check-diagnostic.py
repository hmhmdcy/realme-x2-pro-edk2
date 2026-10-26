"""Exercise actual variable-frame diagnostic memory and observation code."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'diagnostic-model';work.mkdir(exist_ok=True)
s=(HERE/'camss-icp-a5-boot-test.c').read_text()
fragment=s[s.index('/* Temporary synthetic test;'):s.index('static ssize_t image_read(')].rstrip()+'\n'
assert fragment==(HERE/'synthetic-frames.c').read_text()
a=s.index('\ttest_io.input =',s.index('static int __init boot_test_init'));b=s.index('\tret = bus_register_notifier',a)
validation='static int validate(void){u32 stripe_bytes;u64 image_bytes;int ret;\n'+s[a:b]+'return 0;}\n'
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;typedef int32_t s32;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define max(a,b) ((a)>(b)?(a):(b))
#define EXPORT_SYMBOL_GPL(x)
#define GFP_KERNEL 0
struct camss_a5_nv12_layout{u32 width,height,stride,slice_height;bool uv_swap;};
struct camss_a5_ipe_io{struct camss_a5_nv12_layout input,output;u32 output_port;};
struct camss_a5_ipe_partition{u16 fetch_first,fetch_last,output_first,output_last;};
struct camss_a5{u32 id;};struct camss_a5_session{u32 id;};
struct camss_a5_ipe_job{const void *input;void *output;u32 input_bytes,output_bytes,bl_bytes,request_id,max_cores,target_time_ns;};
static void put_unaligned_le16(u16 v,void *p){memcpy(p,&v,2);}
static void put_unaligned_le32(u32 v,void *p){memcpy(p,&v,4);}
static struct camss_a5_ipe_io test_io;
static u32 test_width=640,test_height=480,test_port=8,test_cores=1,test_frames=1;
static bool test_uv_swap;
#define TEST_IMAGE_MAX_BYTES (64U*1024U*1024U)
static u32 test_image_bytes,test_output_bytes,test_input_crc,test_output_crc;
static void *test_output;
static char result[4096];
static unsigned allocs,fail_alloc=99,mode;
static void *kvzalloc(size_t n,int flags){(void)flags;if(allocs++==fail_alloc)return NULL;return calloc(1,n);}
static void kvfree(void *p){free(p);}
static u32 crc32_le(u32 crc,const u8 *data,size_t n){for(size_t i=0;i<n;i++){crc^=data[i];for(unsigned j=0;j<8;j++)crc=(crc>>1)^((crc&1)?0xedb88320:0);}return crc;}
static int scnprintf(char *buf,size_t n,const char *fmt,...){va_list ap;va_start(ap,fmt);int r=vsnprintf(buf,n,fmt,ap);va_end(ap);return r<0?0:(size_t)r>=n?(n?(int)n-1:0):r;}
static int camss_a5_ipe_run(struct camss_a5 *a,struct camss_a5_session *s,const struct camss_a5_ipe_job *j){
 assert(a->id==1 && s->id==((j->request_id-1)&1) && j->max_cores==test_cores && j->bl_bytes==524288 && j->input_bytes==test_image_bytes && j->output_bytes==test_image_bytes);
 if(mode==2)return -EIO;memcpy(j->output,j->input,test_image_bytes);if(mode==1)((u8*)j->output)[0]^=1;return 0;
}
'''
main=r'''
int main(void){struct camss_a5 a={1};struct camss_a5_session sessions[2]={{0},{1}};
 for(unsigned bad=0;bad<8;bad++){test_width=640;test_height=480;test_port=8;test_cores=1;test_frames=1;
 switch(bad){case 0:test_frames=0;break;case 1:test_frames=9;break;case 2:test_width=0xffffffff;break;case 3:test_height=127;break;case 4:test_port=7;break;case 5:test_cores=3;break;case 6:test_width=test_height=8192;break;case 7:test_width=641;break;}
 assert(validate()==(bad==6?-E2BIG:-EINVAL));}
 test_width=128;test_height=128;test_port=9;test_cores=2;test_frames=8;test_uv_swap=true;assert(!validate());
 u32 seen[8];for(u32 seq=0;seq<8;seq++){assert(!test_frame(&a,&sessions[seq&1],seq));assert(test_frames_done==seq+1 && test_output_bytes==test_image_bytes && !frame_observations[seq].y_different && !frame_observations[seq].uv_abs_error);assert(((u8*)test_output)[0]==16+(seq*5%28)*8);seen[seq]=test_output_crc;for(unsigned j=0;j<seq;j++)assert(seen[j]!=seen[seq]);}
 strcpy(result,"{\"diagnostic_model\":true");append_frame_results();puts(result);assert(strlen(result)<4095);
 for(unsigned failure=0;failure<4;failure++){test_frames_done=0;memset(frame_observations,0,sizeof(frame_observations));mode=failure==0?1:failure==1?2:0;allocs=0;fail_alloc=failure<2?99:failure-2;
 int ret=test_frame(&a,&sessions[0],0);assert(ret==(failure==0?0:failure==1?-EIO:-ENOMEM));assert(test_frames_done==(failure==0));if(failure==0)assert(frame_observations[0].y_different==1);else assert(!test_output_bytes);}
 kvfree(test_output);return 0;}
'''
production=(HERE.parent/'kernel383/bypass-partitions.c').read_text()+'\n'+(HERE.parent/'kernel384/bypass-striping.c').read_text()
(work/'probe.c').write_text(prefix+production+fragment+validation+main)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(work/'probe')],capture_output=True);(work/'run-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
result=json.loads(q.stdout);assert len(result['frame_results'])==8 and all(r['non_rt']==bool(i&1) for i,r in enumerate(result['frame_results']))
report=dict(stage=385,actual_diagnostic_parameter_validation_pattern_and_frame_observation_bodies=True,asan_ubsan=True,
 eight_changing_frames_and_alternating_session_arguments=True,valid_json_without_truncation_at_eight_frames=True,
 allocation_failures_and_submission_error_do_not_publish_incomplete_frame=True,luma_corruption_is_observed=True,
 invalid_and_oversize_diagnostic_parameters_rejected_before_allocation=True,hardware_operations=False,passed=True)
(HERE/'diagnostic-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
