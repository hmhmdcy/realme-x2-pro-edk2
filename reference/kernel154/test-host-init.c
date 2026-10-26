/* Actual host power-on and reset functions, with clock/register stubs. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
#define REG_DSI_CTRL 0
#define REG_DSI_RESET 1
#define REG_DSI_CLK_CTRL 2
#define REG_DSI_CMD_MODE_MDP_CTRL2 3
#define REG_DSI_COMMAND_COMPRESSION_MODE_CTRL 4
#define REG_DSI_TRIG_CTRL 5
#define REG_DSI_FIFO_STATUS 6
#define DSI_CTRL_ENABLE 1
#define DSI_CLK_CTRL_ENABLE_CLKS 255
#define DSI_RESET_TOGGLE_DELAY_MS 20
#define DBG(...) ((void)0)
#define pr_err(...) ((void)0)
#define dev_info(...) stub_dev_info(__VA_ARGS__)
struct device { int dummy; };
static __attribute__((unused)) void stub_dev_info(struct device *dev,const char *format,...) {
    (void)dev;(void)format;
}
struct platform_device { struct device dev; };
struct mipi_dsi_host { int dummy; };
struct msm_dsi_phy { int dummy; };
struct msm_dsi_phy_shared_timings { bool byte_intf_clk_div_2; };
struct msm_dsi_host;
struct ops { int (*link_clk_set_rate)(struct msm_dsi_host *);
    int (*link_clk_enable)(struct msm_dsi_host *);
    void (*link_clk_disable)(struct msm_dsi_host *); };
struct cfg { int num_regulators; };
struct msm_dsi_cfg_handler { struct ops *ops; struct cfg *cfg; };
struct msm_dsi_host { struct mipi_dsi_host base; int dev_mutex;
    bool power_on,byte_intf_clk_div_2; struct platform_device *pdev;
    struct msm_dsi_cfg_handler *cfg_hnd; void *supplies; };
static struct msm_dsi_host host;
static u32 regs[7];
static int fail_regulator,fail_rate,fail_enable,fail_pinctrl;
static int enabled_regulators,pm_refs,lock_depth,unclocked,timing_calls,resets;
static int live_timing_writes,reset_restores_enabled;
static bool link_clocks;
static struct msm_dsi_host *to_msm_dsi_host(struct mipi_dsi_host *p) {
    assert(p==&host.base); return &host;
}
static void mutex_lock(int *m) { (void)m; assert(lock_depth++==0); }
static void mutex_unlock(int *m) { (void)m; assert(--lock_depth==0); }
static void msm_dsi_sfpb_config(struct msm_dsi_host *h,bool enable) {(void)h;(void)enable;}
static int regulator_bulk_enable(int n,void *p) {(void)n;(void)p;
    if(fail_regulator) return -EIO;
    enabled_regulators++; return 0;
}
static void regulator_bulk_disable(int n,void *p) {(void)n;(void)p;enabled_regulators--;}
static int pm_runtime_get_sync(struct device *dev) {(void)dev;pm_refs++;return 0;}
static void pm_runtime_put(struct device *dev) {(void)dev;pm_refs--;}
static int set_rate(struct msm_dsi_host *h) {(void)h;return fail_rate?-EIO:0;}
static int enable_clock(struct msm_dsi_host *h) {(void)h;
    if(fail_enable) return -EIO;
    link_clocks=true;return 0;
}
static void disable_clock(struct msm_dsi_host *h) {(void)h;link_clocks=false;}
static int pinctrl_pm_select_default_state(struct device *dev) {(void)dev;return fail_pinctrl?-EIO:0;}
static u32 dsi_read(struct msm_dsi_host *h,int reg) {(void)h;unclocked+=!link_clocks;return regs[reg];}
static void dsi_write(struct msm_dsi_host *h,int reg,u32 value) {(void)h;unclocked+=!link_clocks;
    if(reg==REG_DSI_RESET && value) resets++;
    if(reg==REG_DSI_CTRL && resets && (value&DSI_CTRL_ENABLE)) reset_restores_enabled++;
    regs[reg]=value;
}
static void wmb(void) {}
static void msleep(int ms) {(void)ms;}
static void dsi_timing_setup(struct msm_dsi_host *h,bool bonded) {(void)h;(void)bonded;
    timing_calls++;live_timing_writes+=!!(regs[REG_DSI_CTRL]&DSI_CTRL_ENABLE);
}
static void dsi_ctrl_enable(struct msm_dsi_host *h,struct msm_dsi_phy_shared_timings *t,
    struct msm_dsi_phy *p) {(void)h;(void)t;(void)p;regs[REG_DSI_CTRL]=0x1f1;}
#include "actual-host-functions.h"
static struct ops ops={set_rate,enable_clock,disable_clock};
static struct cfg cfg={2};
static struct msm_dsi_cfg_handler handler={&ops,&cfg};
static struct platform_device pdev;
static struct msm_dsi_phy_shared_timings timings={true};
static struct msm_dsi_phy phy;
static int failures,cases;
static void init(u32 ctrl) {
    memset(&host,0,sizeof(host));memset(regs,0,sizeof(regs));regs[0]=ctrl;
    host.cfg_hnd=&handler;host.pdev=&pdev;
    fail_regulator=fail_rate=fail_enable=fail_pinctrl=0;
    enabled_regulators=pm_refs=lock_depth=unclocked=timing_calls=resets=0;
    live_timing_writes=reset_restores_enabled=0;link_clocks=false;
}
static void check(const char *name,bool good) {
    printf("CASE %s %s\n",name,good?"PASS":"FAIL");cases++;failures+=!good;
}
static int on(void) {return msm_dsi_host_power_on(&host.base,&timings,false,&phy);}
int main(void) {
    init(0x1f5);int ret=on();
    check("firmware_cmd_stopped_before_timing",!live_timing_writes);
    check("first_reset_does_not_resume_firmware_ctrl",!reset_restores_enabled);
    check("native_power_on",ret==0&&host.power_on&&regs[0]==0x1f1&&link_clocks&&resets==1);
    check("clocked_mmio",!unclocked);
    check("repeat_on_is_noop",on()==0&&timing_calls==1&&resets==1);
    init(0x1f3);ret=on();check("firmware_video_stopped_before_timing",ret==0&&!live_timing_writes);
    init(0);ret=on();check("ordinary_dpms_power_on",ret==0&&!live_timing_writes&&!reset_restores_enabled&&!unclocked);
    init(0x1f5);fail_regulator=1;ret=on();
    check("regulator_failure_no_mmio",ret==-EIO&&!timing_calls&&!unclocked&&!host.power_on&&regs[0]==0x1f5&&!lock_depth);
    init(0x1f5);fail_rate=1;ret=on();
    /* The unchanged baseline leaves its runtime PM reference on this path. */
    check("rate_failure_no_mmio",ret==-EIO&&!timing_calls&&!unclocked&&!host.power_on&&!enabled_regulators&&!lock_depth);
    init(0x1f5);fail_enable=1;ret=on();
    check("clock_failure_no_mmio",ret==-EIO&&!timing_calls&&!unclocked&&!host.power_on&&!enabled_regulators&&!lock_depth);
    init(0x1f5);fail_pinctrl=1;ret=on();
    check("pinctrl_failure_teardown",ret==-EIO&&!timing_calls&&!unclocked&&!host.power_on&&!link_clocks&&!enabled_regulators&&!pm_refs&&!lock_depth);
    printf("CASES %d FAILURES %d\n",cases,failures);return failures?1:0;
}
