"""Build the real OF/runtime sensor candidate; restore the entire old target."""
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
P = Path('/mnt/e/edk2-samurai-out/kernel266')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
spec = importlib.util.spec_from_file_location('snapshot227', R.parent / 'kernel227/prepare-fastrpc.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
before = helper.snapshot()
(P / 'kernel-before-private.json').write_text(json.dumps(before, indent=2)+'\n')
assert '# CONFIG_VIDEO_IMX319 is not set\n' in (K / '.config').read_text()
out = P / 'imx319-build-r1'
out.mkdir(mode=0o700)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = {n: sha(R / n) for n in ['imx319.c', 'imx319-oem-tables.h']}
for name in inputs:
    shutil.copyfile(R / name, out / (name + '-input-private'))
directory = K / 'drivers/media/i2c'
def outputs():
    return {p for p in directory.iterdir() if p.is_file() and p.name.startswith(('imx319', '.imx319'))}
names = ['.config', '.config.old', 'Module.symvers', 'modules.order', 'include/generated/compile.h',
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
env = dict(os.environ, KBUILD_BUILD_VERSION='183', PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup')
def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
ret = None
start = time.monotonic()
try:
    for name in inputs:
        shutil.copyfile(R / name, directory / name)
    with (out / 'build-private.log').open('xb') as log:
        ret = subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                              'LD=aarch64-linux-gnu-ld --no-keep-memory', 'CONFIG_VIDEO_IMX319=m', 'W=1', '-j3',
                              'drivers/media/i2c/imx319.ko'], cwd=K, env=env,
                             stdout=log, stderr=subprocess.STDOUT, preexec_fn=limit).returncode
    if ret == 0:
        shutil.copyfile(directory / 'imx319.ko', out / 'imx319.ko')
        subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(out / 'imx319.ko')], check=True)
finally:
    for p in outputs():
        if str(p.relative_to(K)) not in saved:
            p.unlink()
    for name, (data, mode) in saved.items():
        dest = K / name
        dest.write_bytes(data)
        dest.chmod(mode)
    exact = before == helper.snapshot()
    (out / 'restoration-private.json').write_text(json.dumps(dict(build_exit=ret, canonical_restored=exact), indent=2) + '\n')
    assert exact
assert ret == 0, 'Build failed; canonical restored; inspect private log'
diagnostics = [l for l in (out / 'build-private.log').read_text().splitlines() if re.search(r'\b(warning|error):', l, re.I)]
assert not diagnostics, diagnostics
module = out / 'imx319.ko'
info = lambda field: subprocess.check_output(['modinfo', '-F', field, str(module)], text=True).strip()
available = {l.split()[1] for l in saved['Module.symvers'][0].decode().splitlines()}
imports = {l.split()[-1] for l in subprocess.check_output(['aarch64-linux-gnu-nm', '-u', str(module)], text=True).splitlines() if l.strip()}
assert imports <= available and info('intree') == 'Y'
assert info('vermagic') == json.loads((R.parent / 'kernel228/intree-build-validation.json').read_text())['vermagic']
report = dict(stage=266, sha256=sha(module), bytes=module.stat().st_size, intree='Y',
              vermagic=info('vermagic'), imports_available=True, source_inputs=inputs,
              w1_diagnostics=0, real_in_tree_build=True, canonical_source_tree_restored=True,
              standard_metadata_candidate_built=True, hardware_not_yet_executed=True,
              config_video_imx319_m_command_override=True,
              elapsed_seconds=round(time.monotonic() - start, 2))
(R / 'imx319-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
