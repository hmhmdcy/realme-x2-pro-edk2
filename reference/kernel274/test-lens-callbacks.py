"""Compile actual candidate callbacks and inject I2C, power, and PM failures."""
from pathlib import Path
import hashlib,json,subprocess
import host
R=Path(__file__).resolve().parent;source=(R/'lc898219xi.c').read_text()
def block(start):
 a=source.index(start);b=source.index('{',a);depth=1;i=b+1
 while depth:
  depth+=(source[i]=='{')-(source[i]=='}');i+=1
 return source[a:i]+'\n'
names=['static inline struct lc898219xi *to_lc898219xi', 'static int lc898219xi_write(', 'static int lc898219xi_set_position(',
 'static int lc898219xi_set_ctrl(', 'static int lc898219xi_power_off(', 'static int lc898219xi_runtime_resume(', 'static int lc898219xi_runtime_suspend(']
code=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8; typedef uint16_t u16; typedef int64_t s64; typedef int64_t ktime_t;
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
#define LC898219XI_MAX_FOCUS 1023
#define LC898219XI_POSITION 0x84
#define LC898219XI_INITIALIZE 0xe0
#define LC898219XI_OFF_US 100000
#define LC898219XI_START_US 5000
#define V4L2_CID_FOCUS_ABSOLUTE 1
struct mutex { int held; };
struct device { void *data; };
struct i2c_client { int unused; };
struct regulator { int refs; };
struct v4l2_subdev { struct device *dev; struct i2c_client *client; };
struct v4l2_ctrl_handler { struct mutex *lock; };
struct v4l2_ctrl { struct v4l2_ctrl_handler *handler; int id; int val; };
static int64_t clock_us, enabled_at;
static int enable_fail,disable_fail,write_fail_at,write_failure,write_count,pm_active,pm_refs,errors;
static uint8_t writes[64][3];static int sizes[64];
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;}
static ktime_t ktime_get(void){return clock_us;}
static s64 ktime_us_delta(ktime_t a,ktime_t b){return a-b;}
static void usleep_range(s64 lo,s64 hi){assert(lo>=0 && hi>=lo);clock_us+=lo;}
static void *dev_get_drvdata(struct device *d){return d->data;}
static struct i2c_client *v4l2_get_subdevdata(struct v4l2_subdev *sd){return sd->client;}
static int regulator_enable(struct regulator *r){if(enable_fail){--enable_fail;return -EIO;}assert(r->refs==0);++r->refs;enabled_at=clock_us;return 0;}
static int regulator_disable(struct regulator *r){if(disable_fail){--disable_fail;return -EIO;}assert(r->refs==1);--r->refs;return 0;}
static int i2c_master_send(struct i2c_client *c,const u8 *b,int n){(void)c;assert(write_count<64 && n<=3);memcpy(writes[write_count],b,n);sizes[write_count]=n;++write_count;return write_count==write_fail_at?write_failure:n;}
static int pm_runtime_get_if_in_use(struct device *d){(void)d;if(pm_active>0)++pm_refs;return pm_active;}
static void pm_runtime_put(struct device *d){(void)d;assert(pm_refs>0);--pm_refs;}
#define dev_err(dev,...) do{(void)(dev);++errors;}while(0)
'''
code+=block('struct lc898219xi {')+';\n'
for name in names:code+=block(name)
code+=r'''
static struct lc898219xi lens;static struct device dev;static struct i2c_client client;static struct regulator vdd;
static void reset(void){memset(&lens,0,sizeof(lens));memset(&vdd,0,sizeof(vdd));memset(writes,0,sizeof(writes));clock_us=enabled_at=0;enable_fail=disable_fail=write_fail_at=write_failure=write_count=pm_active=pm_refs=errors=0;dev.data=&lens.sd;lens.sd.dev=&dev;lens.sd.client=&client;lens.vdd=&vdd;lens.ctrls.lock=&lens.lock;}
static int control(int id,int value){struct v4l2_ctrl c={&lens.ctrls,id,value};int ret;mutex_lock(&lens.lock);ret=lc898219xi_set_ctrl(&c);mutex_unlock(&lens.lock);return ret;}
int main(void){int cases=0;int64_t off;
 reset();assert(!lc898219xi_runtime_resume(&dev));assert(vdd.refs==1 && lens.supply_enabled && enabled_at>=100000);assert(write_count==1 && sizes[0]==2 && writes[0][0]==0xe0 && writes[0][1]==1);assert(!lens.target_valid && !lens.lock.held);assert(!lc898219xi_runtime_suspend(&dev));assert(!vdd.refs && !lens.supply_enabled);++cases;
 reset();assert(!control(1,400));assert(lens.target_valid && lens.target==400 && !write_count);assert(!lc898219xi_runtime_resume(&dev));assert(write_count==2 && sizes[1]==3 && writes[1][0]==0x84 && writes[1][1]==1 && writes[1][2]==0x90);++cases;
 off=clock_us;assert(!lc898219xi_runtime_suspend(&dev));clock_us+=10000;assert(!lc898219xi_runtime_resume(&dev));assert(enabled_at-off>=100000 && vdd.refs==1);++cases;
 reset();enable_fail=1;assert(lc898219xi_runtime_resume(&dev)==-EIO);assert(!vdd.refs && !lens.supply_enabled && !write_count && !lens.lock.held);++cases;
 reset();write_fail_at=1;write_failure=-ENXIO;assert(lc898219xi_runtime_resume(&dev)==-ENXIO);assert(!vdd.refs && !lens.supply_enabled);++cases;
 reset();write_fail_at=1;write_failure=1;assert(lc898219xi_runtime_resume(&dev)==-EIO);assert(!vdd.refs && !lens.supply_enabled);++cases;
 reset();assert(!control(1,208));write_fail_at=2;write_failure=2;assert(lc898219xi_runtime_resume(&dev)==-EIO);assert(write_count==2 && !vdd.refs && !lens.supply_enabled);++cases;
 reset();write_fail_at=1;write_failure=-ENXIO;disable_fail=1;assert(lc898219xi_runtime_resume(&dev)==-ENXIO);assert(vdd.refs==1 && lens.supply_enabled && errors==1);write_fail_at=0;assert(!lc898219xi_runtime_resume(&dev));assert(vdd.refs==1 && lens.supply_enabled);++cases;
 reset();assert(!lc898219xi_runtime_resume(&dev));off=lens.last_off;disable_fail=1;assert(lc898219xi_runtime_suspend(&dev)==-EIO);assert(vdd.refs==1 && lens.supply_enabled && lens.last_off==off);assert(!lc898219xi_runtime_suspend(&dev));assert(!vdd.refs && !lens.supply_enabled);++cases;
 reset();assert(!lc898219xi_runtime_resume(&dev));pm_active=1;pm_refs=1;assert(!control(1,880));assert(lens.target==880 && lens.target_valid && pm_refs==1 && writes[1][1]==3 && writes[1][2]==0x70);write_fail_at=3;write_failure=-EIO;assert(control(1,400)==-EIO);assert(lens.target==880 && pm_refs==1);++cases;
 reset();pm_active=-EINVAL;assert(control(1,208)==-EINVAL);assert(!lens.target_valid && !write_count && !pm_refs);++cases;
 reset();assert(control(99,208)==-EINVAL);assert(!lens.target_valid && !write_count && !pm_refs);++cases;
 reset();assert(!lc898219xi_runtime_suspend(&dev));assert(!lc898219xi_runtime_suspend(&dev));assert(!vdd.refs && !lens.supply_enabled);++cases;
 printf("{\"actual_callback_cases\":%d,\"passed\":true}\n",cases);return 0;
}
'''
out=host.PRIVATE/'lens-callback-host-r1';out.mkdir(mode=0o700);(out/'test.c').write_text(code)
q=subprocess.run(['cc','-std=gnu11','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all',str(out/'test.c'),'-o',str(out/'test')],capture_output=True)
(out/'compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
q=subprocess.run([str(out/'test')],capture_output=True);(out/'run-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
d=json.loads(q.stdout);d.update(stage=274,source_sha256=hashlib.sha256(source.encode()).hexdigest(),actual_candidate_callbacks_compiled=True,ubsan=True,physical_i2c_and_pm_faults_not_injected=True)
(R/'lens-callback-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
