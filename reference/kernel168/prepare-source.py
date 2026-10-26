from pathlib import Path
import difflib, hashlib, json, subprocess, shutil

root=Path('/mnt/e/RealmeX2Pro edk2/reference');ref=root/'kernel168'
out=Path('/mnt/e/edk2-samurai-out/kernel168');assert not out.exists();out.mkdir(mode=0o700)
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
(out/'source166-rejected-private.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=k))
shutil.copyfile(k/'.config',out/'config-before-private')
name='drivers/slimbus/qcom-ngd-ctrl.c';old=(k/name).read_text();new=old
def replace(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)
new=replace(new,'\tenum qcom_slim_ngd_state state;','\tenum qcom_slim_ngd_state state;\n\tbool registered;')
new=replace(new,'\t\tif (ctrl->state == QCOM_SLIM_NGD_CTRL_DOWN)\n\t\t\tqcom_slim_ngd_notify_slaves(ctrl);\n','')
new=replace(new,'\tif (enable) {\n\t\tint ret = qcom_slim_qmi_init(ctrl, false);',
'''\tif (enable) {
\t\tint ret;

\t\tif (ctrl->registered)
\t\t\treturn 0;
\t\tret = qcom_slim_qmi_init(ctrl, false);''')
new=replace(new,'\t\tdev_info(ctrl->dev, "SLIM controller Registered\\n");',
'''\t\tctrl->registered = true;
\t\t/* Client callbacks require an initialized, registered controller. */
\t\tqcom_slim_ngd_notify_slaves(ctrl);
\t\tdev_info(ctrl->dev, "SLIM controller Registered\\n");''')
new=replace(new,'\t\tslim_unregister_controller(&ctrl->ctrl);',
'''\t\tif (ctrl->registered) {
\t\t\tslim_unregister_controller(&ctrl->ctrl);
\t\t\tctrl->registered = false;
\t\t}''')
new=replace(new,'\tcomplete(&ctrl->qmi_up);','\tcomplete_all(&ctrl->qmi_up);')
new=replace(new,'''\tmutex_lock(&ctrl->ssr_lock);
\tdevice_for_each_child(ctrl->ctrl.dev, NULL,
\t\t\t      qcom_slim_ngd_update_device_status);
\tqcom_slim_ngd_enable(ctrl, false);
\tmutex_unlock(&ctrl->ssr_lock);''',
'''\tmutex_lock(&ctrl->ssr_lock);
\tif (ctrl->state == QCOM_SLIM_NGD_CTRL_DOWN && !ctrl->registered)
\t\tgoto unlock;

\tpm_runtime_get_noresume(ctrl->ctrl.dev);
\tctrl->state = QCOM_SLIM_NGD_CTRL_DOWN;
\tqcom_slim_qmi_exit(ctrl);
\t/* Drain master work before removing any device it could reference. */
\tcancel_work_sync(&ctrl->m_work);
\tdevice_for_each_child(ctrl->ctrl.dev, NULL,
\t\t\t      qcom_slim_ngd_update_device_status);
\tqcom_slim_ngd_enable(ctrl, false);
\tmutex_lock(&ctrl->tx_lock);
\tqcom_slim_ngd_exit_dma(ctrl);
\tmutex_unlock(&ctrl->tx_lock);
unlock:
\tmutex_unlock(&ctrl->ssr_lock);''')
new=replace(new,'''\t\tif (ctrl->state != QCOM_SLIM_NGD_CTRL_DOWN) {
\t\t\tpm_runtime_get_noresume(ctrl->ctrl.dev);
\t\t\tctrl->state = QCOM_SLIM_NGD_CTRL_DOWN;
\t\t\tqcom_slim_ngd_down(ctrl);
\t\t\tqcom_slim_ngd_exit_dma(ctrl);
\t\t}''','\t\tqcom_slim_ngd_down(ctrl);')
(k/name).write_text(new)
(ref/'ngd-service-lifecycle-from166.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
source=json.loads((root/'kernel166/source-validation.json').read_text())
source.update(stage=168,rejected_candidate166=True,master_callback_deferred_until_controller_registered=True,
              master_work_drained_before_client_removal=True,ssr_dma_teardown_inside_ssr_lock=True,
              controller_register_unregister_idempotent=True,qmi_server_readiness_persistent=True)
source['source_sha256'][name]=hashlib.sha256((k/name).read_bytes()).hexdigest()
for folder in [ref,out]: (folder/'source-validation.json').write_text(json.dumps(source,indent=2)+'\n')
for n in ['test-pm-stubs.h','test-pm-main.c','test-codec-stubs.h','run-tests.py','test-transactions.py','build-package.py','collect-runtime.py']:
    text=(root/'kernel166'/n).read_text().replace('kernel166','kernel168').replace('stage=166','stage=168').replace('K166','K168').replace('k166','k168')
    if n=='build-package.py':
        text=text.replace("KBUILD_BUILD_VERSION='166'","KBUILD_BUILD_VERSION='168'").replace('#166 SMP','#168 SMP').replace('kernel_build=166','kernel_build=168').replace("'166'","'168'")
    (ref/n).write_text(text)
for n in ['qcom-ngd-ctrl.c.163-before-private','wcd934x.c.163-before-private']:
    shutil.copyfile(out.parent/'kernel166'/n,out/n)
print('K168_SERVICE_LIFECYCLE_CANDIDATE_PREPARED_BASELINE163')
