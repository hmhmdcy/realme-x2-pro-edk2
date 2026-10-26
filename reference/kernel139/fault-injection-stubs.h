/* SPDX-License-Identifier: GPL-2.0 */
/* Host-only primitive stubs; tested driver functions are extracted verbatim. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
#define HZ 100
#define BIT(n) (1U << (n))
#define GENMASK(h, l) (((~0U) << (l)) & ((~0U) >> (31 - (h))))
#define DMA_MEM_TO_DEV 1
#define DMA_PREP_INTERRUPT 1
#define dev_err(...) ((void)0)
#define spin_lock_irqsave(lock, flags) do { (flags) = 0; assert(!*(lock)); ++*(lock); } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(flags); assert(*(lock) == 1); --*(lock); } while (0)
struct completion { int done; };
#define DECLARE_COMPLETION_ONSTACK(name) struct completion name = {0}
struct device { void *drvdata; int pm_votes; };
struct slim_val_inf { int num_bytes; u8 *wbuf, *rbuf; struct completion *comp; };
struct slim_msg_txn { u8 rl, mt, mc, dt, la, tid; u16 ec; struct slim_val_inf *msg; struct completion *comp; };
enum { SLIM_CLK_ACTIVE, SLIM_CLK_ENTERING_PAUSE, SLIM_CLK_PAUSED };
struct slim_controller {
 struct device *dev; struct { int clk_state; } sched;
 int (*xfer_msg)(struct slim_controller *, struct slim_msg_txn *);
 struct slim_msg_txn *ids[256];
};
struct dma_async_tx_descriptor { void (*callback)(void *); void *callback_param; int cookie; };
struct dma_chan { int unused; };
struct qcom_slim_ngd_ctrl;
struct qcom_slim_ngd_dma_desc {
 void *base; uintptr_t phys; struct completion *comp;
 struct qcom_slim_ngd_ctrl *ctrl; struct dma_async_tx_descriptor *desc;
};
struct qcom_slim_ngd_ctrl {
 struct device *dev; void *tx_base; uintptr_t tx_phys_base;
 int tx_buf_lock, tx_lock, tx_tail, tx_head;
 struct qcom_slim_ngd_dma_desc txdesc[32]; struct dma_chan *dma_tx_channel;
};
static bool fail_prep, fail_tid, suppress_reply, suppress_dma_completion;
static int prep_count, callback_count, free_count, bad_free_count, get_count, put_count;
static struct dma_async_tx_descriptor dma_pool[32], *pending;
static struct slim_controller *reply_ctrl;
static struct slim_msg_txn *reply_txn;
static unsigned char last_payload[40];
static void *dev_get_drvdata(struct device *dev) { return dev->drvdata; }
static void mutex_lock(int *p) { assert(!*p); ++*p; }
static void mutex_unlock(int *p) { assert(*p == 1); --*p; }
static void complete(struct completion *p) { p->done = 1; }
static int pm_runtime_get_sync(struct device *d) { ++get_count; return ++d->pm_votes; }
static void pm_runtime_mark_last_busy(struct device *d) { (void)d; }
static void pm_runtime_put_autosuspend(struct device *d) { ++put_count; --d->pm_votes; }
static unsigned long msecs_to_jiffies(unsigned long ms) { return ms; }
static int slim_alloc_txn_tid(struct slim_controller *c, struct slim_msg_txn *t)
{
 if (fail_tid) return -ENOSPC;
 for (int i = 1; i < 256; ++i) if (!c->ids[i]) { c->ids[i] = t; t->tid = i; return 0; }
 return -ENOSPC;
}
static void slim_free_txn_tid(struct slim_controller *c, struct slim_msg_txn *t)
{
 ++free_count;
 if (!t->tid || c->ids[t->tid] != t) ++bad_free_count;
 c->ids[t->tid] = NULL;
}
static struct dma_async_tx_descriptor *dmaengine_prep_slave_single(struct dma_chan *c,
 uintptr_t phys, int len, int dir, int flags)
{
 (void)c; (void)phys; (void)len; (void)dir; (void)flags;
 ++prep_count;
 if (fail_prep) return NULL;
 struct dma_async_tx_descriptor *p = &dma_pool[(prep_count - 1) % 32];
 memset(p, 0, sizeof(*p)); return p;
}
static int dmaengine_submit(struct dma_async_tx_descriptor *p) { pending = p; return 1; }
static void dma_async_issue_pending(struct dma_chan *c) { (void)c; }
static unsigned long wait_for_completion_timeout(struct completion *c, unsigned long timeout)
{
 (void)timeout;
 if (pending && !suppress_dma_completion) {
  struct dma_async_tx_descriptor *p = pending; pending = NULL;
  struct qcom_slim_ngd_dma_desc *desc = p->callback_param;
  memcpy(last_payload, desc->base, sizeof(last_payload));
  p->callback(p->callback_param); ++callback_count;
 }
 /* Emulate the existing response primitive: remove ID, complete, put PM. */
 if (!suppress_reply && reply_txn && reply_txn->tid && reply_ctrl->ids[reply_txn->tid]) {
  reply_ctrl->ids[reply_txn->tid] = NULL;
  if (reply_txn->comp) complete(reply_txn->comp);
  pm_runtime_put_autosuspend(reply_ctrl->dev);
 }
 return c->done ? 1 : 0;
}
