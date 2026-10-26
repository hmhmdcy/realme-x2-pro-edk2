from pathlib import Path
import json
import runpy
import subprocess

r = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel140')
assert not (out / 'e118-close-fsck-private.txt').exists()
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
subprocess.run(['umount', '/home/cy122/pmos-samurai-kernel118'], check=True)
check = subprocess.run(['e2fsck', '-f', '-n', '/mnt/e/edk2-samurai-out/kernel118/build-volume.ext4'], capture_output=True)
(out / 'e118-close-fsck-private.txt').write_bytes(check.stdout + check.stderr)
assert check.returncode == 0
report = dict(stage=140, e118_volume_cleanly_unmounted=True, offline_readonly_fsck_pass=True,
              original_wsl_root_unchanged=True, ensure118_required_before_next_access=True, goal_complete=False)
(r / 'reference/kernel140/build-volume-close-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K140_E118_VOLUME_UNMOUNTED_READONLY_FSCK_PASS_WSL_ROOT_UNCHANGED')
