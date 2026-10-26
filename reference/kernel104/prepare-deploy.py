from pathlib import Path
import json

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel104'
old = root / 'reference/kernel103'
out = Path('/mnt/e/edk2-samurai-out/kernel104')
prev = out.parent / 'kernel103'
candidate = json.loads((prev / 'candidate-validation.json').read_text())
tests = json.loads((prev / 'tests-validation.json').read_text())
names = ['build-firmware.sh', 'verify-firmware.py', 'collect-preflash.sh',
         'split-backups.sh', 'receive-backups.ps1', 'scp-private.ps1',
         'reboot-f1.ps1', 'read-eud.ps1', 'stop-connectivity.sh',
         'flash-audio.ps1', 'haptics-device']
for name in names:
    assert not (ref / name).exists()
    s = (old / name).read_text().replace('kernel103', 'kernel104').replace('k103', 'k104').replace('K103', 'K104')
    if name in ('collect-preflash.sh', 'split-backups.sh'):
        s = s.replace('#101 SMP PREEMPT', '#102 SMP PREEMPT')
    if name == 'collect-preflash.sh':
        s = s.replace('#101 SMP PREEMPT', '#102 SMP PREEMPT')
        s = s.replace('head -c 6682624', 'head -c ' + str(candidate['boot_bytes']))
        s = s.replace('94fcd45f23179c3ce1bae258e40b2d0fc8e072d8a257aa78a31c59d4e83cc4ff', candidate['boot_sha256'])
        s = s.replace('6c96d1de3a12c64e321450b686d0ed62fb75e34b203e2bded5e972246f40f75d', candidate['logdump_sha256'])
    if name == 'flash-audio.ps1':
        s = s.replace('$audit.kernel_build -ne 102', '$audit.kernel_build -ne 103')
    (ref / name).write_text(s)
s = (old / 'package-audit-generated.py').read_text().replace('kernel103', 'kernel104').replace('k103', 'k104')
s = s.replace('4b3e76ae4c1ea5da894f219c20e5ca680785afd880dc2dd9fce09a3f914566ea', tests['full_boot_readback_sha256'])
s = s.replace('6c96d1de3a12c64e321450b686d0ed62fb75e34b203e2bded5e972246f40f75d', candidate['logdump_sha256'])
s = s.replace('kernel_build=102,logical_stage=103', 'kernel_build=103,logical_stage=104')
(ref / 'prepare-package.py').write_text(s)
(out / 'fastboot-identity.json').write_bytes((prev / 'fastboot-identity.json').read_bytes())
(out / 'wpa-5g-private.conf').write_bytes((prev / 'wpa-5g-private.conf').read_bytes())
print('FRESH_STAGE104_DEPLOY_TOOLS_PREPARED')
