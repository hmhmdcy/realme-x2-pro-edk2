"""Integrate the accepted source and build the actual in-tree module target."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import resource
import shutil
import subprocess
import time

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel228')
spec = importlib.util.spec_from_file_location('prepare227', REF.parent / 'kernel227/prepare-fastrpc.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
native = json.loads((REF / 'native-sensors-validation.json').read_text())
assert native['real_module_pin']['before'] + 1 == native['real_module_pin']['while_open']
assert len(native['five_real_sensor_streams']) == 5 and not any(native['fault_increments'].values())
before = p.snapshot()
assert before == json.loads((p.PRIVATE / 'kernel-before-private.json').read_text())
kernel = p.KERNEL
driver = kernel / 'drivers/misc'
backup = PRIVATE / 'canonical-fastrpc-before'
assert not backup.exists()
backup.mkdir(mode=0o700)
originals = list(driver.glob('*fastrpc*'))
for file in originals:
    if file.is_file():
        shutil.copy2(file, backup / file.name)
symbols = (kernel / 'Module.symvers').read_bytes()
order = (kernel / 'modules.order').read_bytes()
assert len(symbols.splitlines()) == 16798 and len(order.splitlines()) == 772
(PRIVATE / 'full-symbols-before-private').write_bytes(symbols)
(PRIVATE / 'full-module-order-before-private').write_bytes(order)
(PRIVATE / 'canonical-before-private.json').write_text(json.dumps(before, indent=2) + '\n')
extra_names = ['include/generated/compile.h', 'include/generated/utsversion.h', 'System.map']
extra = {n: p.digest((kernel / n).read_bytes()) for n in extra_names if (kernel / n).is_file()}
source = (p.BUILD / 'candidate/fastrpc.c').read_bytes()
assert p.digest(source) == 'f378afedc84d4d0cc29166686210fbf706ea16be59dd4270cab2f3c3ac5faec8'
assert b'MODULE_INFO(intree' not in source, 'Do not spoof module provenance in source'
(driver / 'fastrpc.c').write_bytes(source)
env = dict(os.environ, KBUILD_BUILD_VERSION='183', PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'], RUSTUP_HOME='/home/cy122/.rustup')


def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))


started = time.monotonic()
log = PRIVATE / 'intree-build-private.log'
assert not log.exists()
try:
    with log.open('xb') as output:
        subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                        'LD=aarch64-linux-gnu-ld --no-keep-memory', 'W=1', '-j3', 'drivers/misc/fastrpc.ko'],
                       cwd=kernel, env=env, stdout=output, stderr=subprocess.STDOUT,
                       preexec_fn=limit, check=True)
finally:
    # A single-target modpost may shorten these global lists; retain the full current tree.
    (kernel / 'Module.symvers').write_bytes(symbols)
    (kernel / 'modules.order').write_bytes(order)
assert not re.findall(r'^.*\b(?:warning|error):.*$', log.read_text(), re.M)
module = PRIVATE / 'fastrpc228-intree-private.ko'
assert not module.exists()
shutil.copyfile(driver / 'fastrpc.ko', module)
subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(module)], check=True)


def info(field):
    return subprocess.check_output(['modinfo', '-F', field, str(module)], text=True).strip()


assert info('intree') == 'Y'
assert info('vermagic') == json.loads((REF.parent / 'kernel227/fastrpc-build-validation.json').read_text())['results']['candidate']['vermagic']
imports = subprocess.check_output(['aarch64-linux-gnu-nm', '-u', str(module)], text=True)
names = {line.split()[-1] for line in imports.splitlines() if line.strip()}
prior_imports = set(json.loads((REF.parent / 'kernel227/fastrpc-build-validation.json').read_text())['results']['candidate']['imports'])
assert names == prior_imports
after = p.snapshot()
allowed = {'drivers/misc/fastrpc.c', 'drivers/misc/fastrpc.o', 'drivers/misc/fastrpc.ko',
           'drivers/misc/.fastrpc.o.cmd', 'drivers/misc/.fastrpc.ko.cmd', 'git_diff_sha256'}
changed = {name for name in before if before[name] != after[name]}
assert changed <= allowed, sorted(changed - allowed)
assert all(p.digest((kernel / n).read_bytes()) == v for n, v in extra.items())
assert after['drivers/misc/fastrpc.c'] == p.digest(source)
(PRIVATE / 'canonical-after-private.json').write_text(json.dumps(after, indent=2) + '\n')
report = dict(stage=228, native_functional_candidate_accepted=True, canonical_fastrpc_source_integrated=True,
              actual_intree_target_built=True, intree='Y', no_provenance_macro_inserted=True,
              source_sha256=p.digest(source), module_sha256=p.digest(module.read_bytes()), module_bytes=module.stat().st_size,
              canonical_unstripped_ko_sha256=p.digest((driver / 'fastrpc.ko').read_bytes()),
              vermagic=info('vermagic'), imports_same_as_reviewed_candidate=True, w1_warnings=0,
              seconds_including_validation=round(time.monotonic() - started, 3),
              unrelated_canonical_inputs_and_image_dtb_unchanged=True,
              full16798_symbols_and772_order_preserved=True, changed_snapshot_entries=sorted(changed),
              running_phone_still_external_candidate=True, next_clean_boot_required=True)
(REF / 'intree-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state = json.loads((PRIVATE / 'current-work-private.json').read_text())
state.update(state='canonical source integrated; real in-tree module built; phone still verified external candidate with OOT taint4096',
             next='Stage intree module and controlled boot to verify taint0; current sensor tests passed; preserve first observer failure and external artifact')
(PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
