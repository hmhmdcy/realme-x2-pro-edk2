"""Build the tested OEM temperature-band change in a private k363 source view."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

REF = Path(__file__).resolve().parent
CANDIDATE = REF.parent / 'charging-session-20261023/thermal-bands-candidate'
BASE = CANDIDATE.parent / 'kernel-v2'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
tested = json.loads((CANDIDATE / 'test-result.json').read_bytes())
assert tested['passed'] and tested['frozen_v2_unchanged']
assert tested['tests']['test-differential']['result']['oracle_general_band_equal']
assert tested['tests']['test-step']['result']['passed']
for name, expected in tested['files'].items():
    assert sha(CANDIDATE / name) == expected, name
for name, expected in tested['baseline'].items():
    assert sha(BASE / name) == expected, name
names = list(tested['baseline']) + ['thermal-bands.h']
inputs = {name: (CANDIDATE if name in tested['files'] else BASE) / name
          for name in names}

sys.path.insert(0, str(REF.parent / 'kernel284'))
import storage
shared = storage.mounted_build()
original = shared.parent / 'source354'
release = (shared / 'include/config/kernel.release').read_text().strip()
assert release == '7.3.0-rc6-rmx1931-samurai-k363+'
assert (original / 'drivers/power/supply/Makefile').is_file()
private = Path('/home/cy122/charging-management-20261023/thermal-bands-candidate')
source, build = private / 'source-view', private / 'kbuild'
source.mkdir(parents=True, exist_ok=True)


def branch(src, dst, selected):
    dst.mkdir(exist_ok=True)
    for item in src.iterdir():
        if item.name == '.git':
            continue
        target = dst / item.name
        if item.name in selected:
            assert not target.is_symlink()
            branch(item, target, selected[item.name])
        elif not target.exists() and not target.is_symlink():
            target.symlink_to(item, target_is_directory=item.is_dir())


branch(original, source, {'drivers': {'power': {'supply': {}}}})
supply = source / 'drivers/power/supply'
makefile = supply / 'Makefile'
if makefile.is_symlink():
    makefile.unlink()
makefile.write_text((original / 'drivers/power/supply/Makefile').read_text() +
                    '\n# Private OEM thermal-band module only\nobj-m += samurai-mp2650.o\n')
for name, origin in inputs.items():
    target = supply / name
    assert not target.is_symlink()
    if not target.exists() or target.read_bytes() != origin.read_bytes():
        shutil.copy2(origin, target)
build.mkdir(exist_ok=True)
if not (build / '.config').exists():
    shutil.copy2(shared / '.config', build / '.config')
for name in ['Module.symvers', 'vmlinux.symvers']:
    if (shared / name).exists():
        shutil.copy2(shared / name, build / name)
if not (build / 'vmlinux.o').exists():
    (build / 'vmlinux.o').symlink_to(shared / 'vmlinux.o')
assert (build / 'vmlinux.o').is_symlink()
assert (build / 'vmlinux.o').resolve() == (shared / 'vmlinux.o').resolve()
environment = dict(os.environ)
for name in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG']:
    environment.pop(name, None)
command = ['make', '-C', str(source), 'O=' + str(build), 'ARCH=arm64',
           'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+', 'W=1', '-j4']
with (private / 'build.log').open('w') as log:
    for target in ['modules_prepare', 'drivers/power/supply/samurai-mp2650.ko']:
        result = subprocess.run(command + [target], env=environment,
                                stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            print((private / 'build.log').read_text()[-4000:])
            raise SystemExit(result.returncode)
log = (private / 'build.log').read_text()
assert not re.search(r'warning:|error:|undefined!', log, re.I)
module = build / 'drivers/power/supply/samurai-mp2650.ko'
info = subprocess.check_output(['modinfo', str(module)], text=True)
assert release in info and 'intree:         Y' in info


def config_values(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines()
                if line.startswith('CONFIG_'))


assert config_values(shared / '.config') == config_values(build / '.config')
assert (shared / 'include/config/kernel.release').read_bytes() == (build / 'include/config/kernel.release').read_bytes()
for name, origin in inputs.items():
    assert sha(supply / name) == sha(origin)
result = dict(passed=True, installed=False, module=str(module),
              module_sha256=sha(module), intree=True, modinfo=info,
              source_view=str(source), private_build=str(build),
              sources={name: sha(path) for name, path in inputs.items()},
              test_receipt_sha256=sha(CANDIDATE / 'test-result.json'),
              configuration_differences={},
              shared_config_sha256=sha(shared / '.config'),
              private_config_sha256=sha(build / '.config'),
              shared_source_modified=False, phone_accessed=False,
              image_rebuilt=False, sdk_invoked=False)
(REF / 'thermal-bands-build-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
