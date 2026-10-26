"""Prepare an independent O= tree; shared camera build is read only."""
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
source = shared.parent / 'source354'
private = Path('/home/cy122/charging-management-20261023')
build = private / 'kbuild'
build.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = {str(shared / n): sha(shared / n) for n in
          ['.config', 'Module.symvers', 'include/config/kernel.release']}
if not (build / '.config').exists():
    shutil.copy2(shared / '.config', build / '.config')
env = dict(os.environ)
env.pop('KBUILD_OUTPUT', None)
env.pop('KCONFIG_CONFIG', None)
cmd = ['make', '-C', str(source), 'O=' + str(build), 'ARCH=arm64',
       'CROSS_COMPILE=aarch64-linux-gnu-', '-j4', 'modules_prepare']
with (private / 'prepare.log').open('w') as log:
    subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
shutil.copy2(shared / 'Module.symvers', build / 'Module.symvers')
assert (build / 'include/config/kernel.release').read_bytes() == (
    shared / 'include/config/kernel.release').read_bytes()
assert before == {p: sha(Path(p)) for p in before}
report = {'source': str(source), 'private_build': str(build),
          'release': (build / 'include/config/kernel.release').read_text().strip(),
          'shared_inputs_unchanged': True, 'command': cmd}
(ref / 'prepare-build-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
