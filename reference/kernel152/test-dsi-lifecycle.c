/* Actual driver functions are included from an extracted generated header. */
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef uint32_t u32;
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define DBG(...) ((void)0)
#define pr_err_ratelimited(...) ((void)0)
#define trace_msm_dsi_error_work(...) ((void)0)
#define DSI_RESET_TOGGLE_DELAY_MS 20
#define DSI_ERR_STATE_MDP_FIFO_UNDERFLOW 8
#define DSI_CTRL_ENABLE 1
#define DSI_CTRL_VID_MODE_EN 2
#define DSI_CTRL_CMD_MODE_EN 4
#define DSI_IRQ_MASK_ERROR 1
#define DSI_IRQ_MASK_CMD_MDP_DONE 2
#define DSI_IRQ_MASK_VIDEO_DONE 4
#define MIPI_DSI_MODE_VIDEO 1
#define DSI_CLK_CTRL_ENABLE_CLKS 255
#define REG_DSI_CTRL 0
#define REG_DSI_RESET 1
#define REG_DSI_CLK_CTRL 2
struct mipi_dsi_host {int dummy;};
struct work_struct {int dummy;};
struct mipi_dsi_msg {int dummy;};
struct dev {int dummy;};
struct pdev {struct dev dev;};
struct msm_dsi_host;
struct ops {void (*link_clk_disable)(struct msm_dsi_host *);};
struct cfg {int num_regulators;};
struct msm_dsi_cfg_handler {struct ops *ops; struct cfg *cfg;};
struct msm_dsi_host {
    struct mipi_dsi_host base;
    struct work_struct err_work;
    pthread_mutex_t cmd_mutex,dev_mutex;
    bool power_on,enabled;
    u32 err_work_state,mode_flags;
    int id,irq;
    struct msm_dsi_cfg_handler *cfg_hnd;
    struct pdev *pdev;
    void *supplies;
};
static atomic_uint regs[3];
static atomic_int unclocked_accesses, resets, xfers, intr_enables, canceled, irq_disabled;
static atomic_bool clocks_on, operation_done;
static pthread_mutex_t gate_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t gate_cond=PTHREAD_COND_INITIALIZER;
static bool block_worker, worker_asleep, release_worker;
static _Thread_local int role;
static struct msm_dsi_host *to_msm_dsi_host(struct mipi_dsi_host *p) {return container_of(p,struct msm_dsi_host,base);}
static void mutex_lock(pthread_mutex_t *m) {assert(!pthread_mutex_lock(m));}
static void mutex_unlock(pthread_mutex_t *m) {assert(!pthread_mutex_unlock(m));}
static u32 dsi_read(struct msm_dsi_host *h,u32 r) {
    (void)h; if(!atomic_load(&clocks_on)) atomic_fetch_add(&unclocked_accesses,1);
    return atomic_load(&regs[r]);
}
static void dsi_write(struct msm_dsi_host *h,u32 r,u32 v) {
    (void)h; if(!atomic_load(&clocks_on)) atomic_fetch_add(&unclocked_accesses,1);
    atomic_store(&regs[r],v); if(r==REG_DSI_RESET && v) atomic_fetch_add(&resets,1);
}
static void wmb(void) {atomic_thread_fence(memory_order_seq_cst);}
static void msleep(int delay) {
    (void)delay;
    if(role!=1 || !block_worker) return;
    pthread_mutex_lock(&gate_lock); worker_asleep=true; pthread_cond_broadcast(&gate_cond);
    while(!release_worker) pthread_cond_wait(&gate_cond,&gate_lock);
    pthread_mutex_unlock(&gate_lock);
}
static void dsi_intr_ctrl(struct msm_dsi_host *h,u32 mask,int enable) {
    (void)h;(void)mask; if(!atomic_load(&clocks_on)) atomic_fetch_add(&unclocked_accesses,1);
    if(enable) atomic_fetch_add(&intr_enables,1);
}
static void disable_irq(int irq) {(void)irq; atomic_store(&irq_disabled,1);}
static __attribute__((unused)) void cancel_work_sync(struct work_struct *work) {
    (void)work; assert(atomic_load(&irq_disabled)); atomic_fetch_add(&canceled,1);
}
static void pinctrl_pm_select_sleep_state(struct dev *d) {(void)d;}
static void pm_runtime_put(struct dev *d) {(void)d;}
static void regulator_bulk_disable(int n,void *s) {(void)n;(void)s;}
static void msm_dsi_sfpb_config(struct msm_dsi_host *h,bool on) {(void)h;(void)on;}
static void disable_clocks(struct msm_dsi_host *h) {(void)h;atomic_store(&clocks_on,false);}
static int msm_dsi_manager_cmd_xfer(int id,const struct mipi_dsi_msg *msg) {
    (void)id;(void)msg;atomic_fetch_add(&xfers,1);
    if(!atomic_load(&clocks_on)) atomic_fetch_add(&unclocked_accesses,1);
    return 7;
}
#include "actual-dsi-functions.h"
static struct ops ops={.link_clk_disable=disable_clocks};
static struct cfg cfg={0};
static struct msm_dsi_cfg_handler handler={&ops,&cfg};
static struct pdev pdev;
static struct msm_dsi_host host;
static void init_host(void) {
    memset(&host,0,sizeof(host));
    pthread_mutex_init(&host.cmd_mutex,NULL);pthread_mutex_init(&host.dev_mutex,NULL);
    host.power_on=true;host.enabled=true;host.err_work_state=8;host.cfg_hnd=&handler;host.pdev=&pdev;
    atomic_store(&clocks_on,true);atomic_store(&operation_done,false);
    atomic_store(&regs[0],DSI_CTRL_ENABLE|DSI_CTRL_CMD_MODE_EN);atomic_store(&regs[1],0);atomic_store(&regs[2],0);
    atomic_store(&unclocked_accesses,0);atomic_store(&resets,0);atomic_store(&xfers,0);
    atomic_store(&intr_enables,0);atomic_store(&canceled,0);atomic_store(&irq_disabled,0);
    block_worker=false;worker_asleep=false;release_worker=false;
}
static void fini_host(void) {pthread_mutex_destroy(&host.cmd_mutex);pthread_mutex_destroy(&host.dev_mutex);}
static void *worker(void *unused) {(void)unused;role=1;dsi_err_worker(&host.err_work);return NULL;}
static void *disable_mode(void *unused) {(void)unused;role=2;msm_dsi_host_disable(&host.base);atomic_store(&operation_done,true);return NULL;}
static void *power_off(void *unused) {(void)unused;role=2;msm_dsi_host_power_off(&host.base);atomic_store(&operation_done,true);return NULL;}
static void *transfer(void *unused) {(void)unused;role=2;struct mipi_dsi_msg msg={0};dsi_host_transfer(&host.base,&msg);atomic_store(&operation_done,true);return NULL;}
static void start_blocked_worker(pthread_t *thread) {
    block_worker=true;pthread_create(thread,NULL,worker,NULL);
    pthread_mutex_lock(&gate_lock);while(!worker_asleep)pthread_cond_wait(&gate_cond,&gate_lock);pthread_mutex_unlock(&gate_lock);
}
static void unblock_worker(void) {pthread_mutex_lock(&gate_lock);release_worker=true;pthread_cond_broadcast(&gate_cond);pthread_mutex_unlock(&gate_lock);}
static int failures;
static void check(const char *name,bool ok) {printf("CASE %s %s\n",name,ok?"PASS":"FAIL");failures+=!ok;}
int main(void) {
    pthread_t a,b;
    init_host();start_blocked_worker(&a);pthread_create(&b,NULL,disable_mode,NULL);
    usleep(30000);bool serialized=!atomic_load(&operation_done);unblock_worker();pthread_join(a,NULL);pthread_join(b,NULL);
    check("reset_serializes_mode_disable",serialized);
    check("disable_cannot_restore_old_enabled_ctrl",!(atomic_load(&regs[0])&(DSI_CTRL_ENABLE|DSI_CTRL_CMD_MODE_EN))&&!host.enabled);fini_host();
    init_host();start_blocked_worker(&a);pthread_create(&b,NULL,power_off,NULL);
    usleep(30000);serialized=!atomic_load(&operation_done);unblock_worker();pthread_join(a,NULL);pthread_join(b,NULL);
    check("power_off_waits_for_reset",serialized);check("no_mmio_after_clock_disable",!atomic_load(&unclocked_accesses));fini_host();
    init_host();start_blocked_worker(&a);pthread_create(&b,NULL,transfer,NULL);
    usleep(30000);serialized=!atomic_load(&operation_done);unblock_worker();pthread_join(a,NULL);pthread_join(b,NULL);
    check("dma_transfer_waits_for_reset",serialized&&atomic_load(&xfers)==1);fini_host();
    init_host();host.power_on=false;atomic_store(&clocks_on,false);dsi_err_worker(&host.err_work);
    check("late_off_worker_has_no_mmio",!atomic_load(&unclocked_accesses)&&!atomic_load(&resets)&&!host.err_work_state);fini_host();
    init_host();msm_dsi_host_disable_irq(&host.base);
    check("irq_disable_drains_pending_work",atomic_load(&canceled)==1&&!host.err_work_state);fini_host();
    init_host();struct mipi_dsi_msg msg={0};check("ordinary_transfer",dsi_host_transfer(&host.base,&msg)==7&&atomic_load(&xfers)==1);
    check("null_transfer",dsi_host_transfer(&host.base,NULL)==-EINVAL&&atomic_load(&xfers)==1);
    msm_dsi_host_power_off(&host.base);check("off_transfer_rejected",dsi_host_transfer(&host.base,&msg)==-EINVAL&&atomic_load(&xfers)==1);fini_host();
    init_host();host.err_work_state=1;dsi_err_worker(&host.err_work);
    check("non_underflow_error_no_reset",!atomic_load(&resets)&&!host.err_work_state&&atomic_load(&intr_enables)==1);fini_host();
    init_host();host.enabled=false;atomic_store(&regs[0],0);msm_dsi_host_enable(&host.base);
    check("ordinary_enable_disable",host.enabled&&(atomic_load(&regs[0])&DSI_CTRL_CMD_MODE_EN));
    msm_dsi_host_disable(&host.base);check("ordinary_disable",!host.enabled&&!atomic_load(&regs[0]));
    msm_dsi_host_disable_irq(&host.base);msm_dsi_host_power_off(&host.base);
    check("ordinary_teardown",!host.power_on&&!atomic_load(&clocks_on)&&!atomic_load(&unclocked_accesses));fini_host();
    printf("FAILURES %d\n",failures);return failures?1:0;
}
