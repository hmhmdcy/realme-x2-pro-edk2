"""Compile only the external candidate in its private module/output directories."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

ref = Path(__file__).resolve().parent
sys.path.insert(0, str(ref.parent / 'kernel284'))
import storage
shared = storage.mounted_build()
private = Path('/home/cy122/charging-management-20261023')
module = private / 'module'
module.mkdir(exist_ok=True)
for name in ['Makefile', 'samurai-mp2650.c', 'mp2650-core.h', 'oem-profile.h',
             'samurai-usb-input.c', 'samurai-usb-input-decode.h',
             'gauge-protocol.h', 'gauge-i2c.h', 'samurai-gauge-protection.c']:
    shutil.copy2(ref / name, module / name)
env = dict(os.environ)
env.pop('KBUILD_OUTPUT', None)
cmd = ['make', '-C', str(private / 'kbuild'), 'M=' + str(module),
       'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-', 'W=1', '-j4', 'modules']
with (private / 'build.log').open('w') as log:
    result = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
if result.returncode:
    print((private / 'build.log').read_text())
    raise SystemExit(result.returncode)
ko = module / 'samurai-mp2650.ko'
report = {'command': cmd, 'module': str(ko),
          'module_sha256': hashlib.sha256(ko.read_bytes()).hexdigest(),
          'module_bytes': ko.stat().st_size,
          'modinfo': subprocess.check_output(['modinfo', str(ko)], text=True),
          'build_log': (private / 'build.log').read_text(),
          'phone_accessed': False, 'shared_build_written': False}
observer = module / 'samurai-usb-input.ko'
report['input_observer'] = {'path': str(observer),
    'sha256': hashlib.sha256(observer.read_bytes()).hexdigest(),
    'modinfo': subprocess.check_output(['modinfo', str(observer)], text=True)}
protection = module / 'samurai-gauge-protection.ko'
report['protection_observer'] = {'path': str(protection),
    'sha256': hashlib.sha256(protection.read_bytes()).hexdigest(),
    'modinfo': subprocess.check_output(['modinfo', str(protection)], text=True)}
(ref / 'build-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
