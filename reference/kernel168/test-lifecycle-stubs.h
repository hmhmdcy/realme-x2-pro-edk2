/* SPDX-License-Identifier: GPL-2.0 */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <errno.h>
enum { QCOM_SLIM_NGD_CTRL_AWAKE, QCOM_SLIM_NGD_CTRL_IDLE,
       QCOM_SLIM_NGD_CTRL_ASLEEP, QCOM_SLIM_NGD_CTRL_DOWN };
struct device { void *data; bool enabled, suspended; int votes; };
struct completion { unsigned int done; };
struct work_struct { int unused; };
struct qcom_slim_ngd_ctrl {
 struct device *dev; struct { struct device *dev; } ctrl;
 int state, ssr_lock, tx_lock; bool registered;
 struct { void *handle; struct completion qmi_comp; } qmi;
 struct work_struct m_work;
};
static int registrations, unregisters, dma_exits, drains, notifications;
static bool drained;
#define dev_err(...) ((void)0)
#define dev_info(...) ((void)0)
static void mutex_lock(int *p) { assert(!*p); *p=1; }
static void mutex_unlock(int *p) { assert(*p); *p=0; }
static void complete_all(struct completion *c) { c->done=~0U; }
static void complete(struct completion *c) { ++c->done; }
static int qcom_slim_qmi_init(struct qcom_slim_ngd_ctrl *c, bool unused) {
 (void)unused; c->qmi.handle=c; return 0;
}
static void qcom_slim_qmi_exit(struct qcom_slim_ngd_ctrl *c) {
 c->qmi.handle=NULL; c->qmi.qmi_comp.done=0;
}
static bool pm_runtime_enabled(struct device *d) { return d->enabled; }
static bool pm_runtime_suspended(struct device *d) { return d->suspended; }
static void pm_runtime_disable(struct device *d) { assert(d->enabled);d->enabled=false; }
static void pm_runtime_enable(struct device *d) { assert(!d->enabled);d->enabled=true; }
static int pm_runtime_set_suspended(struct device *d) { assert(!d->enabled);d->suspended=true;return 0; }
static int qcom_slim_ngd_runtime_resume(struct device *d) {
 struct qcom_slim_ngd_ctrl *c=d->data; assert(c->qmi.handle && c->qmi.qmi_comp.done);
 c->state=QCOM_SLIM_NGD_CTRL_AWAKE; d->suspended=false; return 0;
}
static int pm_runtime_resume(struct device *d) { return qcom_slim_ngd_runtime_resume(d); }
static void pm_runtime_mark_last_busy(struct device *d) { (void)d; }
static void pm_runtime_put(struct device *d) { --d->votes; }
static void pm_runtime_get_noresume(struct device *d) { ++d->votes; }
static int slim_register_controller(void *s) { (void)s; ++registrations;return 0; }
static void slim_unregister_controller(void *s) { (void)s;++unregisters; }
static void qcom_slim_ngd_notify_slaves(struct qcom_slim_ngd_ctrl *c) {
 assert(c->registered && c->state==QCOM_SLIM_NGD_CTRL_AWAKE); ++notifications;
}
static void cancel_work_sync(struct work_struct *w) { (void)w;drained=true;++drains; }
static int qcom_slim_ngd_update_device_status(struct device *d, void *arg) { (void)d;(void)arg;return 0; }
static void device_for_each_child(struct device *d, void *arg, int (*cb)(struct device *,void *)) {
 (void)arg;(void)cb;
 struct qcom_slim_ngd_ctrl *c=d->data;
 /* A device reference is safe only after master work is drained. */
 if (drained) assert(c->ssr_lock && !c->qmi.handle);
}
static int qcom_slim_ngd_exit_dma(struct qcom_slim_ngd_ctrl *c) {
 assert(c->ssr_lock && c->tx_lock && drained); ++dma_exits;return 0;
}
