from pathlib import Path
import subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel96')
kernel=Path('/home/cy122/x2pro-linux/linux')
paths=['drivers/net/wireless/ath/ath10k/qmi.c','drivers/net/wireless/ath/ath10k/qmi.h']
for name in paths:
    p=kernel/name
    assert p.read_bytes()==subprocess.check_output(['git','show','HEAD:'+name],cwd=kernel)
    backup=out/(p.name+'-before');assert not backup.exists();backup.write_bytes(p.read_bytes())
p=kernel/paths[0];s=p.read_text()
old='''	if (ret < 0)
		ath10k_err(ar, "failed to assign msa map permissions: %d\\n", ret);

	return ret;
'''
new='''	if (ret < 0)
		ath10k_err(ar, "failed to assign msa map permissions: %d\\n", ret);
	else
		mem_info->mapped = true;

	return ret;
'''
assert s.count(old)==1;s=s.replace(old,new)
old='''	src_perms = BIT(QCOM_SCM_VMID_MSS_MSA) | BIT(QCOM_SCM_VMID_WLAN);
'''
new='''	/* A failed or partial setup must not reclaim an unassigned region. */
	if (!mem_info->mapped)
		return 0;

	src_perms = BIT(QCOM_SCM_VMID_MSS_MSA) | BIT(QCOM_SCM_VMID_WLAN);
'''
assert s.count(old)==1;s=s.replace(old,new)
old='''	if (ret < 0)
		ath10k_err(ar, "failed to unmap msa permissions: %d\\n", ret);

	return ret;
'''
new='''	if (ret < 0)
		ath10k_err(ar, "failed to unmap msa permissions: %d\\n", ret);
	else
		mem_info->mapped = false;

	return ret;
'''
assert s.count(old)==1;s=s.replace(old,new)
old='''	cancel_work_sync(&qmi->event_work);
	destroy_workqueue(qmi->event_wq);
'''
new='''	cancel_work_sync(&qmi->event_work);
	/* Unbinding while the server is alive produces no SERVER_EXIT event. */
	ath10k_qmi_remove_msa_permission(qmi);
	destroy_workqueue(qmi->event_wq);
'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
p=kernel/paths[1];s=p.read_text();old='\tu32 size;\n\tbool secure;\n';new='\tu32 size;\n\tbool secure;\n\tbool mapped;\n'
assert s.count(old)==1;p.write_text(s.replace(old,new))
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel96')
(ref/'ath10k-qmi-unbind-msa.patch').write_bytes(subprocess.check_output(['git','diff','--',*paths],cwd=kernel))
subprocess.run(['git','diff','--check','--',*paths],cwd=kernel,check=True)
print('QMI ownership tracking and unbind reclamation prepared')
