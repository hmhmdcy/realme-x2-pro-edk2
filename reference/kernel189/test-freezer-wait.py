"""Compile actual FastRPC wait helpers; exercise freezer and real-signal boundaries."""
from pathlib import Path
import hashlib,json,subprocess

k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel189');source=(k/'drivers/misc/fastrpc.c').read_text()
def extract(marker):
 start=source.index(marker);begin=source.index('{',start);depth=1;end=begin+1
 while depth:
  depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return source[start:end]+'\n'
functions=extract('static inline int fastrpc_wait_for_response(')+extract('static int fastrpc_wait_for_completion(')
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define ERESTARTSYS 512
#define HZ 100
#define TASK_INTERRUPTIBLE 1
#define TASK_FREEZABLE 0x2000
typedef unsigned int u32;
struct completion { int identity; };
struct fastrpc_invoke_ctx { struct completion work; bool is_polled; };
static struct fastrpc_invoke_ctx context;
static int replies[32],freezes[32],calls,freeze_calls,poll_calls,kernel_calls;
static int poll_result,kernel_done;
static int wait_for_completion_state(struct completion *work,unsigned int state)
{
 assert(work==&context.work && work->identity==0x73);
 assert(state==(TASK_INTERRUPTIBLE|TASK_FREEZABLE));
 assert(calls<32);return replies[calls++];
}
static int try_to_freeze(void) { assert(freeze_calls<32);return freezes[freeze_calls++]; }
static int wait_for_completion_timeout(struct completion *work,int ticks)
{ assert(work==&context.work && ticks==10*HZ);kernel_calls++;return kernel_done; }
static int poll_for_remote_response(struct fastrpc_invoke_ctx *ctx)
{ assert(ctx==&context);poll_calls++;return poll_result; }
static void reset(void)
{ memset(replies,0,sizeof(replies));memset(freezes,0,sizeof(freezes));
 calls=freeze_calls=poll_calls=kernel_calls=0;context.work.identity=0x73;context.is_polled=false; }
'''
tests=r'''
int main(void)
{
 int checks=0;
 for(int depth=0;depth<16;depth++) {
  reset();for(int j=0;j<depth;j++){replies[j]=-ERESTARTSYS;freezes[j]=1;}
  assert(fastrpc_wait_for_completion(&context,0)==0);
  assert(calls==depth+1 && freeze_calls==depth && !kernel_calls && !poll_calls);
  checks++;
 }
 for(int depth=0;depth<16;depth++) {
  reset();for(int j=0;j<depth;j++){replies[j]=-ERESTARTSYS;freezes[j]=1;}
  replies[depth]=-ERESTARTSYS;freezes[depth]=0;
  assert(fastrpc_wait_for_completion(&context,0)==-ERESTARTSYS);
  assert(calls==depth+1 && freeze_calls==depth+1);checks++;
  reset();for(int j=0;j<depth;j++){replies[j]=-ERESTARTSYS;freezes[j]=1;}
  replies[depth]=-EPIPE;
  assert(fastrpc_wait_for_completion(&context,0)==-EPIPE);
  assert(calls==depth+1 && freeze_calls==depth);checks++;
 }
 reset();kernel_done=0;assert(fastrpc_wait_for_completion(&context,1)==-ETIMEDOUT);
 assert(kernel_calls==1 && !calls && !freeze_calls);checks++;
 reset();kernel_done=1;assert(fastrpc_wait_for_completion(&context,1)==0);
 assert(kernel_calls==1 && !calls && !freeze_calls);checks++;
 reset();context.is_polled=true;poll_result=0;
 assert(fastrpc_wait_for_completion(&context,0)==0 && poll_calls==1 && !calls);checks++;
 reset();context.is_polled=true;poll_result=-EIO;replies[0]=-ERESTARTSYS;freezes[0]=1;
 assert(fastrpc_wait_for_completion(&context,0)==0 && poll_calls==1 && calls==2 && !context.is_polled);checks++;
 printf("checks=%d\n",checks);return 0;
}
'''
code=header+functions+tests
path=private/'freezer-host-test.c';path.write_text(code)
binary=private/'freezer-host-test'
cmd=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path),'-o',str(binary)]
p=subprocess.run(cmd,capture_output=True);(private/'host-compile-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
p=subprocess.run([str(binary)],capture_output=True);(private/'host-run-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
checks=int(p.stdout.decode().strip().split('=')[1]);assert checks==52
mutants={
 'remove_freezer_retry':functions.replace('} while (err == -ERESTARTSYS && try_to_freeze());','} while (0);'),
 'hide_ordinary_signal':functions.replace('return err;','return err == -ERESTARTSYS ? 0 : err;'),
 'kernel_wait_becomes_user_wait':functions.replace('if (kernel) {','if (0 && kernel) {'),
}
results={}
for name,mutant in mutants.items():
 # Keep the helper referenced in the no-retry mutant so compiler warnings cannot be mistaken for runtime detection.
 modified=header+mutant+tests.replace('int checks=0;','int checks=0; (void)try_to_freeze;')
 path=private/(name+'.c');path.write_text(modified);exe=private/name
 build=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-O1',str(path),'-o',str(exe)],capture_output=True)
 (private/(name+'-compile-private.log')).write_bytes(build.stdout+build.stderr);assert build.returncode==0,name
 run=subprocess.run([str(exe)],capture_output=True);(private/(name+'-run-private.log')).write_bytes(run.stdout+run.stderr)
 assert run.returncode!=0,name;results[name]=dict(compiled=True,runtime_rejected=True)
report=dict(stage=189,actual_wait_functions_used=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
 host_scenarios=checks,asan_ubsan_passed=True,negative_mutants=results,
 scheduler_and_freezer_are_host_stubs=True,native_freezer_or_suspend_verified=False)
(ref/'freezer-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
