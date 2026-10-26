#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint32_t u32;
typedef int irqreturn_t;
#define IRQ_HANDLED 1
struct work_struct { unsigned dummy; };
struct completion { unsigned completed; };
struct msm_dsi_host {
    int id;
    void *ctrl_base;
    void *workqueue;
    unsigned intr_lock;
    struct work_struct err_work;
    struct completion video_comp, dma_comp;
    u32 err_work_state;
    u32 regs[1024];
};
struct operation { char type; u32 reg, value; };
struct event { char type; int id; u32 reg, raw, state; bool done, irq_enabled; unsigned resets, ops; };
static struct operation operations[128];
static struct event events[32];
static unsigned nops, nevents, resets, queues, cases;
static bool locked, irq_enabled, tracing;
static uint64_t signature = 1469598103934665603ULL;

static void op(char type, u32 reg, u32 value)
{
    assert(nops < 128);
    operations[nops++] = (struct operation){type, reg, value};
}
static u32 dsi_read(struct msm_dsi_host *host, u32 reg)
{
    assert(reg % 4 == 0 && reg / 4 < 1024);
    u32 value = host->regs[reg / 4];
    op('R', reg, value);
    return value;
}
static void dsi_write(struct msm_dsi_host *host, u32 reg, u32 value)
{
    assert(reg % 4 == 0 && reg / 4 < 1024);
    op('C', reg, value);
    host->regs[reg / 4] &= ~value;
}
static void record(char type, int id, u32 reg, u32 raw, u32 state, bool done)
{
    if (!tracing)
        return;
    assert(!locked && nevents < 32);
    events[nevents++] = (struct event){type, id, reg, raw, state, done, irq_enabled, resets, nops};
}
static void __attribute__((unused)) trace_msm_dsi_error_status(int id, u32 reg, u32 raw, u32 state)
{
    record('S', id, reg, raw, state, false);
}
static void __attribute__((unused)) trace_msm_dsi_error_irq(int id, u32 isr)
{
    record('I', id, 0, isr, 0, false);
}
static void __attribute__((unused)) trace_msm_dsi_error_work(int id, u32 state, bool done)
{
    record('W', id, 0, 0, state, done);
}
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
#define spin_lock_irqsave(lock, flags) do { (void)(lock); (flags) = 0; assert(!locked); locked = true; } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(lock); (void)(flags); assert(locked); locked = false; } while (0)
#define DBG(...) do { } while (0)
#define pr_err_ratelimited(format, function, state) op('L', 0, state)
static void dsi_sw_reset(struct msm_dsi_host *host)
{
    (void)host;
    resets++;
    op('X', 0, resets);
}
static void dsi_intr_ctrl(struct msm_dsi_host *host, u32 mask, int enable)
{
    (void)host;
    irq_enabled = enable;
    op('M', mask, enable);
}
static void queue_work(void *workqueue, struct work_struct *work)
{
    (void)workqueue;
    (void)work;
    queues++;
    op('Q', 0, queues);
}
static void complete(struct completion *completion)
{
    completion->completed++;
    op('D', 0, completion->completed);
}

#include "dsi-generated-functions.h"

