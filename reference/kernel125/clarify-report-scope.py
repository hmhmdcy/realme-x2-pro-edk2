from pathlib import Path
import json
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel125'
p=ref/'cpas-iova-port-validation.json';data=json.loads(p.read_text());assert data.pop('actual_reservations_required_before_probe')
data.update(iommu_reservation_callback_policy_required_before_probe=True,opaque_dma_allocator_cookie_not_inspected=True)
p.write_text(json.dumps(data,indent=2)+'\n')
p=ref/'port-cpas-iova.py';s=p.read_text().replace('actual_reservations_required_before_probe=True','iommu_reservation_callback_policy_required_before_probe=True,opaque_dma_allocator_cookie_not_inspected=True');p.write_text(s)
p=ref/'stack-recovery-validation.json';data=json.loads(p.read_text());assert data['stack_count_recovered']==0
data.pop('both_backings_verified_same_task_image');data.update(two_stacked_mounts_observed_by_prior_findmnt_losetup=True,prior_backings_verified_same_task_image=True,wsl_already_unmounted_before_recovery_script=True,recovery_script_explicitly_unmounted_mounts=0)
p.write_text(json.dumps(data,indent=2)+'\n')
print('K125_REPORT_CALLBACK_POLICY_AND_AUTOMATIC_UNMOUNT_SCOPE_CLARIFIED')
