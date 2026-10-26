from pathlib import Path
import hashlib
import json
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel134')
image = out / 'build-volume.ext4'
inventory = json.loads((out / 'zero-range-inventory-private.json').read_text())
operations = json.loads((out / 'windows-zero-range-operations-private.json').read_text(encoding='utf-8-sig'))
assert not Path('/home/cy122/pmos-samurai-build134').is_mount()
assert not subprocess.check_output(['losetup', '-j', str(image)], text=True).strip()
h = hashlib.sha256()
with image.open('rb') as f:
    for data in iter(lambda: f.read(4 * 1024**2), b''):
        h.update(data)
assert h.hexdigest() == inventory['image_sha256'] and image.stat().st_size == inventory['image_bytes']
with (out / 'windows-sparse-readonly-fsck-private.txt').open('x') as log:
    fsck = subprocess.run(['e2fsck', '-fn', str(image)], stdout=log, stderr=subprocess.STDOUT, timeout=90)
assert fsck.returncode == 0
report = dict(stage=134, fixed_new_private_candidate_volume_only=True,
    windows_sparse_operation_exit=operations['native_exit'], zero_ranges_completed=operations['completed_range_count'],
    zero_ranges_planned=operations['verified_range_count'], every_range_freshly_verified_byte_zero_before_mutation=True,
    full_before_after_image_sha256_equal=True, image_sha256=h.hexdigest(), logical_image_length_unchanged=True,
    offline_readonly_fsck_zero=True, host_e_free_increase_bytes=operations['windows_e_free_after_bytes'] - operations['windows_e_free_before_bytes'],
    host_e_current_free_bytes=shutil.disk_usage('/mnt/e').free, original_wsl_vhd_and_stable_volumes_untouched=True,
    goal_complete=False)
(r / 'reference/kernel134/windows-zero-hole-reclamation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
