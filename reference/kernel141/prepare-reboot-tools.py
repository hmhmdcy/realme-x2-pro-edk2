from pathlib import Path
import ast
import hashlib
import json

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel141'
out = Path('/mnt/e/edk2-samurai-out/kernel141')
base = r / 'reference/kernel140'
assert not (ref / 'collect-preflash.sh').exists()
bundle = json.loads((base / 'dma-diagnostic-build-package-validation.json').read_text())
assert bundle['actual_runtime_verified'] and bundle['kernel_build'] == 140
for record in bundle['artifacts']:
    path = Path(record['artifact_path'])
    assert path.stat().st_size == record['bytes']
    h = hashlib.sha256()
    with path.open('rb') as f:
        while data := f.read(1024**2):
            h.update(data)
    assert h.hexdigest() == record['sha256']
bundle['stage'] = 141
bundle['four_artifacts_fresh_hash_verified'] = True
bundle['same_current140_kernel_reboot_only'] = True
bundle['partitions_to_write'] = []
for folder in [out, ref]:
    (folder / 'current140-build-package-validation.json').write_text(json.dumps(bundle, indent=2) + '\n')

def adapt(name):
    return (base / name).read_text().replace('kernel140', 'kernel141').replace('k140', 'k141').replace('K140', 'K141')

def write(name, t):
    assert not (ref / name).exists()
    if name.endswith('.py'):
        ast.parse(t)
    (ref / name).write_text(t)

t = adapt('collect-preflash.sh').replace('/var/lib/samurai/k139-first-runtime/boot-id-private.txt', '/var/lib/samurai/k140-first-runtime/boot-id-private.txt')
write('collect-preflash.sh', t)
t = adapt('verify-preflash.py').replace("out.parent / 'kernel139/embedded-boot-id-private.txt'", "out.parent / 'kernel140/embedded-boot-id-private.txt'")
t = t.replace("b'#139 SMP'", "b'#140 SMP'")
hash139 = json.loads((r / 'reference/kernel139/unwind-build-package-validation.json').read_text())['artifacts'][1]['sha256']
t = t.replace(hash139, bundle['artifacts'][1]['sha256'])
t = t.replace('stage=140, current_kernel=139', 'stage=141, current_kernel=140').replace('boot132_logdump139', 'boot132_logdump140')
write('verify-preflash.py', t)
for old, new in [('quiesce-current139.sh', 'quiesce-current140.sh'), ('freeze-for-bootloader.sh', 'freeze-for-bootloader.sh')]:
    t = adapt(old).replace("'^#139 '", "'^#140 '").replace('CURRENT139', 'CURRENT140')
    write(new, t)
t = adapt('verify-quiesce.py').replace('current_kernel=139,target_kernel=140', 'current_kernel=140,target_kernel=140').replace('CURRENT139', 'CURRENT140')
write('verify-quiesce.py', t)
t = adapt('enter-bootloader.ps1').replace('dma-first', 'startup-first')
write('enter-bootloader.ps1', t)
t = adapt('enable-transition-eud.ps1').replace('dma-first', 'startup-first')
write('enable-transition-eud.ps1', t)
t = adapt('collect-runtime.sh')
write('collect-runtime.sh', t)
t = adapt('verify-runtime.py').replace("ref / 'dma-diagnostic-build-package-validation.json'", "ref / 'current140-build-package-validation.json'")
t = t.replace('stage=140, kernel_build=140', 'stage=141, kernel_build=140').replace('boot132_and_logdump140', 'boot132_and_logdump140')
write('verify-runtime.py', t)
write('check-new-boot.py', '''from pathlib import Path
import os
assert os.uname().version.startswith('#140 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() != Path('/var/lib/samurai/k141-preflash/boot-id-private.txt').read_bytes()
print('K141_NEW140_BOOT_CONFIRMED')
''')
print('K141_SAME140_REBOOT_ONLY_PREFLIGHT_AND_RUNTIME_TOOLS_READY')
