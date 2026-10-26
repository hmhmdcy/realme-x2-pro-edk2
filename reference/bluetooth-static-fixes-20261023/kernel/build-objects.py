"""Compile two objects in the existing owned O; restore its old sources/objects.

No mount, Image, module link, shared write, SDK or device action is performed.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

R = Path(__file__).resolve().parent
REF = R.parents[1]
P = Path('/mnt/e/edk2-samurai-out/bluetooth-static-fixes-20261023/kernel')
ROOT = Path('/mnt/samurai-full282')
SRC = ROOT / 'source354'
VIEW = ROOT / 'bluetooth-transport-20261023/source-view'
O = ROOT / 'bluetooth-transport-20261023/O'
SHARED = ROOT / 'build'
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
lock = json.loads((R / 'source-lock.json').read_text())
assert sys.argv[1:] == ['--qca-after-audited-attempt1'], 'Do not replay the ended first attempt'
prior_attempt = json.loads((P / 'object-build-attempt1-private.json').read_text())
assert prior_attempt['terminal'] and prior_attempt['make_exit'] == 0 and not prior_attempt['validation_passed']
tests = json.loads((R / 'offline-validation.json').read_text())
assert tests['candidate_sha256'] == lock['candidate_sha256']
assert all(case['passed'] for case in tests['serdev']['candidate'])
assert tests['qca']['candidate']['close_leaks'] == 0
assert (O / '.config').exists(), 'Owned ext4/O absent: stop without mount'
assert shutil.disk_usage(ROOT).free >= 2 * 1024**3 + 128 * 1024**2
assert sha(SHARED / '.config') == 'e48f834d69840b2046077db2e60d988fb8bef438806ab594e1a4c082d2b34df3'
assert sha(SHARED / 'Module.symvers') == '0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223'
old_private = P.parents[1] / 'bluetooth-host-config-20261023'
assert (O / '.config').read_bytes() == (old_private / 'config-before-private').read_bytes()
assert (O / 'Module.symvers').read_bytes() == (old_private / 'module-symvers-before-private').read_bytes()
assert (O / 'include/config/kernel.release').read_text().strip() == RELEASE
for name, info in lock['baseline'].items():
    assert sha(SRC / 'drivers/bluetooth' / name) == info['sha256']
    assert sha(R / 'candidate' / name) == lock['candidate_sha256'][name]
assert sha(VIEW / 'drivers/bluetooth/hci_qca.c') == lock['previous_pm_r2_sha256']
assert (VIEW / 'drivers/bluetooth/hci_serdev.c').is_symlink()
assert (VIEW / 'drivers/bluetooth/hci_serdev.c').resolve() == SRC / 'drivers/bluetooth/hci_serdev.c'

guarded = [SHARED / n for n in ['.config', 'Module.symvers', 'include/config/kernel.release']]
guarded += [O / n for n in ['.config', 'Module.symvers', 'include/config/auto.conf',
    'include/generated/autoconf.h', 'include/generated/utsrelease.h', 'include/config/kernel.release']]
guarded += [SRC / 'drivers/bluetooth' / n for n in ['hci_serdev.c', 'hci_qca.c', 'hci_ldisc.c', 'hci_uart.h']]
guarded += [P.parents[1] / 'bluetooth-transport-20261023' / n for n in [
    'hci_uart-qca-pm-r2-k363-intree.ko', 'hci_uart-qca-pm-r2-k363-intree-stripped.ko',
    'qcom_geni_serial-rts-candidate.o', 'hci_qca-pm-r2.c']]
guarded += [old_private / n for n in ['bnep-k363-intree.ko', 'uhid-k363-intree.ko']]
before = {str(p): sha(p) for p in guarded}
sources = {}
objects = {}
backup = P / 'object-build-backup-r2'
backup.mkdir(exist_ok=False)
for name in ['hci_qca.c']:
    path = VIEW / 'drivers/bluetooth' / name
    record = dict(symlink=os.readlink(path) if path.is_symlink() else None, sha256=sha(path))
    if not path.is_symlink():
        shutil.copy2(path, backup / name)
    sources[name] = record
    stem = Path(name).stem
    for filename in [stem + '.o', '.' + stem + '.o.cmd']:
        path = O / 'drivers/bluetooth' / filename
        objects[filename] = dict(existed=path.exists(), sha256=sha(path) if path.exists() else None)
        if path.exists():
            shutil.copy2(path, backup / filename)

env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
    RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai',
    KBUILD_BUILD_VERSION='363', TMPDIR=str(ROOT / 'bluetooth-transport-20261023/tmp'))
for name in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG']:
    env.pop(name, None)
command = ['make', '-C', str(VIEW), 'O=' + str(O), 'ARCH=arm64',
    'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+', 'KERNELRELEASE=' + RELEASE,
    'W=1', 'KCFLAGS=-Werror', '-j1', 'drivers/bluetooth/hci_qca.o']
ret, failure, outputs = None, None, []
started = time.monotonic()
logfile = P / 'object-build-r2.log'
available = {line.split()[1] for line in (SHARED / 'Module.symvers').read_text().splitlines()}
old_module = P.parents[1] / 'bluetooth-transport-20261023/hci_uart-qca-pm-r2-k363-intree.ko'
providers = {line.split()[-1] for line in subprocess.check_output(
    ['aarch64-linux-gnu-nm', '-g', '--defined-only', str(old_module)], text=True).splitlines() if line.strip()}
try:
    for name in sources:
        dst = VIEW / 'drivers/bluetooth' / name
        if dst.is_symlink():
            dst.unlink()
        shutil.copyfile(R / 'candidate' / name, dst)
        assert not dst.is_symlink() and sha(dst) == lock['candidate_sha256'][name]
    with logfile.open('xb') as log:
        proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        state = dict(terminal=False, pid=proc.pid, targets=command[-1:], source_view=str(VIEW), output=str(O))
        (P / 'object-build-state.json').write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps(state), flush=True)
        ret = proc.wait(timeout=180)
    if ret:
        raise RuntimeError('Object compilation failed: ' + str(ret))
    for name in ['hci_serdev.c', 'hci_qca.c']:
        source = O / 'drivers/bluetooth' / (Path(name).stem + '.o')
        target = P / (Path(name).stem + '-static-fixes-k363.o')
        if name in sources:
            shutil.copy2(source, target)
        else:
            assert sha(target) == '2473b122bde4d9e7fa69e2bd982debb9e02d51292cdb6c73165703417baca46a'
        undefined = sorted({line.split()[-1] for line in subprocess.check_output(
            ['aarch64-linux-gnu-nm', '-u', str(target)], text=True).splitlines() if line.strip()})
        assert set(undefined) <= available | providers, set(undefined) - available - providers
        outputs.append(dict(path=str(target), bytes=target.stat().st_size, sha256=sha(target),
            imports=len(undefined), external_imports_in_original363=True,
            same_module_imports=sorted(set(undefined) - available),
            same_module_providers_from_verified_old_hci_uart=True,
            compiled_in_attempt=1 if name == 'hci_serdev.c' else 2))
except BaseException as exc:
    failure = str(exc)
    if 'proc' in locals() and proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=15)
finally:
    for name, record in sources.items():
        dst = VIEW / 'drivers/bluetooth' / name
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        if record['symlink']:
            dst.symlink_to(record['symlink'])
        else:
            shutil.copy2(backup / name, dst)
        assert sha(dst) == record['sha256']
    for name, record in objects.items():
        dst = O / 'drivers/bluetooth' / name
        if record['existed']:
            shutil.copy2(backup / name, dst)
            assert sha(dst) == record['sha256']
        elif dst.exists():
            dst.unlink()
    changed = {str(p): [before[str(p)], sha(p)] for p in guarded if sha(p) != before[str(p)]}
diagnostics = [line for line in logfile.read_text().splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()]
result = dict(terminal=True, exit=ret, failure=failure, seconds=round(time.monotonic() - started, 3),
    passed=ret == 0 and failure is None and not diagnostics and not changed and len(outputs) == 2,
    targets=command[-1:], jobs=1, w1_werror=True, diagnostics=diagnostics, objects=outputs,
    candidate_sha256=lock['candidate_sha256'], fixed_commit=lock['commit'],
    owned_source_symlinks_and_old_objects_restored=True, guarded_inputs_unchanged=not changed,
    guarded_differences=changed, earlier_attempt_preserved=True,
    attempt1_generated_headers_synchronized_to_owned_config=True,
    shared_or_sdk_written=False, image_or_module_linked=False, device_accessed=False,
    free_bytes_after=shutil.disk_usage(ROOT).free, before_hashes=before, build_script_sha256=sha(Path(__file__)))
(P / 'object-build-state.json').write_text(json.dumps(result, indent=2) + '\n')
(P / 'object-build-validation-private.json').write_text(json.dumps(result, indent=2) + '\n')
# Public receipt includes only non-personal build/source hashes and paths.
(R / 'object-build-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2), flush=True)
raise SystemExit(0 if result['passed'] else 1)
