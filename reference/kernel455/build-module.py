"""Build the lifetime module in private kernel455 source/O, never an Image."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel455')
spec = importlib.util.spec_from_file_location('build455_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
SHARED = storage.mount.mounted_build()
ORIGINAL = SHARED.parent / 'source354'
ISOLATED = SHARED.parent / 'kernel455-lens-private'
SOURCE = ISOLATED / 'source-view'
BUILD = ISOLATED / 'O'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
git = lambda *args: subprocess.check_output(['git', '-C', str(ORIGINAL), *args], env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
record = json.loads((HERE.parent / 'kernel363/boot-candidate-build-validation.json').read_text())
release = record['release']
image = PRIVATE.parent / 'kernel363/Image-k363-private'
assert sha(image) == record['artifacts']['arch/arm64/boot/Image']['sha256']
assert sha(SHARED / 'Module.symvers') == record['artifacts']['Module.symvers']['sha256']
config = subprocess.check_output([str(ORIGINAL / 'scripts/extract-ikconfig'), str(image)])
assert hashlib.sha256(config).hexdigest() == record['artifacts']['.config']['sha256']
head_before = git('rev-parse', 'HEAD')
headers = ['include/linux/kref.h', 'include/linux/list.h', 'include/linux/module.h',
           'include/linux/pm_runtime.h', 'include/linux/regulator/consumer.h',
           'include/media/v4l2-subdev.h', 'include/media/v4l2-ctrls.h', 'include/media/v4l2-device.h']
assert all(git('show', record['commit'] + ':' + p) == (ORIGINAL / p).read_bytes() for p in headers)

inputs = [SHARED / n for n in ['.config', 'Module.symvers', 'include/config/kernel.release',
          'include/config/auto.conf', 'include/generated/autoconf.h', 'include/generated/utsrelease.h']]
inputs += [ORIGINAL / 'drivers/media/i2c' / n for n in ['Makefile', 'Kconfig']]
inputs += [HERE.parent / 'kernel453/bu64253.c', PRIVATE.parent / 'kernel453/bu64253-intree-r2.ko']
before = {str(p):sha(p) for p in inputs}

def branch(src, dst, owned):
    dst.mkdir(exist_ok=True)
    for p in src.iterdir():
        if p.name == '.git':
            continue
        q = dst / p.name
        if p.name in owned:
            assert not q.is_symlink()
            branch(p, q, owned[p.name])
        elif not q.exists() and not q.is_symlink():
            q.symlink_to(p, target_is_directory=p.is_dir())

ISOLATED.mkdir(exist_ok=True)
branch(ORIGINAL, SOURCE, {'drivers': {'media': {'i2c': {}}}})
i2c = SOURCE / 'drivers/media/i2c'
makefile = i2c / 'Makefile'
if makefile.is_symlink():
    makefile.unlink()
makefile.write_text((ORIGINAL / 'drivers/media/i2c/Makefile').read_text() + '\n# Isolated kernel455 lifetime r3\nobj-m += bu64253.o\n')
assert not (i2c / 'bu64253.c').is_symlink()
shutil.copyfile(HERE / 'bu64253.c', i2c / 'bu64253.c')
BUILD.mkdir(exist_ok=True)
if not (BUILD / '.config').exists():
    (BUILD / '.config').write_bytes(config)
for name in ['Module.symvers', 'vmlinux.symvers']:
    if (SHARED / name).exists():
        shutil.copyfile(SHARED / name, BUILD / name)
if not (BUILD / 'vmlinux.o').exists():
    shutil.copyfile(SHARED / 'vmlinux.o', BUILD / 'vmlinux.o')
assert (BUILD / 'vmlinux.o').is_file() and not (BUILD / 'vmlinux.o').is_symlink()
tmp = ISOLATED / 'tmp'; tmp.mkdir(exist_ok=True)
attempt = 1
while (PRIVATE / ('module-build-r' + str(attempt) + '-private.log')).exists():
    attempt += 1
logfile = PRIVATE / ('module-build-r' + str(attempt) + '-private.log')
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'], RUSTUP_HOME='/home/cy122/.rustup',
           KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai', KBUILD_BUILD_VERSION='363', TMPDIR=str(tmp))
for key in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG']:
    env.pop(key, None)
common = ['make', '-C', str(SOURCE), 'O=' + str(BUILD), 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
          'LOCALVERSION=+', 'KERNELRELEASE=' + release, 'W=1', 'KCFLAGS=-Werror', '-j3']
phases = []; begin = time.monotonic(); ret = None
targets = ['olddefconfig', 'modules_prepare', 'drivers/media/i2c/bu64253.ko']
with logfile.open('xb') as log:
    for target in targets:
        started = time.monotonic()
        proc = subprocess.Popen(common + [target], env=env, stdout=log, stderr=subprocess.STDOUT)
        print(json.dumps(dict(stage=455, attempt=attempt, target=target, pid=proc.pid, started=True)), flush=True)
        ret = proc.wait()
        phases.append(dict(target=target, exit=ret, seconds=round(time.monotonic()-started, 3)))
        if ret:
            break
assert git('rev-parse', 'HEAD') == head_before
assert {str(p):sha(p) for p in inputs} == before
mapping = lambda raw: {l.split('=',1)[0]:l for l in raw.decode().splitlines() if l.startswith(('CONFIG_', '# CONFIG_'))}
a = mapping(config); b = mapping((BUILD / '.config').read_bytes())
diff = {k:[a.get(k),b.get(k)] for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
assert all('VIDEO_QCOM_CAMSS_ICP' in k for k in diff), diff
diagnostics = [line for line in logfile.read_text(errors='replace').splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()]
report = dict(stage=455, attempt=attempt, candidate='BU64253 lifetime r3', phases=phases, exit=ret,
              elapsed_seconds=round(time.monotonic()-begin, 3), kernel_release=release,
              image363_config_sha256=hashlib.sha256(config).hexdigest(),
              configuration_differences_from_image363=diff, source_head=head_before.decode().strip(),
              k363_public_api_headers_compared=headers, public_api_headers_equal_pinned_k363=True,
              source_sha256=sha(HERE / 'bu64253.c'), module_symvers_exactly_image363=True,
              independent_455_source_view_and_output=True, no_shared_vmlinux_object_link=True,
              shared_inputs_and_453_source_and_module_unchanged=True, diagnostics=diagnostics,
              image_or_rootfs_built=False, installed_or_loaded=False, requires_core_0064_first=True,
              sdk_or_phone_accessed=False, passed=ret == 0 and not diagnostics)
if ret == 0:
    ko = BUILD / 'drivers/media/i2c/bu64253.ko'
    output = PRIVATE / ('bu64253-lifetime-r3-build' + str(attempt) + '.ko')
    shutil.copyfile(ko, output)
    info = lambda field: subprocess.check_output(['modinfo', '-F', field, str(output)], text=True).strip()
    imported = sorted({line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm', '-u', str(output)],text=True).splitlines() if line.strip()})
    available = {line.split()[1] for line in (SHARED / 'Module.symvers').read_text().splitlines()}
    assert set(imported) <= available, set(imported)-available
    assert info('intree') == 'Y' and info('vermagic').split()[0] == release
    report.update(module_bytes=output.stat().st_size, module_sha256=sha(output), intree=info('intree'),
                  vermagic=info('vermagic'), depends=info('depends'), imported_symbols=len(imported),
                  all_imported_symbols_available_in_image363=True)
    (PRIVATE / 'module-imports-private.json').write_text(json.dumps(imported, indent=2) + '\n')
(HERE / ('module-build-r' + str(attempt) + '-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
(HERE / 'module-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
raise SystemExit(0 if report['passed'] else 1)
