from pathlib import Path
import fcntl
import json
import os
import runpy
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
assert os.geteuid() == 0 and not (ref / 'candidate-volume-before-sparse-validation.json').exists()
assert json.loads((ref / 'kernel-build-validation.json').read_text())['full_image_modules_dtb_build_pass']
runpy.run_path(str(ref / 'ensure-build-volume.py'))
image = out / 'build-volume.ext4'
mount = Path('/home/cy122/pmos-samurai-build134')
with Path('/run/samurai-build-volume-locks/samurai-k134-mount.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    subprocess.run(['sync', '-f', str(mount)], check=True, timeout=30)
    subprocess.run(['umount', str(mount)], check=True, timeout=30)
    assert not mount.is_mount() and not subprocess.check_output(['losetup', '-j', str(image)], text=True).strip()
    with (out / 'volume-before-sparse-readonly-fsck-private.txt').open('x') as log:
        p = subprocess.run(['e2fsck', '-fn', str(image)], stdout=log, stderr=subprocess.STDOUT, timeout=90)
    assert p.returncode == 0
(ref / 'candidate-volume-before-sparse-validation.json').write_text(json.dumps(dict(stage=134,
    candidate_volume_unmounted=True, offline_readonly_fsck_exit=0,
    candidate_build_complete=True, original_wsl_vhd_untouched=True), indent=2) + '\n')
print('K134_NEW_CANDIDATE_VOLUME_CLOSED_AND_READONLY_FSCK_PASS', flush=True)
