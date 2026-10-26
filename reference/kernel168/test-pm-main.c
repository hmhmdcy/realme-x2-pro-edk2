/* SPDX-License-Identifier: GPL-2.0 */
static void reset(struct qcom_slim_ngd_ctrl *c, struct device *d) {
    *c = (struct qcom_slim_ngd_ctrl){ .dev = d, .state = QCOM_SLIM_NGD_CTRL_IDLE };
    d->data = c; c->qmi.handle = c;
    power_ret = power_calls = rx_ret = tx_ret = 0;
    terminate_calls = release_calls = free_calls = 0;
}
int main(void) {
    struct qcom_slim_ngd_ctrl c; struct device d; u32 mmio = 0;
    struct qcom_slim_ngd ngd = { .base = &mmio };
    int errors[] = { -EBUSY, -ETIMEDOUT, -EREMOTEIO };
    int cases = 0;
    for (unsigned int i = 0; i < sizeof(errors)/sizeof(errors[0]); ++i) {
        reset(&c, &d); assert(qcom_slim_ngd_init_dma(&c) == 0);
        power_ret = errors[i]; assert(qcom_slim_ngd_runtime_suspend(&d) == errors[i]);
        if (!c.dma_rx_channel || !c.dma_tx_channel || c.state != QCOM_SLIM_NGD_CTRL_IDLE) {
            qcom_slim_ngd_exit_dma(&c); puts("BASELINE_REJECTED_SUSPEND_INVALIDATES_DMA"); return 2;
        }
        assert(terminate_calls == 0 && free_calls == 0);
        qcom_slim_ngd_exit_dma(&c); assert(free_calls == 2); ++cases;
    }
    reset(&c, &d); assert(qcom_slim_ngd_init_dma(&c) == 0);
    assert(qcom_slim_ngd_runtime_suspend(&d) == 0);
    assert(c.state == QCOM_SLIM_NGD_CTRL_ASLEEP);
    assert(!c.dma_rx_channel && !c.dma_tx_channel && !c.rx_base && !c.tx_base);
    assert(terminate_calls == 2 && release_calls == 2 && free_calls == 2);
    qcom_slim_ngd_exit_dma(&c); assert(free_calls == 2); ++cases;
    reset(&c, &d); c.state = QCOM_SLIM_NGD_CTRL_DOWN; power_ret = -EREMOTEIO;
    assert(qcom_slim_ngd_runtime_resume(&d) == -EREMOTEIO);
    assert(c.state == QCOM_SLIM_NGD_CTRL_DOWN); ++cases;
    reset(&c, &d); c.qmi.handle = NULL;
    assert(qcom_slim_ngd_runtime_resume(&d) == -ENOTCONN && power_calls == 0); ++cases;
    reset(&c, &d); c.state = QCOM_SLIM_NGD_CTRL_ASLEEP; power_ret = -ETIMEDOUT;
    assert(qcom_slim_ngd_runtime_resume(&d) == -ETIMEDOUT);
    assert(c.state == QCOM_SLIM_NGD_CTRL_ASLEEP); ++cases;
    reset(&c, &d); c.state = QCOM_SLIM_NGD_CTRL_ASLEEP;
    assert(qcom_slim_ngd_runtime_resume(&d) == 0 && c.state == QCOM_SLIM_NGD_CTRL_AWAKE); ++cases;
    reset(&c, &d); tx_ret = -ENOMEM;
    assert(qcom_slim_ngd_init_dma(&c) == -ENOMEM);
    assert(!c.dma_rx_channel && !c.rx_base && free_calls == 1); ++cases;
    reset(&c, &d); rx_ret = -ENODEV;
    assert(qcom_slim_ngd_init_dma(&c) == -ENODEV && !c.dma_rx_channel); ++cases;
    reset(&c, &d); c.state = QCOM_SLIM_NGD_CTRL_ASLEEP; c.ngd = &ngd; rx_ret = -ENOMEM;
    assert(qcom_slim_ngd_setup(&c) == -ENOMEM && mmio == 0); ++cases;
    reset(&c, &d); c.state = QCOM_SLIM_NGD_CTRL_ASLEEP; c.ngd = &ngd;
    assert(qcom_slim_ngd_setup(&c) == 0 && mmio == 7);
    qcom_slim_ngd_exit_dma(&c); ++cases;
    reset(&c, &d);
    for (int i = 0; i < 100; ++i) {
        assert(qcom_slim_ngd_init_dma(&c) == 0);
        assert(qcom_slim_ngd_runtime_suspend(&d) == 0);
    }
    assert(free_calls == 200 && terminate_calls == 200 && release_calls == 200); ++cases;
    printf("{\"cases\":%d,\"cycles\":100}\n", cases);
    return 0;
}
