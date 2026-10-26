"""Retired prototype build entry; 315 reuses the tested 314 CAMSS module."""
raise SystemExit('No315 kernel change selected; use314 kernel-build-validation.json and315 build-candidate.py.')
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel315')
TREE = Path('/home/cy122/x2pro-linux/camera314-streams-kernel')
spec = importlib.util.spec_from_file_location('storage284', HERE.parent / 'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
BUILD = storage.mounted_build()
release = (BUILD / 'include/config/kernel.release').read_text().strip()
target = Path('drivers/media/platform/qcom/camss')
attempt = 1
while (PRIVATE / f'camss-build-r{attempt}.log').exists():
    attempt += 1
log = PRIVATE / f'camss-build-r{attempt}.log'
backup = PRIVATE / f'camss-build-r{attempt}-before'
backup.mkdir()
# In-tree single-module modpost reads vmlinux.o, not external-module symvers.
# Include the existing module dependency closure in the same invocation.
symbols = {line.split()[1]: line.split()[2]
           for line in (BUILD / 'Module.symvers').read_text().splitlines()}
modules = {str(target / 'qcom-camss')}
pending = list(modules)
while pending:
    name = pending.pop()
    output = subprocess.check_output(['aarch64-linux-gnu-nm', '-u', str(BUILD / (name + '.ko'))], text=True)
    for line in output.splitlines():
        module = symbols.get(line.split()[-1])
        if module and module != 'vmlinux' and module not in modules:
            modules.add(module)
            pending.append(module)
directories = {str(Path(name).parent) for name in modules}
for directory in directories:
    shutil.copytree(BUILD / directory, backup / directory, symlinks=True)
names = [
    '.config', '.config.old', 'Module.symvers', 'modules.order', 'Makefile', 'source',
    'include/generated/compile.h', 'include/generated/utsversion.h',
    'include/generated/utsrelease.h', 'include/generated/autoconf.h',
    'include/config/auto.conf', 'include/config/auto.conf.cmd',
    'include/config/kernel.release',
]
saved = {}
for name in names:
    p = BUILD / name
    if p.is_symlink():
        saved[name] = ('symlink', os.readlink(p))
    elif p.is_file():
        saved[name] = ('file', p.read_bytes())
    else:
        saved[name] = ('missing', None)
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_VERSION='298',
           KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai',
           TMPDIR=str(BUILD.parent / 'tmp'))
command = [
    'make', '-C', str(TREE), 'O=' + str(BUILD), 'ARCH=arm64',
    'CROSS_COMPILE=aarch64-linux-gnu-', '-j3', 'W=1', 'KCFLAGS=-Werror',
    'KERNELRELEASE=' + release,
]
command += [name + '.ko' for name in sorted(modules)]
start = time.monotonic()
state = PRIVATE / 'camss-build-state.json'
try:
    with log.open('xb') as output:
        child = subprocess.Popen(command, env=env, stdout=output, stderr=subprocess.STDOUT)
        state.write_text(json.dumps(dict(pid=child.pid, terminal=False, attempt=attempt)) + '\n')
        code = child.wait()
    if code == 0:
        module = PRIVATE / f'qcom-camss-sof315-r{attempt}.ko'
        shutil.copyfile(BUILD / target / 'qcom-camss.ko', module)
finally:
    for directory in directories:
        shutil.rmtree(BUILD / directory)
        shutil.copytree(backup / directory, BUILD / directory, symlinks=True)
    for name, (kind, data) in saved.items():
        p = BUILD / name
        if p.is_symlink():
            p.unlink()
        if kind == 'symlink':
            if p.exists():
                p.unlink()
            p.symlink_to(data)
        elif kind == 'file':
            p.write_bytes(data)
        elif p.exists():
            p.unlink()
diagnostics = [s for s in log.read_text(errors='replace').splitlines()
               if 'warning:' in s.lower() or 'error:' in s.lower()]
report = dict(stage=315, attempt=attempt, exit_code=code,
              seconds=round(time.monotonic() - start, 2), diagnostics=diagnostics,
              kernel_release=release, build_outputs_restored=True, installed=False)
report['dependency_modules'] = sorted(modules - {str(target / 'qcom-camss')})
if code == 0:
    report['module'] = str(module)
    report['vermagic'] = subprocess.check_output(
        ['modinfo', '-F', 'vermagic', str(module)], text=True).strip()
    report['intree'] = subprocess.check_output(
        ['modinfo', '-F', 'intree', str(module)], text=True).strip()
state.write_text(json.dumps(dict(pid=child.pid, terminal=True, **report)) + '\n')
(HERE / 'kernel-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
raise SystemExit(code)
