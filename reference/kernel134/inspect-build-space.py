from pathlib import Path
import json
import runpy
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
k = Path('/home/cy122/pmos-samurai-kernel118/power132/kernel')
tracked = subprocess.check_output(['git', '-C', str(k), 'ls-files', '-z']).split(b'\0')
others = subprocess.check_output(['git', '-C', str(k), 'ls-files', '--others', '--exclude-standard', '-z']).split(b'\0')
source = [k / p.decode() for p in tracked + others if p]
source_bytes = sum(p.lstat().st_size for p in source)
source_blocks = sum(p.lstat().st_blocks * 512 for p in source)
log = Path('/mnt/e/edk2-samurai-out/kernel134/power132-directory-space-private.txt')
with log.open('x') as out:
    subprocess.run(['du', '-h', '--max-depth=1', str(k)], stdout=out, check=True, timeout=90)
print(json.dumps(dict(source_entries=len(source), source_bytes=source_bytes, source_allocated_bytes=source_blocks,
    inner_e118_free_bytes=shutil.disk_usage(k).free, host_e_free_bytes=shutil.disk_usage('/mnt/e').free,
    host_c_free_bytes=shutil.disk_usage('/mnt/c').free)), flush=True)
