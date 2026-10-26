from pathlib import Path
import difflib, hashlib, json, subprocess, re

k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel166')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel166')
assert not subprocess.check_output(['git','diff','--binary'],cwd=k)
changes={}
def replace(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)
def fn_replace(s,name,transform):
    start=re.search(r'static int (?:__maybe_unused )?'+name+r'\(',s).start()
    a=s.index('{',start);depth=1;b=a+1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[:start]+transform(s[start:b])+s[b:]

name='drivers/slimbus/messaging.c';old=(k/name).read_text()
new=replace(old,'\t\tret = pm_runtime_get_sync(ctrl->dev);\n',
'''\t\tret = pm_runtime_get_sync(ctrl->dev);
\t\tif (ret < 0) {
\t\t\tpm_runtime_put_noidle(ctrl->dev);
\t\t\treturn ret;
\t\t}
''')
changes[name]=(old,new)
name='drivers/slimbus/qcom-ngd-ctrl.c';old=(k/name).read_text();new=old
new=replace(new,'\trc = qmi_txn_init(ctrl->qmi.handle, &txn,\n\t\t\t\tslimbus_power_resp_msg_v01_ei, &resp);\n',
'''\trc = qmi_txn_init(ctrl->qmi.handle, &txn,
\t\t\t\tslimbus_power_resp_msg_v01_ei, &resp);
\tif (rc < 0)
\t\treturn rc;
''')
new=replace(new,'\tqmi_handle_release(ctrl->qmi.handle);\n',
                '\treinit_completion(&ctrl->qmi.qmi_comp);\n\tqmi_handle_release(ctrl->qmi.handle);\n')
new=replace(new,'rx_post_err:\n\tdma_free_coherent',
                'rx_post_err:\n\tdmaengine_terminate_sync(ctrl->dma_rx_channel);\n\tdma_free_coherent')
new=replace(new,'\tdma_release_channel(ctrl->dma_rx_channel);\n\treturn ret;\n',
                '\tctrl->rx_base = NULL;\n\tdma_release_channel(ctrl->dma_rx_channel);\n\tctrl->dma_rx_channel = NULL;\n\treturn ret;\n')
new=replace(new,'\t\tret = -EINVAL;\n\t\tgoto rel_tx;', '\t\tret = -ENOMEM;\n\t\tgoto rel_tx;')
new=replace(new,'\tdma_release_channel(ctrl->dma_tx_channel);\n\treturn ret;\n',
                '\tdma_release_channel(ctrl->dma_tx_channel);\n\tctrl->dma_tx_channel = NULL;\n\treturn ret;\n')
new=replace(new,'static int qcom_slim_ngd_init_dma(',
                'static int qcom_slim_ngd_exit_dma(struct qcom_slim_ngd_ctrl *ctrl);\n\nstatic int qcom_slim_ngd_init_dma(')
new=replace(new,'\tif (ret)\n\t\tdev_err(ctrl->dev, "tx dma init failed\\n");',
'''\tif (ret) {
\t\tdev_err(ctrl->dev, "tx dma init failed\\n");
\t\tqcom_slim_ngd_exit_dma(ctrl);
\t}''')
new=replace(new,'\tmutex_lock(&ctrl->tx_lock);\n\tpbuf = qcom_slim_ngd_tx_msg_get',
'''\tmutex_lock(&ctrl->tx_lock);
\tif (!ctrl->dma_tx_channel || !ctrl->dma_rx_channel) {
\t\tret = -EHOSTDOWN;
\t\tgoto err_unlock;
\t}
\tpbuf = qcom_slim_ngd_tx_msg_get''')
new=replace(new,'\tctrl->dma_tx_channel = ctrl->dma_rx_channel = NULL;\n',
'''\tctrl->dma_tx_channel = ctrl->dma_rx_channel = NULL;
\tif (ctrl->rx_base) {
\t\tdma_free_coherent(ctrl->dev,
\t\t\t\t  QCOM_SLIM_NGD_DESC_NUM * SLIM_MSGQ_BUF_LEN,
\t\t\t\t  ctrl->rx_base, ctrl->rx_phys_base);
\t\tctrl->rx_base = NULL;
\t}
\tif (ctrl->tx_base) {
\t\tdma_free_coherent(ctrl->dev,
\t\t\t\t  (QCOM_SLIM_NGD_DESC_NUM + 1) * SLIM_MSGQ_BUF_LEN,
\t\t\t\t  ctrl->tx_base, ctrl->tx_phys_base);
\t\tctrl->tx_base = NULL;
\t}
''')
new=replace(new,'static void qcom_slim_ngd_setup(', 'static int qcom_slim_ngd_setup(')
new=replace(new,'''\tu32 cfg = readl_relaxed(ctrl->ngd->base);

\tif (ctrl->state == QCOM_SLIM_NGD_CTRL_DOWN ||
\t\tctrl->state == QCOM_SLIM_NGD_CTRL_ASLEEP)
\t\tqcom_slim_ngd_init_dma(ctrl);''',
'''\tu32 cfg = readl_relaxed(ctrl->ngd->base);
\tint ret;

\tif (ctrl->state == QCOM_SLIM_NGD_CTRL_DOWN ||
\t    ctrl->state == QCOM_SLIM_NGD_CTRL_ASLEEP) {
\t\tret = qcom_slim_ngd_init_dma(ctrl);
\t\tif (ret)
\t\t\treturn ret;
\t}''')
new=replace(new,'\twritel_relaxed(cfg, ctrl->ngd->base);\n}',
                '\twritel_relaxed(cfg, ctrl->ngd->base);\n\n\treturn 0;\n}')
