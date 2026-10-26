"""Exercise the actual old/new C functions with deterministic MMIO/time stubs."""
from pathlib import Path
import subprocess,json
root=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel118')
out=Path('/mnt/e/edk2-samurai-out/kernel118')
def function(stage,name):
    t=Path(f'/home/cy122/pmos-samurai-kernel{stage}/kernel/drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c').read_text()
    start=t.index('static u32 dpu_hw_ctl_poll_reset_status(')
    end=t.index('\n}',start)+2
    return t[start:end].replace('dpu_hw_ctl_poll_reset_status(',name+'(')
harness=r'''
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
typedef uint32_t u32;
typedef int64_t ktime_t;
struct dpu_hw_blk_reg_map { int unused; };
struct dpu_hw_ctl { struct dpu_hw_blk_reg_map hw; };
static int64_t now, clear_at, wake_step;
static int reads;
#define BIT(n) (1U << (n))
#define CTL_SW_RESET 0
static u32 read_reset(struct dpu_hw_blk_reg_map *c, int reg) {
    (void)c; (void)reg; ++reads;
    return now >= clear_at ? 0 : 1;
}
#define DPU_REG_READ(c, reg) read_reset(c, reg)
static ktime_t ktime_get(void) { return now; }
static ktime_t ktime_add_us(ktime_t t,u32 delta) { return t+delta; }
static int ktime_compare_safe(ktime_t a,ktime_t b) { return (a>b)-(a<b); }
static void usleep_range(int lo,int hi) { (void)lo; (void)hi; now+=wake_step; }
'''
harness+=function(115,'old_poll')+'\n'+function(118,'new_poll')+r'''
static u32 run(u32 (*poll)(struct dpu_hw_ctl *, u32),int64_t clear,int64_t sleep) {
    struct dpu_hw_ctl ctx={0}; now=0; clear_at=clear; wake_step=sleep; reads=0;
    return poll(&ctx,2000);
}
int main(void) {
    assert(run(old_poll,1000,2500)==1); /* old stale-bit false failure */
    assert(run(new_poll,1000,2500)==0); /* clears during delayed wakeup */
    assert(reads==2 && now==2500);
    assert(run(new_poll,100000,2500)==1); /* stuck bit remains failure */
    assert(reads==2 && now==2500);
    assert(run(new_poll,0,30)==0); /* already idle */
    assert(run(new_poll,90,30)==0); /* normal multi-read completion */
    assert(run(new_poll,100000,30)==1 && now>=2000 && now<2050);
    puts("POLL_ACTUAL_C_FIVE_CASES_PASS_STALE_READ_REPRODUCED_STUCK_RESET_REJECTED");
}
'''
p=out/'poll-behavior.c';p.write_text(harness)
subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2',str(p),'-o',str(out/'poll-behavior')],check=True)
subprocess.run([str(out/'poll-behavior')],check=True,timeout=3)
report=dict(actual_old_and_new_c_functions_exercised=True,old_delayed_wakeup_false_timeout_reproduced=True,new_delayed_wakeup_reads_cleared_bit=True,stuck_bit_rejected=True,already_idle_pass=True,normal_completion_pass=True,normal_stuck_deadline_bounded=True,device_runtime_not_tested=True,goal_complete=False)
(root/'poll-behavior-validation.json').write_text(json.dumps(report,indent=2)+'\n')
