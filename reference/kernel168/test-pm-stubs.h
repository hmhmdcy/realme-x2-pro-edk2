/* SPDX-License-Identifier: GPL-2.0 */
/* Only hardware/PM primitives are mocked; driver functions are extracted. */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef unsigned int u32;
#define __maybe_unused
#define dev_err(...) ((void)0)
#define dev_err_ratelimited(...) ((void)0)
#define dev_info(...) ((void)0)
#define dev_info_once(...) ((void)0)
#define QCOM_SLIM_NGD_DESC_NUM 32
#define SLIM_MSGQ_BUF_LEN 40
#define NGD_CFG_RX_MSGQ_EN 2
#define NGD_CFG_TX_MSGQ_EN 4
#define NGD_CFG_ENABLE 1
enum { QCOM_SLIM_NGD_CTRL_AWAKE, QCOM_SLIM_NGD_CTRL_IDLE,
       QCOM_SLIM_NGD_CTRL_ASLEEP, QCOM_SLIM_NGD_CTRL_DOWN };
struct device { void *data; };
struct dma_chan { int live; };
struct qcom_slim_ngd { u32 *base; };
struct qcom_slim_ngd_ctrl {
    struct device *dev; int state; struct { void *handle; } qmi;
    struct dma_chan *dma_rx_channel, *dma_tx_channel;
    void *rx_base, *tx_base; unsigned long rx_phys_base, tx_phys_base;
    struct qcom_slim_ngd *ngd;
};
static int power_ret, power_calls, rx_ret, tx_ret;
static int terminate_calls, release_calls, free_calls;
static struct dma_chan rx_channel, tx_channel;
static void *dev_get_drvdata(struct device *dev) { return dev->data; }
static void dmaengine_terminate_sync(struct dma_chan *c) {
    assert(c->live == 1); c->live = 2; ++terminate_calls;
}
static void dma_release_channel(struct dma_chan *c) {
    assert(c->live == 2); c->live = 0; ++release_calls;
}
static void dma_free_coherent(struct device *d, int size, void *p, unsigned long phys) {
    (void)d; (void)size; (void)phys;
    assert(p); free(p); ++free_calls;
}
static int qcom_slim_qmi_power_request(struct qcom_slim_ngd_ctrl *c, bool active) {
    (void)c; assert(!active); ++power_calls; return power_ret;
}
static int qcom_slim_ngd_power_up(struct qcom_slim_ngd_ctrl *c) {
    (void)c; ++power_calls; return power_ret;
}
static u32 readl_relaxed(u32 *p) { return *p; }
static void writel_relaxed(u32 val, u32 *p) { *p = val; }
static int qcom_slim_ngd_init_rx_msgq(struct qcom_slim_ngd_ctrl *c) {
    if (rx_ret) return rx_ret;
    rx_channel.live = 1; c->dma_rx_channel = &rx_channel;
    c->rx_base = malloc(1280); assert(c->rx_base); return 0;
}
static int qcom_slim_ngd_init_tx_msgq(struct qcom_slim_ngd_ctrl *c) {
    if (tx_ret) return tx_ret;
    tx_channel.live = 1; c->dma_tx_channel = &tx_channel;
    c->tx_base = malloc(1320); assert(c->tx_base); return 0;
}
