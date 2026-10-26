from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;source=(P/'camss-icp-a5-boot.c.test').read_text()
body=re.search(r'static void process_message\([^;]+?\n\{.*?^\}\n',source,re.S|re.M).group()
defines='\n'.join(l for l in source.splitlines() if l.startswith('#define '))
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;typedef uint32_t u32;typedef uint64_t u64;
#define module_param_named(...)
#define READ_ONCE(x) (x)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define dev_info(...) ((void)0)
static unsigned completions;
struct camss_a5{void *dev;u8 message[4096],init_data[256];u32 expected,messages,last_type,init_bytes,session_opcode,session_reply_handle,session_header_error,session_payload_status,session_scratch_bytes,protocol_errors,response;u64 session_cookie,session_cookie2,ping_cookie;bool init_done,pc_done,ping_done,session_reply;int error;};
static u32 get_unaligned_le32(const void *p){u32 v;memcpy(&v,p,4);return v;}
static u64 get_unaligned_le64(const void *p){u64 v;memcpy(&v,p,8);return v;}
static void put32(void *p,u32 v){memcpy(p,&v,4);}
static void put64(void *p,u64 v){memcpy(p,&v,8);}
static u32 cmpxchg(u32 *p,u32 old,u32 next){u32 v=*p;if(v==old)*p=next;return v;}
static void complete(u32 *p){(void)p;++completions;}
static void command_failure(struct camss_a5 *a,int e){a->error=e;complete(&a->response);}
'''
tests=r'''
static struct camss_a5 fixture(void){
 struct camss_a5 a={.expected=IPE_ASYNC_INDIRECT_ACK,.session_opcode=IPE_FRAME_PROCESS,.session_cookie=17,.session_cookie2=31};
 put32(a.message,72);put32(a.message+4,IPE_ASYNC_INDIRECT_ACK);put32(a.message+8,IPE_FRAME_PROCESS);put64(a.message+12,17);put64(a.message+20,31);return a;
}
int main(void){
 for(unsigned c=0;c<7;++c){
  struct camss_a5 a=fixture();unsigned bytes=72;completions=0;
  test_drop_frame_ack=1;test_dropped_frame_acks=0;
  if(c==1)put64(a.message+12,99);
  if(c==2)put32(a.message+32,3);
  if(c==3){a.session_opcode=IPE_CONFIG_IO;bytes=56;put32(a.message,56);put32(a.message+8,IPE_CONFIG_IO);}
  if(c==4){bytes=68;put32(a.message,68);}
  if(c==5)a.expected=0;
  if(c==6)test_drop_frame_ack=0;
  process_message(&a,bytes);
  assert(test_dropped_frame_acks==(c==0));assert(test_drop_frame_ack==(c==0 || c==6?0U:1U));
  assert(completions==(c==2 || c==3 || c==4 || c==6));
  if(c==0){assert(a.session_reply && !a.error);process_message(&a,bytes);assert(completions==1 && test_dropped_frame_acks==1);}
 }
 printf("HOOK_MODEL cases=7 passed=1\n");return 0;
}
'''
model=P/'hook-model.c';model.write_text(prefix+defines+'\n'+(P/'test-declarations.c').read_text()+body+tests)
q=subprocess.run(['cc','-DCAMSS_A5_TEST_DROP_FRAME_ACK','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(model),'-o',str(P/'hook-model')],capture_output=True);(P/'hook-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
q=subprocess.run([str(P/'hook-model')],capture_output=True);(P/'hook-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
# Removing the explicit test-only blocks must reproduce the original file.
normal=re.sub(r'#ifdef CAMSS_A5_TEST_DROP_FRAME_ACK\n.*?#endif\n','',source,flags=re.S)
assert normal.replace('#include "camss-icp-a5-ipe.h"\n\n\n','#include "camss-icp-a5-ipe.h"\n\n',1)==(P/'camss-icp-a5-boot.c.before').read_text()
r=dict(stage=394,actual_parser_with_test_guard=True,asan_ubsan=True,cases=7,valid_frame_once_only=True,wrong_token_and_error_and_nonframe_and_bad_size_not_dropped=True,production_without_test_blocks_identical=True,passed=True)
(HERE/'hook-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
