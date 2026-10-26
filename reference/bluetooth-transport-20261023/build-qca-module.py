"""Build the proven QCA PM return-contract fix in a private k363 source view.

Shared source and build inputs are only read, never patched or rebuilt.
No SDK, phone, package, module installation or image operations are performed.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

R = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bt_storage', R.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
shared = storage.mount.mounted_build()
original = shared.parent / 'source354'
isolated = shared.parent / 'bluetooth-transport-20261023'
view = isolated / 'source-view'
build = isolated / 'O'
private = Path('/mnt/e/edk2-samurai-out/bluetooth-transport-20261023')
private.mkdir(exist_ok=True)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


record = json.loads((R.parent / 'kernel363/boot-candidate-build-validation.json').read_text())
image = private.parent / 'kernel363/Image-k363-private'
assert sha(image) == record['artifacts']['arch/arm64/boot/Image']['sha256']
config = subprocess.check_output([str(original / 'scripts/extract-ikconfig'), str(image)])
assert hashlib.sha256(config).hexdigest() == record['artifacts']['.config']['sha256']
assert sha(shared / 'Module.symvers') == record['artifacts']['Module.symvers']['sha256']
release = (shared / 'include/config/kernel.release').read_text().strip()
assert release == '7.3.0-rc6-rmx1931-samurai-k363+'
assert sha(original / 'drivers/bluetooth/hci_qca.c') == sha(R / 'source/hci_qca.c')
test = json.loads((R / 'qca-suspend-contract-validation.json').read_text())
assert test['asan_ubsan_passed'] and test['results']['qca_suspend_candidate']['contract_mismatches'] == 0
revision2 = '--r2' in sys.argv
patch = R / ('qca-suspend-recovery-r2.patch' if revision2 else 'qca-suspend-return-contract-candidate.patch')
if revision2:
    recovery = json.loads((R / 'qca-pm-recovery-validation.json').read_text())
    assert recovery['asan_ubsan_passed'] and recovery['r2_return_value_regression']['contract_mismatches'] == 0
    assert sha(patch) == recovery['r2_patch_sha256']
else:
    assert sha(patch) == test['patch_sha256']


def snapshot():
    files = [shared / n for n in ['.config', 'Module.symvers', 'include/config/kernel.release',
             'include/config/auto.conf', 'include/generated/autoconf.h', 'include/generated/utsrelease.h']]
    files += [original / 'drivers/bluetooth' / n for n in
              ['hci_qca.c', 'hci_uart.h', 'hci_serdev.c', 'hci_h4.c', 'hci_ldisc.c', 'Makefile', 'Kconfig']]
    return {str(p): sha(p) for p in files}


before = snapshot()


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


isolated.mkdir(exist_ok=True)
branch(original, view, {'drivers': {'bluetooth': {}}})
candidate = view / 'drivers/bluetooth/hci_qca.c'
if candidate.is_symlink():
    candidate.unlink()
shutil.copyfile(R / 'source/hci_qca.c', candidate)
applied = subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(view), '-i', str(patch)],
                         capture_output=True, check=True)
(private / 'patch-apply.log').write_bytes(applied.stdout + applied.stderr)
build.mkdir(exist_ok=True)
resume_prepared = '--reuse-prepared' in sys.argv
if resume_prepared:
    prior = json.loads((R / 'module-build-validation.json').read_text())
    assert prior['shared_inputs_unchanged'] and prior['image363_config_sha256'] == hashlib.sha256(config).hexdigest()
    assert (build / 'include/config/kernel.release').read_text().strip() == release
    assert sha(candidate) == (recovery['r2_source_sha256'] if revision2 else prior['driver_source_sha256'])
else:
    assert not (build / '.config').exists(), 'Use --reuse-prepared only after inspecting the prior report'
    (build / '.config').write_bytes(config)
for name in ['Module.symvers', 'vmlinux.symvers']:
    if (shared / name).exists():
        shutil.copyfile(shared / name, build / name)
if not (build / 'vmlinux.o').exists():
    (build / 'vmlinux.o').symlink_to(shared / 'vmlinux.o')
assert (build / 'vmlinux.o').is_symlink() and (build / 'vmlinux.o').resolve() == (shared / 'vmlinux.o').resolve()
tmp = isolated / 'tmp'
tmp.mkdir(exist_ok=True)
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_USER='builder',
           KBUILD_BUILD_HOST='samurai', KBUILD_BUILD_VERSION='363', TMPDIR=str(tmp))
for key in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG']:
    env.pop(key, None)
common = ['make', '-C', str(view), 'O=' + str(build), 'ARCH=arm64',
          'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+',
          'KERNELRELEASE=' + release, 'W=1', 'KCFLAGS=-Werror', '-j3']
phases = []
started = time.monotonic()
attempt = 1
while (private / ('module-build-r' + str(attempt) + '.log')).exists():
    attempt += 1
logfile = private / ('module-build-r' + str(attempt) + '.log')
targets = [['olddefconfig'], ['modules_prepare'],
           ['drivers/bluetooth/btbcm.ko', 'drivers/bluetooth/btqca.ko', 'drivers/bluetooth/hci_uart.ko']]
if resume_prepared:
    targets = targets[-1:]
ret = None
with logfile.open('xb') as log:
    for target in targets:
        begin = time.monotonic()
        proc = subprocess.Popen(common + target, env=env, stdout=log, stderr=subprocess.STDOUT)
        state = dict(terminal=False, target=target, pid=proc.pid, build=str(build), source_view=str(view))
        (private / 'module-build-state.json').write_text(json.dumps(state) + '\n')
        print(json.dumps(state), flush=True)
        ret = proc.wait()
        phases.append(dict(target=target, exit=ret, seconds=round(time.monotonic() - begin, 3)))
        if ret:
            break
assert snapshot() == before, 'Relevant shared inputs changed; inspect before proceeding'
mapping = lambda raw: {l.split('=', 1)[0]: l for l in raw.decode().splitlines()
                       if l.startswith('CONFIG_') or l.startswith('# CONFIG_')}
a, b = mapping(config), mapping((build / '.config').read_bytes())
config_diff = {k: [a.get(k), b.get(k)] for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
assert all('VIDEO_QCOM_CAMSS' in k for k in config_diff), config_diff
diagnostics = [l for l in logfile.read_text(errors='replace').splitlines()
               if 'warning:' in l.lower() or 'error:' in l.lower()]
report = dict(phases=phases, exit=ret, seconds=round(time.monotonic() - started, 3),
    attempt=attempt, reused_private_preparation=resume_prepared, candidate_revision='r2' if revision2 else 'r1',
    kernel_release=release, image363_config_exactly_extracted=True,
    image363_config_sha256=hashlib.sha256(config).hexdigest(),
    input_module_symvers_exactly_image363=True,
    original_source_head=subprocess.check_output(['git', '-C', str(original), 'rev-parse', 'HEAD'], text=True).strip(),
    configuration_differences_from_image363=config_diff,
    driver_source_sha256=sha(candidate), baseline_source_sha256=sha(R / 'source/hci_qca.c'),
    patch_sha256=sha(patch), shared_inputs_unchanged=True,
    private_source_view_and_output=True, shared_source_or_build_written=False,
    sdk_or_phone_accessed=False, installed_or_loaded=False,
    diagnostics=diagnostics, passed=ret == 0 and not diagnostics)
if not ret:
    output = private / ('hci_uart-qca-pm-' + ('r2-' if revision2 else '') + 'k363-intree.ko')
    shutil.copyfile(build / 'drivers/bluetooth/hci_uart.ko', output)
    get = lambda key: subprocess.check_output(['modinfo', '-F', key, str(output)], text=True).strip()
    imported = sorted({l.split()[-1] for l in subprocess.check_output(
        ['aarch64-linux-gnu-nm', '-u', str(output)], text=True).splitlines() if l.strip()})
    available = {l.split()[1] for l in (shared / 'Module.symvers').read_text().splitlines()}
    assert set(imported) <= available, set(imported) - available
    assert get('intree') == 'Y' and get('vermagic').split()[0] == release
    report.update(module_bytes=output.stat().st_size, module_sha256=sha(output), intree=get('intree'),
        vermagic=get('vermagic'), depends=get('depends'), imported_symbols=len(imported),
        imported_symbols_available_in_image363=True, private_module=str(output))
    stripped = private / ('hci_uart-qca-pm-' + ('r2-' if revision2 else '') + 'k363-intree-stripped.ko')
    shutil.copyfile(output, stripped)
    subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(stripped)], check=True)
    assert subprocess.check_output(['modinfo', '-F', 'vermagic', str(stripped)], text=True).strip() == get('vermagic')
    assert subprocess.check_output(['modinfo', '-F', 'intree', str(stripped)], text=True).strip() == 'Y'
    report.update(stripped_module=str(stripped), stripped_module_bytes=stripped.stat().st_size,
                  stripped_module_sha256=sha(stripped))
    (private / 'module-imports.json').write_text(json.dumps(imported, indent=2) + '\n')
(R / ('module-build-r' + str(attempt) + '-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
(R / ('qca-pm-r2-module-build-validation.json' if revision2 else 'module-build-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
(private / 'module-build-state.json').write_text(json.dumps(dict(terminal=True, **report), indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
raise SystemExit(0 if report['passed'] else 1)
