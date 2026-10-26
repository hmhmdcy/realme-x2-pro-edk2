/* SPDX-License-Identifier: GPL-2.0 */
static struct device dev;
static struct slim_controller core;
static struct qcom_slim_ngd_ctrl ngd;
static u32 buffer[330];
static u8 payload[2] = {0x12, 0x34};
static struct slim_val_inf msg;
static struct slim_msg_txn txn;
static int active_ids(void) { int n = 0; for (int i = 1; i < 256; ++i) n += !!core.ids[i]; return n; }
static void reset(u8 mc)
{
 memset(&dev, 0, sizeof(dev)); memset(&core, 0, sizeof(core));
 memset(&ngd, 0, sizeof(ngd)); memset(buffer, 0, sizeof(buffer));
 core.dev = &dev; core.sched.clk_state = SLIM_CLK_ACTIVE;
 core.xfer_msg = qcom_slim_ngd_xfer_msg; dev.drvdata = &ngd;
 ngd.dev = &dev; ngd.tx_base = buffer;
 msg = (struct slim_val_inf){.num_bytes=2, .wbuf=payload};
 txn = (struct slim_msg_txn){.rl=9, .mt=SLIM_MSG_MT_CORE, .mc=mc,
   .dt=SLIM_MSG_DEST_LOGICALADDR, .la=0x20, .msg=&msg};
 fail_prep = fail_tid = suppress_reply = suppress_dma_completion = false;
 prep_count = callback_count = free_count = bad_free_count = get_count = put_count = 0;
 pending = NULL; reply_ctrl = &core; reply_txn = &txn;
}
static bool slots_clear(void)
{
 for (int i = 0; i < 32; ++i) if (ngd.txdesc[i].comp) return false;
 return ngd.tx_head == ngd.tx_tail && ngd.tx_lock == 0 && ngd.tx_buf_lock == 0;
}
int main(void)
{
 bool ok[12] = {0}; int dma_failed = 0, exhausted = 0;
 reset(SLIM_MSG_MC_REQUEST_VALUE); fail_prep = true;
 for (int i = 0; i < 100; ++i) {
  txn.rl = 9; int ret = slim_do_transfer(&core, &txn);
  dma_failed += ret == -EINVAL; exhausted += ret == -ENOMEM;
 }
 ok[0] = dma_failed == 100 && exhausted == 0 && slots_clear();
 ok[1] = active_ids() == 0 && dev.pm_votes == 0 && get_count == put_count && !bad_free_count;
 fail_prep = false; txn.rl = 9;
 int ret = slim_do_transfer(&core, &txn);
 ok[2] = ret == 0 && callback_count == 1 && slots_clear() && active_ids() == 0 && dev.pm_votes == 0 && last_payload[6] == payload[0] && last_payload[7] == payload[1];

 reset(SLIM_MSG_MC_REQUEST_VALUE); ngd.tx_tail = 31;
 ret = slim_do_transfer(&core, &txn);
 ok[3] = ret == -ENOMEM && ngd.tx_head == 0 && ngd.tx_tail == 31 && !active_ids() && !dev.pm_votes && !bad_free_count && !prep_count;
 reset(SLIM_MSG_MC_REQUEST_VALUE); fail_tid = true;
 ret = slim_do_transfer(&core, &txn);
 ok[4] = ret == -ENOSPC && slots_clear() && !active_ids() && !dev.pm_votes && !prep_count;
 reset(SLIM_MSG_MC_CONNECT_SOURCE); fail_tid = true;
 ret = slim_do_transfer(&core, &txn);
 ok[5] = ret == -ENOSPC && slots_clear() && !active_ids() && !dev.pm_votes && !prep_count;
 reset(SLIM_MSG_MC_CONNECT_SOURCE); fail_prep = true;
 ret = slim_do_transfer(&core, &txn);
 ok[6] = ret == -EINVAL && slots_clear() && !active_ids() && !dev.pm_votes && !bad_free_count;
 reset(SLIM_MSG_MC_CHANGE_VALUE); fail_prep = true;
 ret = slim_do_transfer(&core, &txn);
 ok[7] = ret == -EINVAL && slots_clear() && !active_ids() && !dev.pm_votes && free_count == 0;

 /* An earlier queued slot remains live when the newest reservation fails. */
 reset(SLIM_MSG_MC_CHANGE_VALUE);
 struct completion older = {0}, newer = {0};
 u32 *b = qcom_slim_ngd_tx_msg_get(&ngd, 8, &older);
 assert(qcom_slim_ngd_tx_msg_post(&ngd, b, 8) == 0);
 struct dma_async_tx_descriptor *older_dma = pending;
 b = qcom_slim_ngd_tx_msg_get(&ngd, 8, &newer); fail_prep = true;
 ret = qcom_slim_ngd_tx_msg_post(&ngd, b, 8);
 ok[8] = ret == -EINVAL && ngd.tx_head == 0 && ngd.tx_tail == 1 && ngd.txdesc[0].comp == &older && ngd.txdesc[1].comp == NULL;
 older_dma->callback(older_dma->callback_param);
 ok[8] = ok[8] && older.done && ngd.tx_head == 1 && ngd.tx_tail == 1;

 reset(SLIM_MSG_MC_CHANGE_VALUE); txn.mt = SLIM_MSG_MT_DEST_REFERRED_USER;
 assert(slim_alloc_txn_tid(&core, &txn) == 0); fail_prep = true;
 ret = qcom_slim_ngd_xfer_msg(&core, &txn);
 ok[9] = ret == -EINVAL && slots_clear() && active_ids() == 1 && free_count == 0;
 slim_free_txn_tid(&core, &txn);
 ok[9] = ok[9] && !active_ids() && !bad_free_count;
 reset(SLIM_MSG_MC_REQUEST_VALUE); txn.tid = 200;
 core.sched.clk_state = SLIM_CLK_PAUSED;
 slim_do_transfer(&core, &txn);
 ok[10] = txn.tid == 0 && !dev.pm_votes && !prep_count;
 reset(SLIM_MSG_MC_REQUEST_VALUE); txn.dt = SLIM_MSG_DEST_ENUMADDR;
 ret = slim_do_transfer(&core, &txn);
 ok[11] = ret == -EPROTONOSUPPORT && !active_ids() && !dev.pm_votes && !prep_count && slots_clear();
 int passed = 0;
 printf("{\"cases\":[");
 for (int i = 0; i < 12; ++i) { passed += ok[i]; printf("%s%s", i ? "," : "", ok[i] ? "true" : "false"); }
 printf("],\"passed\":%d,\"dma_failures\":%d,\"ring_exhaustions\":%d}\n", passed, dma_failed, exhausted);
 return passed == 12 ? 0 : 2;
}
