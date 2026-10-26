"""Compile real in-tree P components, restoring all maintained inputs/outputs."""
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
P = Path('/mnt/e/edk2-samurai-out/kernel235')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
spec = importlib.util.spec_from_file_location('snapshot227', R.parent / 'kernel227/prepare-fastrpc.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
before = helper.snapshot()
assert before == json.loads((P / 'kernel-before-private.json').read_text())
out = P / 'pmic-build-r4'
out.mkdir(mode=0o700)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = {n: sha(R / n) for n in ['qcom-pm8008.c', 'qcom-pm8008-imx319-lab.c', 'qcom-pm8008-imx319-lab.h']}
for name in inputs:
    shutil.copyfile(R / name, out / (name + '-input-private'))
prefixes = {'drivers/mfd': ('qcom-pm8008', '.qcom-pm8008'),
            'drivers/regulator': ('qcom-pm8008', '.qcom-pm8008')}


def outputs():
    return {p for directory, starts in prefixes.items() for p in (K / directory).iterdir()
            if p.is_file() and p.name.startswith(starts)}


names = ['drivers/regulator/Makefile', 'include/linux/mfd/qcom-pm8008-imx319-lab.h',
         '.config', '.config.old', 'Module.symvers', 'modules.order', 'include/generated/compile.h',
         'include/generated/utsversion.h', 'include/generated/autoconf.h', 'include/config/auto.conf',
         'include/config/auto.conf.cmd', 'include/config/kernel.release']
saved = {str(p.relative_to(K)): (p.read_bytes(), stat.S_IMODE(p.stat().st_mode))
         for p in outputs() | {K / n for n in names} if p.is_file()}
backup = out / 'before'
backup.mkdir(mode=0o700)
for name, (data, mode) in saved.items():
    dest = backup / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
assert len(saved['Module.symvers'][0].splitlines()) == 16798
assert len(saved['modules.order'][0].splitlines()) == 772
env = dict(os.environ, KBUILD_BUILD_VERSION='183', PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup')


def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))


ret = None
started = time.monotonic()
try:
    shutil.copyfile(R / 'qcom-pm8008.c', K / 'drivers/mfd/qcom-pm8008.c')
    shutil.copyfile(R / 'qcom-pm8008-imx319-lab.c', K / 'drivers/regulator/qcom-pm8008-imx319-lab.c')
    shutil.copyfile(R / 'qcom-pm8008-imx319-lab.h', K / 'include/linux/mfd/qcom-pm8008-imx319-lab.h')
    with (K / 'drivers/regulator/Makefile').open('ab') as stream:
        stream.write(b'\nobj-$(CONFIG_REGULATOR_QCOM_PM8008_IMX319_LAB) += qcom-pm8008-imx319-lab.o\n')
    with (out / 'build-private.log').open('xb') as log:
        ret = subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                              'LD=aarch64-linux-gnu-ld --no-keep-memory',
                              'CONFIG_REGULATOR_QCOM_PM8008_IMX319_LAB=m', 'W=1', '-j3',
                              'drivers/mfd/qcom-pm8008.ko', 'drivers/regulator/qcom-pm8008-imx319-lab.ko'],
                             cwd=K, env=env, stdout=log, stderr=subprocess.STDOUT,
                             preexec_fn=limit).returncode
    if ret == 0:
        for directory, name in [('mfd', 'qcom-pm8008'), ('regulator', 'qcom-pm8008-imx319-lab')]:
            dest = out / (name + '.ko')
            shutil.copyfile(K / 'drivers' / directory / (name + '.ko'), dest)
            subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(dest)], check=True)
finally:
    for p in outputs() | {K / n for n in names}:
        if p.is_file() and str(p.relative_to(K)) not in saved:
            p.unlink()
    for name, (data, mode) in saved.items():
        p = K / name
        p.write_bytes(data)
        p.chmod(mode)
    exact = helper.snapshot() == before
    (out / 'restoration-private.json').write_text(json.dumps(dict(build_exit=ret, canonical_restored=exact), indent=2) + '\n')
    assert exact
assert ret == 0, 'Build failed; canonical restored; inspect private build log'
log = (out / 'build-private.log').read_text()
diagnostics = [l for l in log.splitlines() if re.search(r'\b(warning|error):', l, re.I)]
assert not diagnostics, diagnostics
available = {l.split()[1] for l in saved['Module.symvers'][0].decode().splitlines()}
results = {}
for name in ['qcom-pm8008', 'qcom-pm8008-imx319-lab']:
    module = out / (name + '.ko')
    info = lambda field: subprocess.check_output(['modinfo', '-F', field, str(module)], text=True).strip()
    imports = {l.split()[-1] for l in subprocess.check_output(['aarch64-linux-gnu-nm', '-u', str(module)], text=True).splitlines() if l.strip()}
    assert imports <= available
    assert info('intree') == 'Y'
    assert info('vermagic') == json.loads((R.parent / 'kernel228/intree-build-validation.json').read_text())['vermagic']
    results[name] = dict(sha256=sha(module), bytes=module.stat().st_size, intree='Y', vermagic=info('vermagic'), imports_available=True)
report = dict(stage=235, modules=results, real_in_tree_build=True, w1_diagnostics=0,
              source_inputs=inputs,
              canonical_and_q_regulator_restored=True, default_profile_disabled=True,
              phone_unchanged=True, elapsed_seconds=round(time.monotonic() - started, 2))
(R / 'pmic-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
