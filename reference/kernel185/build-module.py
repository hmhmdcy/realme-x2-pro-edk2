"""Build only hci_uart; preserve the deployed Image, DTB and other source changes."""
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
out = Path('/mnt/e/edk2-samurai-out/kernel185')
source = json.loads((ref / 'source-validation.json').read_text())
host = json.loads((ref / 'host-tests-validation.json').read_text())
assert host['asan_ubsan_passed'] and host['source_sha256'] == source['source_sha256_after']
assert source['checkpatch_exit'] == 0
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = {name: sha(k / name) for name in ['.config', 'arch/arm64/boot/Image',
                                        'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']}
baseline = json.loads((ref.parent / 'kernel183/source-validation.json').read_text())['source_sha256']
assert all(sha(k / name) == digest for name, digest in baseline.items())
assert sha(k / 'drivers/bluetooth/hci_qca.c') == source['source_sha256_after']
shutil.copyfile(k / 'drivers/bluetooth/hci_uart.ko', out / 'hci_uart-before-build-private.ko')
env = dict(os.environ, KBUILD_BUILD_VERSION='183',
           PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'], RUSTUP_HOME='/home/cy122/.rustup')


def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))


with (out / 'module-build-private.log').open('xb') as log:
    subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                    'LD=aarch64-linux-gnu-ld --no-keep-memory', 'W=1', '-j3',
                    'drivers/bluetooth/hci_uart.ko'], cwd=k, env=env, stdout=log,
                   stderr=subprocess.STDOUT, preexec_fn=limit, check=True)
diagnostics = re.findall(r'^.*\b(?:warning|error):.*$', (out / 'module-build-private.log').read_text(), re.M)
assert not diagnostics, diagnostics
candidate = out / 'hci_uart-k185-private.ko'
shutil.copyfile(k / 'drivers/bluetooth/hci_uart.ko', candidate)
subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(candidate)], check=True)
vermagic = subprocess.check_output(['modinfo', '-F', 'vermagic', str(candidate)], text=True).strip()
oldvermagic = subprocess.check_output(['modinfo', '-F', 'vermagic', str(out / 'hci_uart-before-build-private.ko')], text=True).strip()
assert vermagic == oldvermagic
assert all(sha(k / name) == digest for name, digest in before.items())
assert all(sha(k / name) == digest for name, digest in baseline.items())
undefined = subprocess.check_output(['aarch64-linux-gnu-nm', '-u', str(candidate)], text=True)
(out / 'undefined-symbols-private.txt').write_text(undefined)
symvers = {line.split()[1]: line.split()[0] for line in (k / 'Module.symvers').read_text().splitlines()}
assert all(line.split()[-1] in symvers for line in undefined.splitlines() if line.strip())
report = {'kernel_build_unchanged': 183, 'runtime_generation': 132,
          'targeted_hci_uart_module_built': True, 'w1_warnings': 0,
          'vermagic_same_as_baseline': True, 'all_imported_symbols_in183_build': True,
          'image_dtb_config_unchanged': True, 'prior183_tracked_sources_unchanged': True,
          'candidate_sha256': sha(candidate), 'candidate_bytes': candidate.stat().st_size,
          'vermagic': vermagic, 'source_sha256': source['source_sha256_after'],
          'runtime_deployed': False}
(ref / 'module-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