static void init(struct msm_dsi_host *host)
{
    memset(host, 0, sizeof(*host));
    host->id = 1;
    host->ctrl_base = host;
    nops = nevents = resets = queues = 0;
    locked = false;
    irq_enabled = tracing = true;
}
static void finish(struct msm_dsi_host *host)
{
    assert(!locked);
    for (unsigned i = 0; i < nops; i++) {
        signature = (signature ^ operations[i].type) * 1099511628211ULL;
        signature = (signature ^ operations[i].reg) * 1099511628211ULL;
        signature = (signature ^ operations[i].value) * 1099511628211ULL;
    }
    signature = (signature ^ host->err_work_state) * 1099511628211ULL;
    signature = (signature ^ host->video_comp.completed) * 1099511628211ULL;
    signature = (signature ^ host->dma_comp.completed) * 1099511628211ULL;
    cases++;
}
static void expect_status(struct msm_dsi_host *host, u32 reg, u32 raw, u32 state, unsigned writes)
{
    assert(host->err_work_state == state && nops == 1 + writes);
    assert(operations[0].type == 'R' && operations[0].reg == reg && operations[0].value == raw);
    if (writes) {
        assert(operations[1].type == 'C' && operations[1].reg == reg && operations[1].value == raw);
        assert(host->regs[reg / 4] == 0);
    }
    if (writes == 2)
        assert(operations[2].type == 'C' && operations[2].value == 0);
#ifndef BASELINE144
    assert(nevents == 1 && events[0].type == 'S' && events[0].id == 1);
    assert(events[0].reg == reg && events[0].raw == raw && events[0].state == state && events[0].ops == nops);
#endif
    finish(host);
}
int main(void)
{
    struct msm_dsi_host host;
    void (*helpers[])(struct msm_dsi_host *) = {dsi_clk_status, dsi_fifo_status, dsi_ack_err_status,
                                               dsi_timeout_status, dsi_status, dsi_dln0_phy_err};
    const u32 regs[] = {REG_DSI_CLK_STATUS, REG_DSI_FIFO_STATUS, REG_DSI_ACK_ERR_STATUS,
                        REG_DSI_TIMEOUT_STATUS, REG_DSI_STATUS0, REG_DSI_DLN0_PHY_ERR};
    const u32 raws[] = {DSI_CLK_STATUS_PLL_UNLOCKED, DSI_FIFO_STATUS_CMD_MDP_FIFO_UNDERFLOW, 2,
                        1, DSI_STATUS0_INTERLEAVE_OP_CONTENTION, DSI_DLN0_PHY_ERR_DLN0_ERR_ESC};
    const u32 states[] = {DSI_ERR_STATE_PLL_UNLOCKED, DSI_ERR_STATE_FIFO | DSI_ERR_STATE_MDP_FIFO_UNDERFLOW,
                          DSI_ERR_STATE_ACK, DSI_ERR_STATE_TIMEOUT,
                          DSI_ERR_STATE_INTERLEAVE_OP_CONTENTION, DSI_ERR_STATE_DLN0_PHY};
    for (unsigned i = 0; i < 6; i++) {
        init(&host);
        helpers[i](&host);
        expect_status(&host, regs[i], 0, 0, 0);
        init(&host);
        host.regs[regs[i] / 4] = raws[i];
        helpers[i](&host);
        expect_status(&host, regs[i], raws[i], states[i], i == 2 ? 2 : 1);
    }
    for (unsigned i = 0; i < 2; i++) {
        init(&host);
        u32 raw = 0x40000000U | (i ? DSI_FIFO_STATUS_CMD_MDP_FIFO_UNDERFLOW : 0);
        host.regs[REG_DSI_FIFO_STATUS / 4] = raw;
        host.err_work_state = DSI_ERR_STATE_TIMEOUT;
        dsi_fifo_status(&host);
        expect_status(&host, REG_DSI_FIFO_STATUS, raw,
                      DSI_ERR_STATE_TIMEOUT | DSI_ERR_STATE_FIFO | (i ? DSI_ERR_STATE_MDP_FIFO_UNDERFLOW : 0), 1);
    }
    for (unsigned i = 0; i < 2; i++) {
        init(&host);
        u32 raw = 0x80000000U | (i ? DSI_DLN0_PHY_ERR_DLN0_ERR_ESC : 0);
        host.regs[REG_DSI_DLN0_PHY_ERR / 4] = raw;
        dsi_dln0_phy_err(&host);
        expect_status(&host, REG_DSI_DLN0_PHY_ERR, raw, i ? DSI_ERR_STATE_DLN0_PHY : 0, i);
    }
    const u32 worker_states[] = {0, DSI_ERR_STATE_FIFO, DSI_ERR_STATE_MDP_FIFO_UNDERFLOW,
                                  DSI_ERR_STATE_FIFO | DSI_ERR_STATE_MDP_FIFO_UNDERFLOW | DSI_ERR_STATE_PLL_UNLOCKED};
    for (unsigned i = 0; i < 4; i++) {
        init(&host);
        irq_enabled = false;
        host.err_work_state = worker_states[i];
        dsi_err_worker(&host.err_work);
        assert(host.err_work_state == 0 && irq_enabled);
        assert(resets == !!(worker_states[i] & DSI_ERR_STATE_MDP_FIFO_UNDERFLOW));
        assert(operations[nops - 1].type == 'M' && operations[nops - 1].value == 1);
#ifndef BASELINE144
        assert(nevents == 2 && events[0].type == 'W' && !events[0].done && !events[0].irq_enabled);
        assert(events[0].ops == 0 && events[0].state == worker_states[i]);
        assert(events[1].type == 'W' && events[1].done && events[1].irq_enabled);
        assert(events[1].state == worker_states[i] && events[1].ops == nops && events[1].resets == resets);
#endif
        finish(&host);
    }
    init(&host);
    host.ctrl_base = NULL;
    assert(dsi_host_irq(3, &host) == IRQ_HANDLED && nops == 0 && nevents == 0);
    finish(&host);
    init(&host);
    host.regs[REG_DSI_INTR_CTRL / 4] = DSI_IRQ_CMD_DMA_DONE | DSI_IRQ_VIDEO_DONE;
    assert(dsi_host_irq(3, &host) == IRQ_HANDLED && nops == 4 && nevents == 0);
    assert(host.video_comp.completed == 1 && host.dma_comp.completed == 1 && queues == 0);
    finish(&host);
    for (unsigned disabled = 0; disabled < 2; disabled++) {
        init(&host);
        tracing = !disabled;
        for (unsigned i = 0; i < 6; i++)
            host.regs[regs[i] / 4] = raws[i];
        const u32 isr = DSI_IRQ_ERROR | DSI_IRQ_CMD_DMA_DONE | DSI_IRQ_VIDEO_DONE;
        host.regs[REG_DSI_INTR_CTRL / 4] = isr;
        assert(dsi_host_irq(3, &host) == IRQ_HANDLED && queues == 1 && !irq_enabled);
        assert(host.video_comp.completed == 1 && host.dma_comp.completed == 1);
#ifndef BASELINE144
        if (!disabled) {
            assert(nevents == 7 && events[0].type == 'I' && events[0].raw == isr && events[0].ops == 2);
            for (unsigned i = 0; i < 6; i++)
                assert(events[i + 1].type == 'S' && events[i + 1].reg == regs[i] && events[i + 1].raw == raws[i]);
        }
#endif
        dsi_err_worker(&host.err_work);
        assert(host.err_work_state == 0 && irq_enabled && resets == 1);
#ifndef BASELINE144
        assert(nevents == (disabled ? 0U : 9U));
#endif
        finish(&host);
    }
    assert(cases == 24);
    printf("DSI actual-function cases passed: %u; hardware-effect signature: %016llx\n", cases, (unsigned long long)signature);
    return 0;
}
