from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
image = out / 'build-volume.ext4'
assert os.geteuid() == 0 and image.resolve() == Path('/mnt/e/edk2-samurai-out/kernel134/build-volume.ext4')
assert image.stat().st_size == 8 * 1024**3 and not image.is_symlink()
assert not Path('/home/cy122/pmos-samurai-build134').is_mount()
assert not subprocess.check_output(['losetup', '-j', str(image)], text=True).strip()
assert json.loads((ref / 'candidate-volume-before-sparse-validation.json').read_text())['offline_readonly_fsck_exit'] == 0
assert not (ref / 'zero-hole-reclamation-validation.json').exists()
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(4 * 1024**2), b''):
            h.update(data)
    return h.hexdigest()
before_digest = sha(image)
before_free = shutil.disk_usage('/mnt/e').free
(out / 'zero-hole-before-private.json').write_text(json.dumps(dict(image_sha256=before_digest,
    volume_bytes=image.stat().st_size, host_e_free_bytes=before_free), indent=2) + '\n')
print('K134_CLOSED_VOLUME_FULL_BYTE_HASH_SAVED_BEFORE_ZERO_HOLE_SCAN', flush=True)
timed_out = False
with (out / 'dig-zero-holes-private.txt').open('x') as log:
    try:
        p = subprocess.run(['fallocate', '--dig-holes', str(image)], stdout=log, stderr=subprocess.STDOUT, timeout=180)
        dig_exit = p.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        dig_exit = 124
        log.write('Bounded zero-hole scan exceeded 180 seconds; no replay; verify existing image bytes.\n')
after_digest = sha(image)
assert before_digest == after_digest
with (out / 'volume-after-sparse-readonly-fsck-private.txt').open('x') as log:
    fsck = subprocess.run(['e2fsck', '-fn', str(image)], stdout=log, stderr=subprocess.STDOUT, timeout=90)
assert fsck.returncode == 0
after_free = shutil.disk_usage('/mnt/e').free
report = dict(stage=134, target='private kernel134 build-volume.ext4 only', volume_bytes=image.stat().st_size,
    logical_image_length_unchanged=True, full_before_after_image_sha256_equal=True, image_sha256=after_digest,
    dig_zero_holes_exit=dig_exit, dig_zero_holes_timed_out=timed_out,
    host_e_before_free_bytes=before_free, host_e_after_free_bytes=after_free,
    host_e_free_increase_bytes=after_free - before_free, offline_readonly_fsck_before_after_zero=True,
    candidate_volume_stayed_unmounted=True, original_wsl_vhd_untouched=True, stable_volumes_untouched=True,
    goal_complete=False)
(ref / 'zero-hole-reclamation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
