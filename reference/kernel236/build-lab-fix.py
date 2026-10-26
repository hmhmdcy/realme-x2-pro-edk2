"""Build only the lab module in-tree, preserving all maintained artifacts."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import resource
import shutil
import stat
import subprocess
import time

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel236')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
spec = importlib.util.spec_from_file_location('snapshot227', R.parent / 'kernel227/prepare-fastrpc.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
before = helper.snapshot()
assert before == json.loads((P.parent / 'kernel228/canonical-after-private.json').read_text())
out = P / 'lab-fix-build-r1'
out.mkdir(mode=0o700)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
inputs = {name: sha(R / name) for name in ['qcom-pm8008-imx319-lab.c', 'qcom-pm8008-imx319-lab.h']}
for name in inputs:
    shutil.copyfile(R / name, out / (name + '-input-private'))
directory = K / 'drivers/regulator'
def outputs():
    return {path for path in directory.iterdir() if path.is_file() and path.name.startswith(('qcom-pm8008', '.qcom-pm8008'))}
names = ['drivers/regulator/Makefile', 'include/linux/mfd/qcom-pm8008-imx319-lab.h',
         '.config', '.config.old', 'Module.symvers', 'modules.order', 'include/generated/compile.h',
         'include/generated/utsversion.h', 'include/generated/autoconf.h', 'include/config/auto.conf',
         'include/config/auto.conf.cmd', 'include/config/kernel.release']
saved = {str(path.relative_to(K)): (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
         for path in outputs() | {K / name for name in names} if path.is_file()}
backup = out / 'before'
backup.mkdir(mode=0o700)
for name, (data, mode) in saved.items():
    path = backup / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
env = dict(os.environ, KBUILD_BUILD_VERSION='183', PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'], RUSTUP_HOME='/home/cy122/.rustup')
def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
ret = None
start = time.monotonic()
try:
    shutil.copyfile(R / 'qcom-pm8008-imx319-lab.c', directory / 'qcom-pm8008-imx319-lab.c')
    shutil.copyfile(R / 'qcom-pm8008-imx319-lab.h', K / 'include/linux/mfd/qcom-pm8008-imx319-lab.h')
    with (directory / 'Makefile').open('ab') as stream:
        stream.write(b'\nobj-$(CONFIG_REGULATOR_QCOM_PM8008_IMX319_LAB) += qcom-pm8008-imx319-lab.o\n')
    with (out / 'build-private.log').open('xb') as log:
        ret = subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                              'LD=aarch64-linux-gnu-ld --no-keep-memory', 'CONFIG_REGULATOR_QCOM_PM8008_IMX319_LAB=m',
                              'W=1', '-j3', 'drivers/regulator/qcom-pm8008-imx319-lab.ko'], cwd=K, env=env,
                             stdout=log, stderr=subprocess.STDOUT, preexec_fn=limit).returncode
    if ret == 0:
        shutil.copyfile(directory / 'qcom-pm8008-imx319-lab.ko', out / 'qcom-pm8008-imx319-lab.ko')
        subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(out / 'qcom-pm8008-imx319-lab.ko')], check=True)
finally:
    for path in outputs() | {K / name for name in names}:
        if path.is_file() and str(path.relative_to(K)) not in saved:
            path.unlink()
    for name, (data, mode) in saved.items():
        path = K / name
        path.write_bytes(data)
        path.chmod(mode)
    restored = helper.snapshot() == before
    (out / 'restoration-private.json').write_text(json.dumps(dict(build_exit=ret, canonical_restored=restored), indent=2) + '\n')
    assert restored
assert ret == 0, 'Inspect private build log; canonical restored'
diagnostics = [line for line in (out / 'build-private.log').read_text().splitlines() if re.search(r'\b(warning|error):', line, re.I)]
assert not diagnostics, diagnostics
module = out / 'qcom-pm8008-imx319-lab.ko'
info = lambda field: subprocess.check_output(['modinfo', '-F', field, str(module)], text=True).strip()
available = {line.split()[1] for line in saved['Module.symvers'][0].decode().splitlines()}
imports = {line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm', '-u', str(module)], text=True).splitlines() if line.strip()}
assert imports <= available and info('intree') == 'Y'
assert info('vermagic') == json.loads((R.parent / 'kernel235/imx319-build-validation.json').read_text())['vermagic']
report = dict(stage=236, source_inputs=inputs, sha256=sha(module), bytes=module.stat().st_size, intree='Y',
              vermagic=info('vermagic'), imports_available=True, real_in_tree_build=True, w1_diagnostics=0,
              canonical_after228_and_q_regulator_restored=True, hardware_not_loaded_yet=True,
              elapsed_seconds=round(time.monotonic() - start, 2))
(R / 'lab-fix-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
