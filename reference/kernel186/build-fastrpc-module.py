from pathlib import Path
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel186')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = json.loads((ref.parent / 'kernel183/source-validation.json').read_text())['source_sha256']
assert all(sha(k / name) == digest for name, digest in baseline.items())
qca = json.loads((ref.parent / 'kernel185/source-validation.json').read_text())['source_sha256_after']
assert sha(k / 'drivers/bluetooth/hci_qca.c') == qca
source = json.loads((ref / 'fastrpc-source-validation.json').read_text())
assert source['checkpatch_exit'] == 0 and sha(k / 'drivers/misc/fastrpc.c') == source['source_after_sha256']
before = {name: sha(k / name) for name in ['.config', 'arch/arm64/boot/Image',
    'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']}
symbols = (k / 'Module.symvers').read_bytes()
order = (k / 'modules.order').read_bytes()
assert len(symbols.splitlines()) == 16793 and len(order.splitlines()) == 770
(private / 'full183-Module.symvers-before-private').write_bytes(symbols)
(private / 'full183-modules.order-before-private').write_bytes(order)
old = private / 'fastrpc-before-build-private.ko'
assert not old.exists()
shutil.copyfile(k / 'drivers/misc/fastrpc.ko', old)
env = dict(os.environ, KBUILD_BUILD_VERSION='183',
    PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'], RUSTUP_HOME='/home/cy122/.rustup')
def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
log = private / 'fastrpc-module-build-private.log'
try:
    with log.open('xb') as output:
        subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
            'LD=aarch64-linux-gnu-ld --no-keep-memory', 'W=1', '-j3', 'drivers/misc/fastrpc.ko'],
            cwd=k, env=env, stdout=output, stderr=subprocess.STDOUT, preexec_fn=limit, check=True)
finally:
    (k / 'Module.symvers').write_bytes(symbols)
    (k / 'modules.order').write_bytes(order)
assert not re.findall(r'^.*\b(?:warning|error):.*$', log.read_text(), re.M)
candidate = private / 'fastrpc-k186-private.ko'
assert not candidate.exists()
shutil.copyfile(k / 'drivers/misc/fastrpc.ko', candidate)
subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(candidate)], check=True)
vm = subprocess.check_output(['modinfo', '-F', 'vermagic', str(candidate)], text=True).strip()
assert vm == subprocess.check_output(['modinfo', '-F', 'vermagic', str(old)], text=True).strip()
undefined = subprocess.check_output(['aarch64-linux-gnu-nm', '-u', str(candidate)], text=True)
available = {line.split()[1] for line in symbols.decode().splitlines()}
assert all(line.split()[-1] in available for line in undefined.splitlines() if line.strip())
assert all(sha(k / name) == digest for name, digest in baseline.items())
assert all(sha(k / name) == digest for name, digest in before.items())
assert sha(k / 'drivers/bluetooth/hci_qca.c') == qca
report = dict(stage=186, kernel_build_unchanged=183, runtime_generation=132,
    fastrpc_module_built=True, w1_warnings=0, vermagic=vm, vermagic_same=True,
    imported_symbols_checked=True, original183_and_qca185_sources_unchanged=True,
    image_dtb_config_unchanged=True, full_symbol_table_and_module_order_restored=True,
    source_sha256=source['source_after_sha256'], candidate_sha256=sha(candidate),
    candidate_bytes=candidate.stat().st_size, runtime_deployed=False)
(ref / 'fastrpc-module-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