new=replace(new,'\t\tqcom_slim_ngd_setup(ctrl);\n\t\treturn 0;',
                '\t\treturn qcom_slim_ngd_setup(ctrl);')
new=replace(new,'\tqcom_slim_ngd_setup(ctrl);\n\n\ttime_left',
                '\tret = qcom_slim_ngd_setup(ctrl);\n\tif (ret)\n\t\treturn ret;\n\n\ttime_left')
new=fn_replace(new,'qcom_slim_ngd_runtime_resume',lambda s:
    replace(replace(s,'\tif (!ctrl->qmi.handle)\n\t\treturn 0;',
                    '\tif (!ctrl->qmi.handle)\n\t\treturn -ENOTCONN;'),
            '\treturn 0;\n}', '\treturn ret;\n}'))
new=replace(new,'\t\t\tdev_err(ctrl->dev, "HW wakeup attempt during SSR\\n");',
'''\t\t\tdev_err(ctrl->dev, "HW wakeup attempt during SSR\\n");
\t\tdev_err_ratelimited(ctrl->dev,
\t\t\t\t    "NGD resume failed: ret=%d state=%d tx=%d rx=%d\\n",
\t\t\t\t    ret, ctrl->state, !!ctrl->dma_tx_channel,
\t\t\t\t    !!ctrl->dma_rx_channel);
\t\tqcom_slim_ngd_exit_dma(ctrl);''')
new=replace(new,'''\t\tcomplete(&ctrl->qmi.qmi_comp);
\t\tif (!pm_runtime_enabled(ctrl->ctrl.dev) ||
\t\t\t !pm_runtime_suspended(ctrl->ctrl.dev))
\t\t\tqcom_slim_ngd_runtime_resume(ctrl->ctrl.dev);
\t\telse
\t\t\tpm_runtime_resume(ctrl->ctrl.dev);
''',
'''\t\tcomplete_all(&ctrl->qmi.qmi_comp);
\t\tif (pm_runtime_enabled(ctrl->ctrl.dev)) {
\t\t\t/* SSR invalidates both DMA and the old runtime-PM state. */
\t\t\tpm_runtime_disable(ctrl->ctrl.dev);
\t\t\tif (ctrl->state == QCOM_SLIM_NGD_CTRL_DOWN)
\t\t\t\tret = pm_runtime_set_suspended(ctrl->ctrl.dev);
\t\t\tpm_runtime_enable(ctrl->ctrl.dev);
\t\t\tif (ret < 0)
\t\t\t\treturn ret;
\t\t\tret = pm_runtime_resume(ctrl->ctrl.dev);
\t\t} else {
\t\t\tret = qcom_slim_ngd_runtime_resume(ctrl->ctrl.dev);
\t\t}
\t\tif (ret < 0)
\t\t\treturn ret;
''')
new=fn_replace(new,'qcom_slim_ngd_runtime_suspend',lambda s:
    replace(replace(s,'\tqcom_slim_ngd_exit_dma(ctrl);\n\tif (!ctrl->qmi.handle)\n\t\treturn 0;',
'''\tif (!ctrl->qmi.handle) {
\t\tqcom_slim_ngd_exit_dma(ctrl);
\t\treturn 0;
\t}'''),
            '\tif (!ret || ret == -ETIMEDOUT)\n\t\tctrl->state = QCOM_SLIM_NGD_CTRL_ASLEEP;',
'''\tif (!ret) {
\t\tqcom_slim_ngd_exit_dma(ctrl);
\t\tctrl->state = QCOM_SLIM_NGD_CTRL_ASLEEP;
\t}'''))
changes[name]=(old,new)
patch=[]
for name,(before,after) in changes.items():
    assert before!=after
    (k/name).write_text(after)
    patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(ref/'ngd-pm-lifecycle.patch').write_text(''.join(patch))
report=dict(stage=166, modified_files=list(changes),
            source_sha256={n:hashlib.sha256((k/n).read_bytes()).hexdigest() for n in changes},
            resume_errors_propagated=True, core_aborts_failed_pm_get_and_balances_vote=True,
            setup_errors_propagated=True, partial_dma_init_unwound=True,
            coherent_buffers_freed_after_terminate=True, rejected_suspend_keeps_dma_and_state=True,
            qmi_readiness_persistent_until_disconnect=True, ssr_pm_state_reset_at_service_up=True,
            direct_tx_requires_both_dma_channels=True, physical_validation_pending=True)
for folder in [ref,out]:
    (folder/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
