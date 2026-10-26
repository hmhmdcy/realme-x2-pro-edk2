"""Build one real in-tree HCI module, then restore the maintained tree."""
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
P = Path('/mnt/e/edk2-samurai-out/kernel234')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
spec = importlib.util.spec_from_file_location('snapshot227', R.parent / 'kernel227/prepare-fastrpc.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
before = helper.snapshot()
assert before == json.loads((P.parent / 'kernel228/canonical-after-private.json').read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
source = json.loads((R / 'diagnostic-source-validation.json').read_text())
assert sha((R / 'hci_qca.c').read_bytes()) == source['source_after_sha256']
out = P / 'diagnostic-build-r2'
out.mkdir(mode=0o700)
directory = K / 'drivers/bluetooth'
names = ['.config', '.config.old', 'Module.symvers', 'modules.order',
         'include/generated/compile.h', 'include/generated/utsversion.h',
         'include/config/auto.conf', 'include/config/auto.conf.cmd',
         'include/generated/autoconf.h', 'include/config/kernel.release']
saved = {str(p.relative_to(K)): (p.read_bytes(), stat.S_IMODE(p.stat().st_mode))
         for p in list(directory.iterdir()) + [K / n for n in names] if p.is_file()}
backup = out / 'before'
backup.mkdir(mode=0o700)
for name, (data, mode) in saved.items():
    p = backup / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
assert len(saved['Module.symvers'][0].splitlines()) == 16798
assert len(saved['modules.order'][0].splitlines()) == 772
env = dict(os.environ, KBUILD_BUILD_VERSION='183',
           PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'], RUSTUP_HOME='/home/cy122/.rustup')


def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))


start = time.monotonic()
ret = None
try:
    shutil.copyfile(R / 'hci_qca.c', directory / 'hci_qca.c')
    with (out / 'build-private.log').open('xb') as log:
        ret = subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                              'LD=aarch64-linux-gnu-ld --no-keep-memory', 'W=1', '-j3',
                              'drivers/bluetooth/btbcm.ko', 'drivers/bluetooth/btqca.ko',
                              'drivers/bluetooth/hci_uart.ko'],
                             cwd=K, env=env, stdout=log, stderr=subprocess.STDOUT,
                             preexec_fn=limit).returncode
    if ret == 0:
        shutil.copyfile(directory / 'hci_uart.ko', out / 'hci_uart.ko')
        subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(out / 'hci_uart.ko')], check=True)
finally:
    for p in directory.iterdir():
        if p.is_file() and str(p.relative_to(K)) not in saved:
            p.unlink()
    for name, (data, mode) in saved.items():
        p = K / name
        p.write_bytes(data)
        p.chmod(mode)
    after = helper.snapshot()
    exact = all((K / name).read_bytes() == data for name, (data, _) in saved.items())
    (out / 'restoration-private.json').write_text(json.dumps(dict(
        build_returncode=ret, maintained_snapshot_restored=before == after,
        all_bluetooth_files_restored=exact), indent=2) + '\n')
    assert before == after and exact
assert ret == 0, 'Build failed; maintained tree restored; inspect private build log'
log = (out / 'build-private.log').read_text()
assert not re.search(r'\b(?:warning|error):|Restart config|Error in reading', log, re.I)
module = out / 'hci_uart.ko'
info = lambda field: subprocess.check_output(['modinfo', '-F', field, str(module)], text=True).strip()
assert info('intree') == 'Y'
assert info('vermagic') == subprocess.check_output([
    'modinfo', '-F', 'vermagic', str(backup / 'drivers/bluetooth/hci_uart.ko')], text=True).strip()
available = {s.split()[1] for s in saved['Module.symvers'][0].decode().splitlines()}
imports = {s.split()[-1] for s in subprocess.check_output([
    'aarch64-linux-gnu-nm', '-u', str(module)], text=True).splitlines() if s.strip()}
assert imports <= available
report = dict(stage=234, candidate_sha256=sha(module.read_bytes()), candidate_bytes=module.stat().st_size,
              source_sha256=source['source_after_sha256'], intree='Y', vermagic=info('vermagic'),
              real_in_tree_build=True, w1_diagnostics=0, imports_in_full183_symbols=True,
              canonical_after228_exactly_restored=True, all_bluetooth_objects_and_sources_restored=True,
              diagnostics_only=True, default_disabled=True, phone_unchanged=True,
              elapsed_seconds=round(time.monotonic() - start, 2))
(R / 'diagnostic-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
