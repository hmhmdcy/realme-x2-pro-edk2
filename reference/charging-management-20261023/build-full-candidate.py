"""Build only the reviewed OEM-Full charger in a separate private intree view.

The deployed r5 source, build tree, payload and manifest are never overwritten.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ref = Path(__file__).resolve().parent
revision = int(sys.argv[1]) if len(sys.argv) > 1 else 1
assert revision in (1, 2)
v1 = ref.parent / 'charging-session-20261023/full-integration-candidate'
candidate = v1 if revision == 1 else ref.parent / 'charging-session-20261023/kernel-v2'
receipt = json.loads((candidate / 'test-result.json').read_text())
assert receipt['passed']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name, expected in receipt['candidate_files'].items():
    assert sha(candidate / name) == expected, 'Candidate changed since tests: ' + name
assert all(receipt['baseline_production_unchanged' if revision == 1 else 'main_unchanged'].values())
baseline_dir = ref if revision == 1 else v1
for name, expected in receipt['baseline'].items():
    assert sha(baseline_dir / name) == expected, 'Candidate baseline changed: ' + name
main_baseline = json.loads((v1 / 'test-result.json').read_text())['baseline']
for name, expected in main_baseline.items():
    assert sha(ref / name) == expected, 'Deployed baseline changed: ' + name
sys.path.insert(0, str(ref.parent / 'kernel284'))
import storage
shared = storage.mounted_build()
original = shared.parent / 'source354'
private = Path('/home/cy122/charging-management-20261023') / ('oem-full-candidate' if revision == 1 else 'oem-full-candidate-v2')
source, build = private / 'source-view', private / 'kbuild'
source.mkdir(parents=True, exist_ok=True)

def branch(src, dst, path):
    # Same read-only source-view algorithm used for the deployed r5 build.
    dst.mkdir(exist_ok=True)
    for p in src.iterdir():
        if p.name == '.git': continue
        q = dst / p.name
        if p.name in path: branch(p, q, path[p.name])
        elif not q.exists() and not q.is_symlink(): q.symlink_to(p, target_is_directory=p.is_dir())

branch(original, source, {'drivers': {'power': {'supply': {}}}})
supply = source / 'drivers/power/supply'
mk = supply / 'Makefile'
if mk.is_symlink(): mk.unlink()
mk.write_text((original / 'drivers/power/supply/Makefile').read_text() +
              '\n# Isolated OEM Full candidate; no deployment\nobj-m += samurai-mp2650.o\n')
names = ['samurai-mp2650.c', 'mp2650-core.h', 'charge-cycle.h', 'charging-notify.h',
         'gauge-i2c.h', 'gauge-protocol.h', 'oem-profile.h', 'oem-full-cycle.h']
for n in names:
    target = supply / n
    assert not target.is_symlink()
    if not target.exists() or target.read_bytes() != (candidate / n).read_bytes(): shutil.copy2(candidate / n, target)
build.mkdir(exist_ok=True)
if not (build / '.config').exists(): shutil.copy2(shared / '.config', build / '.config')
for n in ['Module.symvers', 'vmlinux.symvers']:
    p = shared / n
    if p.exists(): shutil.copy2(p, build / n)
if not (build / 'vmlinux.o').exists(): (build / 'vmlinux.o').symlink_to(shared / 'vmlinux.o')
assert (build / 'vmlinux.o').is_symlink() and (build / 'vmlinux.o').resolve() == (shared / 'vmlinux.o').resolve()
env = dict(os.environ)
for n in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG']: env.pop(n, None)
command = ['make', '-C', str(source), 'O=' + str(build), 'ARCH=arm64',
           'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+', 'W=1', '-j4']
with (private / 'build.log').open('w') as log:
    for targets in [['modules_prepare'], ['drivers/power/supply/samurai-mp2650.ko']]:
        result = subprocess.run(command + targets, stdout=log, stderr=subprocess.STDOUT, env=env)
        if result.returncode:
            print((private / 'build.log').read_text()[-6000:]); raise SystemExit(result.returncode)
log = (private / 'build.log').read_text()
assert not re.search(r'warning:|error:|undefined!', log, re.I)
module = build / 'drivers/power/supply/samurai-mp2650.ko'
info = subprocess.check_output(['modinfo', str(module)], text=True)
assert 'intree:         Y' in info and (shared / 'include/config/kernel.release').read_text().strip() in info
def enabled_config(path):
    return {line.split('=', 1)[0]: line.split('=', 1)[1]
            for line in path.read_text().splitlines() if line.startswith('CONFIG_')}
original_config, candidate_config = enabled_config(shared / '.config'), enabled_config(build / '.config')
config_diff = {n: [original_config.get(n), candidate_config.get(n)]
               for n in original_config.keys() | candidate_config.keys()
               if original_config.get(n) != candidate_config.get(n)}
assert not config_diff, config_diff
assert (shared / 'include/config/kernel.release').read_bytes() == (build / 'include/config/kernel.release').read_bytes()
result = {'passed': True, 'revision': revision, 'installed': False, 'module': str(module), 'module_sha256': sha(module),
          'intree': True, 'modinfo': info, 'source_view': str(source), 'private_build': str(build),
          'sources': {n: sha(candidate / n) for n in names},
          'test_receipt_sha256': sha(candidate / 'test-result.json'),
          'configuration_differences': config_diff,
          'config_byte_identical': (build / '.config').read_bytes() == (shared / '.config').read_bytes(),
          'shared_config_sha256': sha(shared / '.config'), 'private_config_sha256': sha(build / '.config'),
          'main_r5_source_sha256': sha(ref / 'samurai-mp2650.c'),
          'shared_checkout_modified': False, 'phone_accessed': False}
(ref / ('oem-full-build-result.json' if revision == 1 else 'oem-full-v2-build-result.json')).write_text(json.dumps(result, indent=2) + '\n')
print(log[-1800:]); print(json.dumps(result, indent=2))
