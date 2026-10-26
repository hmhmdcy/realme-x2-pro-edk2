"""Run the actual control callback with I2C/PM fault injection before deployment."""
from pathlib import Path
import hashlib,json,subprocess
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE/'control-test';P.mkdir(mode=0o700)
source=(R/'s5kgw1.c').read_text();a=source.index('static int s5kgw1_set_ctrl(');b=source.index('{',a);depth=1;i=b+1
while depth:depth+=int(source[i]=='{')-int(source[i]=='}');i+=1
callback=source[a:i]
prefix=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <assert.h>
#include <errno.h>
typedef int64_t s64;
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define S5KGW1_EXPOSURE_MIN 6
#define S5KGW1_EXPOSURE_MARGIN 6
#define V4L2_CID_VBLANK 1
#define V4L2_CID_ANALOGUE_GAIN 2
#define V4L2_CID_EXPOSURE 3
#define CCI_REG8(a) ((a)|(1U<<16))
#define CCI_REG16(a) ((a)|(2U<<16))
struct v4l2_ctrl_handler {int unused;};
struct v4l2_ctrl {struct v4l2_ctrl_handler *handler;unsigned int id;int val;int default_value;int maximum;};
struct mode {unsigned int height;};
struct s5kgw1 {void *dev,*regmap;bool removing,power_fault;struct mode *mode;
 struct v4l2_ctrl_handler controls;struct v4l2_ctrl *exposure;};
static unsigned int calls,fail_at;static int refs;static bool active;
static unsigned int addresses[8];static uint64_t values[8];
static int pm_runtime_get_if_in_use(void *d) {(void)d;if(!active)return 0;refs++;return 1;}
static void pm_runtime_put(void *d) {(void)d;assert(refs==1);refs--;}
static int __v4l2_ctrl_modify_range(struct v4l2_ctrl *c,int lo,int hi,int step,int def) {
 assert(lo==6 && step==1 && def>=lo && def<=hi);c->maximum=hi;
 if(c->val>hi)c->val=hi;return 0;
}
static int cci_write(void *m,unsigned int reg,uint64_t value,int *err) {
 (void)m;if(err && *err)return *err;
 assert(calls<8);addresses[calls]=reg;values[calls]=value;calls++;
 int ret=calls==fail_at?-EIO:0;if(err)*err=ret;return ret;
}
'''
main=r'''
int main(void) {
 struct mode mode={.height=3456};unsigned int cases=0;
 for(unsigned int id=1;id<=3;id++) {
  unsigned int total=id==1?4:3;
  for(unsigned int fail=0;fail<=total;fail++) {
   struct s5kgw1 s={.mode=&mode};
   struct v4l2_ctrl exposure={.val=4000,.default_value=3578};s.exposure=&exposure;
   struct v4l2_ctrl ctrl={.handler=&s.controls,.id=id,.val=id==1?128:1024};
   calls=0;fail_at=fail;refs=0;active=true;
   int ret=s5kgw1_set_ctrl(&ctrl);
   assert(ret==(fail?-EIO:0));assert(!refs);
   assert(addresses[0]==CCI_REG8(0x0104) && values[0]==1);
   assert(addresses[calls-1]==CCI_REG8(0x0104) && values[calls-1]==0);
   assert(s.power_fault==(fail==total));
   if(!fail) {
    assert(calls==total);
    if(id==1) {
     assert(exposure.maximum==3578 && exposure.val==3578);
     assert(addresses[1]==CCI_REG16(0x0340) && values[1]==3584);
     assert(addresses[2]==CCI_REG16(0x0202) && values[2]==3578);
    } else assert(addresses[1]==(id==2?CCI_REG16(0x0204):CCI_REG16(0x0202)) && values[1]==1024);
   }
   cases++;
  }
 }
 for(unsigned int state=0;state<3;state++) {
  struct s5kgw1 s={.mode=&mode,.power_fault=state==1,.removing=state==2};
  struct v4l2_ctrl exposure={.val=100,.default_value=3578};s.exposure=&exposure;
  struct v4l2_ctrl ctrl={.handler=&s.controls,.id=2,.val=32};
  calls=0;fail_at=0;refs=0;active=false;
  assert(s5kgw1_set_ctrl(&ctrl)==(state?-EIO:0));assert(!calls && !refs);cases++;
 }
 printf("passed %u\n",cases);return 0;
}
'''
(P/'harness.c').write_text(prefix+callback+main)
q=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-O2','-fsanitize=undefined',str(P/'harness.c'),'-o',str(P/'harness')],capture_output=True)
(P/'build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
q=subprocess.run([str(P/'harness')],capture_output=True);(P/'run-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout==b'passed 16\n','Inspect control harness result'
report=dict(stage=272,actual_control_callback_executed=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),cases=16,
 group_hold_release_attempted_after_every_write_failure=True,release_failure_blocks_future_io=True,
 runtime_pm_references_balanced=True,frame_length_and_exposure_margin_preserved=True,
 no_io_while_suspended_removing_or_faulted=True,undefined_behavior_sanitizer=True,
 phone_unchanged=True,physical_control_latency_and_gain_response_still_unverified=True)
(R/'control-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
