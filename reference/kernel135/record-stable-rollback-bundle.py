from pathlib import Path
import json
import hashlib
r=Path('/mnt/e/RealmeX2Pro edk2')
ref=r/'reference/kernel135'
runtime=json.loads((ref/'rollback-runtime-validation.json').read_text())
assert runtime['kernel_build']==132 and runtime['new_boot_verified'] and runtime['taint']==0
bundle=json.loads((r/'reference/kernel132/complete-bundle-validation.json').read_text())
assert bundle['matching_boot_logdump_rootfs_modules_complete'] and bundle['rootfs_generation']==132
artifacts=[]
for item in bundle['artifacts']:
    p=Path('/mnt/e')/item['artifact_path'].removeprefix('E:/')
    assert p.stat().st_size==item['bytes']
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024**2),b''):
            h.update(chunk)
    assert h.hexdigest()==item['sha256']
    artifacts.append(item)
report=dict(stage=135,current_kernel=132,current_matching_rootfs_generation=132,latest_candidate_rootfs_generation=134,matching_stable_four_artifact_hashes_fresh_verified=True,artifacts=artifacts,actual_new_boot_132_with_matching_modules_verified=True,userdata_bulk_image_not_flushed_or_erased=True,automatic_desktop_processes_recovered=True,full_automatic_display_acceptance=False,gpu_overall_acceptance=False,charging_control_accepted=False,goal_complete=False)
(ref/'stable-rollback-bundle-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K135_CURRENT132_MATCHING_STABLE_FOUR_ARTIFACTS_FULL_FRESH_SHA_PASS',flush=True)
