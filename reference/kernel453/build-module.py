"""Build only BU64253 in its own source view and O= tree; shared inputs read only."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel453')
spec = importlib.util.spec_from_file_location('build_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
SHARED = storage.mount.mounted_build()
ORIGINAL = SHARED.parent / 'source354'
ISOLATED = SHARED.parent / 'kernel453-lens-private'
SOURCE = ISOLATED / 'source-view'
BUILD = ISOLATED / 'O'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

release = (SHARED / 'include/config/kernel.release').read_text().strip()
assert release == '7.3.0-rc6-rmx1931-samurai-k363+'
kernel363 = json.loads((HERE.parent / 'kernel363/boot-candidate-build-validation.json').read_text())
image = PRIVATE.parent / 'kernel363/Image-k363-private'
assert sha(image) == kernel363['artifacts']['arch/arm64/boot/Image']['sha256']
extract = subprocess.run([str(ORIGINAL / 'scripts/extract-ikconfig'), str(image)], capture_output=True)
if not extract.returncode:
    (PRIVATE / 'image363-config-private').write_bytes(extract.stdout)
    image_config = extract.stdout
else:
    image_config = None
inspection = dict(release=release, shared_config_sha256=sha(SHARED / '.config'),
                  image363_config_recorded_sha256=kernel363['artifacts']['.config']['sha256'],
                  embedded_config_extracted=image_config is not None,
                  embedded_config_sha256=hashlib.sha256(image_config).hexdigest() if image_config else None,
                  shared_symvers_sha256=sha(SHARED / 'Module.symvers'),
                  relevant_config=[l for l in (SHARED / '.config').read_text().splitlines()
                                   if l.startswith(('CONFIG_IKCONFIG', 'CONFIG_MODVERSIONS', 'CONFIG_FW_LOADER', 'CONFIG_MEDIA_CONTROLLER', 'CONFIG_VIDEO_V4L2_SUBDEV_API', 'CONFIG_PREEMPT', 'CONFIG_MODULE_', 'CONFIG_GCC_VERSION', 'CONFIG_CC_VERSION_TEXT'))],
                  isolated_path_exists=ISOLATED.exists(), free_bytes=shutil.disk_usage(SHARED).free)
(PRIVATE / 'build-inspection-private.json').write_text(json.dumps(inspection, indent=2) + '\n')
if '--inspect' in sys.argv:
    print(json.dumps(inspection, indent=2)); raise SystemExit(0)

assert image_config is not None
assert hashlib.sha256(image_config).hexdigest() == kernel363['artifacts']['.config']['sha256']
assert sha(SHARED / 'Module.symvers') == kernel363['artifacts']['Module.symvers']['sha256']

def snapshot():
    paths = [SHARED / n for n in ['.config', 'Module.symvers', 'include/config/kernel.release',
                                  'include/config/auto.conf', 'include/generated/autoconf.h',
                                  'include/generated/utsrelease.h']]
    paths += [ORIGINAL / 'drivers/media/i2c' / n for n in ['Makefile', 'Kconfig']]
    paths += [ORIGINAL / 'include/media' / n for n in ['media-entity.h', 'v4l2-subdev.h']]
    return {str(p): sha(p) for p in paths}

before = snapshot()
ISOLATED.mkdir(exist_ok=True)

def branch(src, dst, owned):
    dst.mkdir(exist_ok=True)
    for p in src.iterdir():
        if p.name == '.git':
            continue
        q = dst / p.name
        if p.name in owned:
            assert not q.is_symlink(), q
            branch(p, q, owned[p.name])
        elif not q.exists() and not q.is_symlink():
            q.symlink_to(p, target_is_directory=p.is_dir())

branch(ORIGINAL, SOURCE, {'drivers': {'media': {'i2c': {}}}})
i2c = SOURCE / 'drivers/media/i2c'
makefile = i2c / 'Makefile'
if makefile.is_symlink():
    makefile.unlink()
makefile.write_text((ORIGINAL / 'drivers/media/i2c/Makefile').read_text() +
                    '\n# Isolated kernel453 BU64253 integration\nobj-m += bu64253.o\n')
candidate = i2c / 'bu64253.c'
assert not candidate.is_symlink()
shutil.copyfile(HERE / 'bu64253.c', candidate)
BUILD.mkdir(exist_ok=True)
if not (BUILD / '.config').exists():
    (BUILD / '.config').write_bytes(image_config)
for name in ['Module.symvers', 'vmlinux.symvers']:
    if (SHARED / name).exists():
        shutil.copyfile(SHARED / name, BUILD / name)
vmlinux = BUILD / 'vmlinux.o'
if not vmlinux.exists():
    vmlinux.symlink_to(SHARED / 'vmlinux.o')
assert vmlinux.is_symlink() and vmlinux.resolve() == (SHARED / 'vmlinux.o').resolve()

attempt = 1
while (PRIVATE / ('module-build-r' + str(attempt) + '-private.log')).exists():
    attempt += 1
logfile = PRIVATE / ('module-build-r' + str(attempt) + '-private.log')
temporary = ISOLATED / 'tmp'
temporary.mkdir(exist_ok=True)
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_USER='builder',
           KBUILD_BUILD_HOST='samurai', KBUILD_BUILD_VERSION='363', TMPDIR=str(temporary))
for name in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG']:
    env.pop(name, None)
common = ['make', '-C', str(SOURCE), 'O=' + str(BUILD), 'ARCH=arm64',
          'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+',
          'KERNELRELEASE=' + release, 'W=1', 'KCFLAGS=-Werror', '-j3']
phases = []; started = time.monotonic(); ret = None
targets_to_run = [['olddefconfig'], ['modules_prepare'], ['drivers/media/i2c/bu64253.ko']]
if '--reuse-prepared' in sys.argv:
    assert (BUILD / 'include/config/kernel.release').read_text().strip() == release
    assert all((BUILD / n).is_file() for n in ['include/generated/autoconf.h', 'include/generated/utsrelease.h', 'include/config/auto.conf'])
    prior = json.loads((HERE / 'module-build-validation.json').read_text())
    assert prior['passed'] and prior['image363_config_sha256'] == hashlib.sha256(image_config).hexdigest()
    targets_to_run = [['drivers/media/i2c/bu64253.ko']]
with logfile.open('xb') as log:
    for targets in targets_to_run:
        begin = time.monotonic()
        proc = subprocess.Popen(common + targets, env=env, stdout=log, stderr=subprocess.STDOUT)
        state = dict(stage=453, attempt=attempt, terminal=False, pid=proc.pid, target=targets,
                     source_view=str(SOURCE), build=str(BUILD))
        (PRIVATE / 'module-build-state-private.json').write_text(json.dumps(state) + '\n')
        print(json.dumps(state), flush=True)
        ret = proc.wait()
        phases.append(dict(target=targets[0], exit=ret, seconds=round(time.monotonic() - begin, 3)))
        if ret:
            break
assert snapshot() == before, 'A tracked shared input changed; inspect before any further operation'
config_map = lambda raw: {l.split('=', 1)[0]: l for l in raw.decode().splitlines() if l.startswith('CONFIG_') or l.startswith('# CONFIG_')}
a = config_map(image_config); b = config_map((BUILD / '.config').read_bytes())
config_diff = {k: [a.get(k), b.get(k)] for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
assert all('VIDEO_QCOM_CAMSS' in k for k in config_diff), config_diff
diagnostics = [l for l in logfile.read_text(errors='replace').splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()]
report = dict(stage=453, attempt=attempt, phases=phases, exit=ret, seconds=round(time.monotonic() - started, 3),
              kernel_release=release, image363_config_exactly_extracted=True,
              image363_config_sha256=hashlib.sha256(image_config).hexdigest(),
              input_module_symvers_exactly_image363=True, original_source_head=subprocess.check_output(['git', '-C', str(ORIGINAL), 'rev-parse', 'HEAD'], text=True).strip(),
              configuration_differences_from_image363=config_diff,
              driver_source_sha256=sha(HERE / 'bu64253.c'), shared_inputs_unchanged=True,
              reused_private_preparation='--reuse-prepared' in sys.argv,
              private_source_view_and_output=True, shared_source_or_build_written=False,
              sdk_or_phone_accessed=False, installed_or_loaded=False,
              diagnostics=diagnostics, passed=ret == 0 and not diagnostics)
if not ret:
    ko = BUILD / 'drivers/media/i2c/bu64253.ko'
    output = PRIVATE / ('bu64253-intree-r' + str(attempt) + '.ko')
    shutil.copyfile(ko, output)
    get = lambda name: subprocess.check_output(['modinfo', '-F', name, str(output)], text=True).strip()
    imported = sorted({l.split()[-1] for l in subprocess.check_output(['aarch64-linux-gnu-nm', '-u', str(output)], text=True).splitlines() if l.strip()})
    available = {l.split()[1] for l in (SHARED / 'Module.symvers').read_text().splitlines()}
    assert set(imported) <= available, set(imported) - available
    assert get('intree') == 'Y' and get('vermagic').split()[0] == release
    report.update(module_bytes=output.stat().st_size, module_sha256=sha(output), intree=get('intree'),
                  vermagic=get('vermagic'), depends=get('depends'), imported_symbols=len(imported),
                  imported_symbols_available_in_image363=True, private_module=str(output))
    (PRIVATE / ('module-imports-r' + str(attempt) + '-private.json')).write_text(json.dumps(imported, indent=2) + '\n')
(HERE / ('module-build-r' + str(attempt) + '-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
if report['passed']:
    (HERE / 'module-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(PRIVATE / 'module-build-state-private.json').write_text(json.dumps(dict(terminal=True, **report), indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
raise SystemExit(0 if report['passed'] else 1)
