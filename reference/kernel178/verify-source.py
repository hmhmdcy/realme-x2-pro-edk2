from pathlib import Path
import hashlib, json, subprocess

ref = Path(__file__).parent
kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
base = json.loads((ref.parent / 'kernel176/source-validation.json').read_text())['source_sha256']
current = {p: hashlib.sha256((kernel / p).read_bytes()).hexdigest() for p in base}
assert current == base
extra_paths = ['drivers/remoteproc/remoteproc_core.c', 'drivers/remoteproc/remoteproc_sysfs.c',
               'drivers/remoteproc/qcom_common.c', 'drivers/soc/qcom/pdr_interface.c',
               'drivers/soc/qcom/qmi_interface.c', 'include/linux/mfd/wcd934x/wcd934x.h']
extra = {p: hashlib.sha256((kernel / p).read_bytes()).hexdigest() for p in extra_paths}
pdr = (kernel / 'drivers/soc/qcom/pdr_interface.c').read_text()
qmi = (kernel / 'drivers/soc/qcom/qmi_interface.c').read_text()
config = [l for l in (kernel / '.config').read_text().splitlines() if any(k in l for k in ['CONFIG_QCOM_PDR_HELPERS=', 'CONFIG_QCOM_QMI_HELPERS=', 'CONFIG_MFD_WCD934X=', 'CONFIG_SND_SOC_WCD934X='])]
report = dict(stage=178, deployed_kernel_build=176, kernel_sources_unchanged_from176=True,
              source_sha256=current, investigated_source_sha256=extra, relevant_config=config,
              pdr_notifier_waits_under_list_lock=True, stale_down_after_new_up_is_hypothesis_not_proven=True,
              host_concurrency_reproduction_and_fix_not_yet_completed=True, no_kernel_build_or_flash=True,
              remoteproc_documentation='https://docs.kernel.org/staging/remoteproc.html',
              ngd_lock_discussion='https://lists.openwall.net/linux-kernel/2026/03/31/2370')
assert 'qmi_txn_wait(&txn, 5 * HZ)' in pdr and 'pdr_notifier_del_server' in pdr
assert 'ops->del_server(qmi, svc)' in qmi
(ref / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(stage=178, sources_unchanged=True, relevant_config=config)))
