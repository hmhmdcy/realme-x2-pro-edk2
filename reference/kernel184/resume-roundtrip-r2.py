"""Resume preparation after upload failed before a device transition began."""
from pathlib import Path
import os
import subprocess
import sys
import host

assert not (host.PRIVATE / 'r2-reboot-request-private.json').exists()
host.ssh('test ! -e /var/lib/samurai/k184r2-preflash && test ! -e /var/lib/samurai/k184r2-tools && mkdir -m700 /var/lib/samurai/k184r2-tools')
folder = host.PRIVATE / 'reboot-r2-tools-private'
env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent))
for name in ['prepare-reboot.py', 'quiesce-and-archive.py', 'reboot-current.py', 'fastboot-reboot-current.py']:
    argv = [sys.executable, str(folder / name)]
    if name == 'prepare-reboot.py':
        argv.append('--capture')
    subprocess.run(argv, env=env, check=True)
