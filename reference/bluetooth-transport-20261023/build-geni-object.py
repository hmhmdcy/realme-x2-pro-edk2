"""Compile only the offline GENI candidate object in the existing private O=.

This does not link an Image or change either QCA module artifact.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import time

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/bluetooth-transport-20261023')
spec = importlib.util.spec_from_file_location('geni_storage', R.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
shared = storage.mount.mounted_build()
isolated = shared.parent / 'bluetooth-transport-20261023'
original = isolated.parent / 'source354'
geni_original = original if (original / 'drivers/tty/serial/qcom_geni_serial.c').exists() else Path('/home/cy122/pmos-samurai-kernel136/kernel')
view = isolated / 'source-view'
build = isolated / 'O'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
prior = json.loads((R / 'qca-pm-r2-module-build-validation.json').read_text())
assert prior['passed'] and prior['shared_inputs_unchanged']
report = json.loads((R / 'rts-contract-validation.json').read_text())
assert report['asan_ubsan_passed']
baseline = geni_original / 'drivers/tty/serial/qcom_geni_serial.c'
assert sha(baseline) == report['source_geni_sha256']
assert (build / 'include/config/kernel.release').read_text().strip() == prior['kernel_release']
assert sha(geni_original / 'include/linux/serial_core.h') == sha(original / 'include/linux/serial_core.h')
inputs = [baseline, geni_original / 'drivers/tty/serial/Makefile', original / 'include/linux/serial_core.h']
modules = [Path(prior['private_module']), Path(prior['stripped_module'])]
before = {str(p): sha(p) for p in inputs + modules}


def branch(src, dst, owned):
    if dst.is_symlink():
        dst.unlink()
    dst.mkdir(exist_ok=True)
    for p in src.iterdir():
        if p.name == '.git':
            continue
        q = dst / p.name
        if p.name in owned:
            branch(p, q, owned[p.name])
        elif not q.exists() and not q.is_symlink():
            q.symlink_to(p, target_is_directory=p.is_dir())


branch(geni_original / 'drivers/tty', view / 'drivers/tty', {'serial': {}})
candidate = view / 'drivers/tty/serial/qcom_geni_serial.c'
assert candidate.is_symlink() and candidate.resolve() == baseline.resolve()
candidate.unlink()
shutil.copyfile(baseline, candidate)
patch = R / 'geni-rts-mode-lock-candidate.patch'
assert sha(patch) == report['patch_sha256']
proc = subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(view), '-i', str(patch)],
                      capture_output=True, check=True)
(P / 'geni-object-patch.log').write_bytes(proc.stdout + proc.stderr)
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_USER='builder',
           KBUILD_BUILD_HOST='samurai', KBUILD_BUILD_VERSION='363', TMPDIR=str(isolated / 'tmp'))
for key in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG']:
    env.pop(key, None)
logfile = P / 'geni-object-build.log'
started = time.monotonic()
with logfile.open('xb') as log:
    cp = subprocess.run(['make', '-C', str(view), 'O=' + str(build), 'ARCH=arm64',
        'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+',
        'KERNELRELEASE=' + prior['kernel_release'], 'W=1', 'KCFLAGS=-Werror', '-j2',
        'drivers/tty/serial/qcom_geni_serial.o'], env=env, stdout=log, stderr=subprocess.STDOUT)
assert {str(p): sha(p) for p in inputs + modules} == before
diagnostics = [l for l in logfile.read_text(errors='replace').splitlines()
               if 'warning:' in l.lower() or 'error:' in l.lower()]
result = dict(exit=cp.returncode, seconds=round(time.monotonic() - started, 3),
    real_kernel_w1_werror_object_only=True, diagnostics=diagnostics,
    passed=cp.returncode == 0 and not diagnostics,
    patch_sha256=sha(patch), baseline_source_sha256=sha(baseline),
    candidate_source_sha256=sha(candidate),
    shared_inputs_and_qca_module_artifacts_unchanged=True,
    image_not_linked=True, sdk_or_phone_accessed=False, installed_or_loaded=False)
if not cp.returncode:
    obj = build / 'drivers/tty/serial/qcom_geni_serial.o'
    output = P / 'qcom_geni_serial-rts-candidate.o'
    shutil.copyfile(obj, output)
    result.update(object_bytes=output.stat().st_size, object_sha256=sha(output), private_object=str(output))
(R / 'geni-object-build-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
