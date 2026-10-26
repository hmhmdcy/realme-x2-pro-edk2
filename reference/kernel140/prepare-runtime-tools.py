from pathlib import Path
import ast
import json

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel140'
base = r / 'reference/kernel139'
assert not (ref / 'collect-preflash.sh').exists()

def adapt(name):
    return (base / name).read_text().replace('kernel139', 'kernel140').replace('k139', 'k140').replace('K139', 'K140')

def write(name, t):
    if name.endswith('.py'):
        ast.parse(t)
    (ref / name).write_text(t)

t = adapt('collect-preflash.sh').replace('/var/lib/samurai/k137-rollback132-runtime/boot-id-private.txt', '/var/lib/samurai/k139-first-runtime/boot-id-private.txt')
t = t.replace('FRESH132', 'FRESH139')
write('collect-preflash.sh', t)
t = adapt('verify-preflash.py').replace("out.parent / 'kernel137/embedded-boot-id-private.txt'", "out.parent / 'kernel139/embedded-boot-id-private.txt'").replace("b'#132 SMP'", "b'#139 SMP'")
hash139 = json.loads((base / 'unwind-build-package-validation.json').read_text())['artifacts'][1]['sha256']
t = t.replace('db6b966975b987cd51e91f9488185b0a5e4a557755cc3b7043f0e6550aa19751', hash139)
t = t.replace('stage=139, current_kernel=132', 'stage=140, current_kernel=139').replace('boot_logdump_persist_match_stable132=True', 'boot132_logdump139_persist_verified=True')
write('verify-preflash.py', t)
for old, new in [('quiesce-current132.sh', 'quiesce-current139.sh'), ('freeze-for-bootloader.sh', 'freeze-for-bootloader.sh')]:
    t = adapt(old).replace("'^#132 '", "'^#139 '").replace('CURRENT132', 'CURRENT139')
    write(new, t)
t = adapt('verify-quiesce.py').replace('current_kernel=132,target_kernel=139', 'current_kernel=139,target_kernel=140').replace('CURRENT132', 'CURRENT139')
write('verify-quiesce.py', t)
t = adapt('enter-bootloader.ps1').replace('unwind-first', 'dma-first')
write('enter-bootloader.ps1', t)
t = adapt('flash-unwind-logdump.ps1').replace('unwind-first', 'dma-first').replace('unwind-build-package-validation', 'dma-diagnostic-build-package-validation')
t = t.replace('!$build.unsubmitted_unwind_applied', '!$build.diagnostic_only_addition_to139').replace('logdump-k140-unwind.img', 'logdump-k140-dma-diagnostic.img')
t = t.replace('stage=139', 'stage=140').replace('kernel_build=139', 'kernel_build=140').replace('UNWIND_LOGDUMP', 'DMA_DIAGNOSTIC_LOGDUMP')
write('flash-diagnostic-logdump.ps1', t)
t = adapt('poll-new-boot.ps1').replace("'^#139 '", "'^#140 '").replace('unwind-ssh-', 'dma-ssh-').replace('UNWIND_SSH', 'DMA_DIAGNOSTIC_SSH')
write('poll-new-boot.ps1', t)
t = adapt('collect-runtime.sh').replace("'^#139 '", "'^#140 '").replace('UNWIND132', 'DMA_DIAGNOSTIC132')
write('collect-runtime.sh', t)
t = adapt('verify-runtime.py').replace('#139 SMP', '#140 SMP').replace('unwind-build-package-validation', 'dma-diagnostic-build-package-validation')
t = t.replace('stage=139, kernel_build=139', 'stage=140, kernel_build=140').replace('boot132_and_logdump139', 'boot132_and_logdump140')
t = t.replace('unsubmitted_unwind_applied=True', 'unsubmitted_unwind_applied=True, diagnostic_only_addition_to139=True')
write('verify-runtime.py', t)
t = adapt('observe-first-health.py').replace("'#139 '", "'#140 '").replace('stage=139, current_kernel=139', 'stage=140, current_kernel=140')
write('observe-first-health.py', t)
t = adapt('peek-health.py').replace("'#139 '", "'#140 '").replace('kernel_build=139', 'kernel_build=140')
write('peek-health.py', t)
t = adapt('enable-transition-eud.ps1').replace('unwind-first', 'dma-first')
write('enable-transition-eud.ps1', t)
print('K140_DISTINCT_CURRENT139_AND_DIAGNOSTIC140_RUNTIME_TOOLS_READY')
