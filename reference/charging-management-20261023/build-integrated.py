"""Build genuine in-tree modules in a private source view and O= directory.

All shared source entries are read-only references. Only the private power
supply Makefile and new candidate files differ. No MODULE_INFO is forged.
"""
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
original = shared.parent / 'source354'
private = Path('/home/cy122/charging-management-20261023')
source = private / 'source-view'
build = private / 'kbuild-integrated'

def branch(src, dst, path):
    dst.mkdir(exist_ok=True)
    for p in src.iterdir():
        if p.name == '.git':
            continue
        q = dst / p.name
        if p.name in path:
            branch(p, q, path[p.name])
        elif not q.exists() and not q.is_symlink():
            q.symlink_to(p, target_is_directory=p.is_dir())

source.mkdir(exist_ok=True)
branch(original, source, {'drivers': {'power': {'supply': {}}}})
supply = source / 'drivers/power/supply'
mk = supply / 'Makefile'
if mk.is_symlink():
    mk.unlink()  # Exact private symlink only; never its shared target.
mk.write_text((original / 'drivers/power/supply/Makefile').read_text() +
    '\n# RMX1931 isolated charging integration\nobj-m += samurai-mp2650.o\n'
    'obj-m += samurai-usb-input.o\nobj-m += samurai-gauge-protection.o\n')
files = ['samurai-mp2650.c', 'mp2650-core.h', 'charge-cycle.h', 'charging-notify.h', 'oem-profile.h', 'gauge-protocol.h',
         'gauge-i2c.h', 'samurai-usb-input.c', 'samurai-usb-input-decode.h',
         'samurai-gauge-protection.c']
for name in files:
    p = supply / name
    assert not p.is_symlink()
    if not p.exists() or p.read_bytes() != (ref / name).read_bytes():
        shutil.copy2(ref / name, p)
build.mkdir(exist_ok=True)
if not (build / '.config').exists():
    shutil.copy2(shared / '.config', build / '.config')
for name in ['Module.symvers', 'vmlinux.symvers']:
    src = shared / name
    if src.exists() and (not (build / name).exists() or (build / name).read_bytes() != src.read_bytes()):
        shutil.copy2(src, build / name)
vmlinux = build / 'vmlinux.o'
if not vmlinux.exists():
    vmlinux.symlink_to(shared / 'vmlinux.o')
assert vmlinux.is_symlink() and vmlinux.resolve() == (shared / 'vmlinux.o').resolve()
env = dict(os.environ)
for name in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG']:
    env.pop(name, None)
common = ['make', '-C', str(source), 'O=' + str(build), 'ARCH=arm64',
          'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+', 'W=1', '-j4']
requested = sys.argv[1:] or ['samurai-mp2650', 'samurai-usb-input', 'samurai-gauge-protection']
assert requested and set(requested) <= {'samurai-mp2650', 'samurai-usb-input', 'samurai-gauge-protection'}
with (private / 'integrated-build.log').open('w') as log:
    for targets in [['modules_prepare'], ['drivers/power/supply/' + n + '.ko' for n in requested]]:
        q = subprocess.run(common + targets, env=env, stdout=log, stderr=subprocess.STDOUT)
        if q.returncode:
            print((private / 'integrated-build.log').read_text()[-12000:])
            raise SystemExit(q.returncode)
print((private / 'integrated-build.log').read_text()[-10000:])
result = {'source_view': str(source), 'private_build': str(build), 'modules': {},
          'sources': {n: hashlib.sha256((ref / n).read_bytes()).hexdigest() for n in files}}
assert (shared / 'include/config/kernel.release').read_bytes() == (build / 'include/config/kernel.release').read_bytes()
old_config = {l.split('=')[0]: l for l in (shared / '.config').read_text().splitlines() if l.startswith('CONFIG_')}
new_config = {l.split('=')[0]: l for l in (build / '.config').read_text().splitlines() if l.startswith('CONFIG_')}
diff = {n: [old_config.get(n), new_config.get(n)] for n in old_config.keys() | new_config.keys()
        if old_config.get(n) != new_config.get(n)}
result['configuration_differences'] = diff
assert all(n.startswith('CONFIG_VIDEO_QCOM_CAMSS') for n in diff), diff
for name in ['samurai-mp2650', 'samurai-usb-input', 'samurai-gauge-protection']:
    ko = build / 'drivers/power/supply' / (name + '.ko')
    assert ko.exists(), ko
    if ko.exists():
        info = subprocess.check_output(['modinfo', str(ko)], text=True)
        assert 'intree:         Y' in info
        assert (shared / 'include/config/kernel.release').read_text().strip() in info
        result['modules'][name] = {'path': str(ko), 'modinfo': info,
            'sha256': hashlib.sha256(ko.read_bytes()).hexdigest()}
assert len(result['modules']) == 3
(ref / 'integrated-build-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
