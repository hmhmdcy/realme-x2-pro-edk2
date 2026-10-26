"""Generate a fresh namespace for a second, independently guarded round-trip."""
from pathlib import Path
import os
import subprocess
import sys

ref = Path(__file__).resolve().parent
scratch = ref / 'reboot-r2'
scratch.mkdir(exist_ok=True)
private = Path('/mnt/e/edk2-samurai-out/kernel184/reboot-r2-tools-private')
private.mkdir(exist_ok=True)
env = dict(os.environ, PYTHONPATH=str(ref))
for name in ['prepare-reboot.py', 'quiesce-and-archive.py', 'reboot-current.py', 'fastboot-reboot-current.py']:
    text = (ref / name).read_text().replace('k184', 'k184r2')
    text = text.replace("host.PRIVATE / '", "host.PRIVATE / 'r2-")
    if name == 'prepare-reboot.py':
        text = text.replace('ref = Path(__file__).resolve().parent', 'ref = Path(' + repr(str(scratch)) + ')')
        text = text.replace("old = ref.parent / 'kernel183'", "old = ref.parent.parent / 'kernel183'")
    if name == 'quiesce-and-archive.py':
        text = text.replace('k184r2-baseline k184r2-baseline-r2 k184r2-sensor-light-v1 k184r2-sensor-light-v2 k184r2-libssc-r2',
                            'k184-sensor-light-v3 k184-reboot-runtime')
    dest = private / name
    assert not dest.exists()
    dest.write_text(text)
    subprocess.run([sys.executable, '-m', 'py_compile', str(dest)], check=True)
print('Fresh namespace prepared; no device transition requested.', flush=True)
if sys.argv[1:] != ['--run']:
    raise SystemExit(0)
import host
host.ssh('test ! -e /var/lib/samurai/k184r2-tools && mkdir -m700 /var/lib/samurai/k184r2-tools')
for name in ['prepare-reboot.py', 'quiesce-and-archive.py', 'reboot-current.py', 'fastboot-reboot-current.py']:
    argv = [sys.executable, str(private / name)]
    if name == 'prepare-reboot.py':
        argv.append('--capture')
    subprocess.run(argv, env=env, check=True)
