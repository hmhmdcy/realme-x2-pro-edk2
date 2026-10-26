from pathlib import Path
import json
import runpy
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
stage = Path('/home/cy122/pmos-samurai-rootfs129')
with Path('/mnt/e/edk2-samurai-out/kernel134/rootfs-directory-space-private.txt').open('x') as log:
    subprocess.run(['du', '-h', '--max-depth=1', str(stage)], stdout=log, check=True, timeout=90)
print('K134_ROOTFS_VOLUME_INNER_FREE_BYTES', shutil.disk_usage(stage).free, flush=True)
print('K134_ROOTFS_STAGE_DIRECTORIES', json.dumps([p.name for p in stage.iterdir() if p.is_dir()]), flush=True)
