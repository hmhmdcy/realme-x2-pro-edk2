from pathlib import Path
import json
import os
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel134')
image = out / 'build-volume.ext4'
mount = Path('/home/cy122/pmos-samurai-build134')
assert os.geteuid() == 0 and not image.exists() and not mount.exists()
assert shutil.disk_usage('/mnt/e').free > 10 * 1024**3
with image.open('xb') as f:
    f.truncate(8 * 1024**3)
with (out / 'mkfs-private.txt').open('x') as log:
    subprocess.run(['mkfs.ext4', '-F', '-m', '0', '-L', 'samurai-k134', str(image)],
                   stdout=log, stderr=subprocess.STDOUT, check=True, timeout=90)
mount.mkdir(mode=0o700)
report = dict(stage=134, private_e_kernel_only_volume_bytes=image.stat().st_size,
    volume_label='samurai-k134', existing_volumes_not_resized=True, original_wsl_vhd_unchanged=True,
    host_c_free_bytes=shutil.disk_usage('/mnt/c').free, host_e_free_bytes=shutil.disk_usage('/mnt/e').free,
    phone_unchanged=True)
(r / 'reference/kernel134/volume-create-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K134_PRIVATE_E_KERNEL_ONLY_VOLUME_CREATED', flush=True)
