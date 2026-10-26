from pathlib import Path
import ast
import hashlib
import json

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel137'
out = Path('/mnt/e/edk2-samurai-out/kernel137')
failure = json.loads((ref / 'first-runtime-validation.json').read_text())
assert failure['new_boot_verified'] and failure['taint'] == 0 and failure['counts']['dsi_errors'] > 0
failure['candidate_rejected'] = True
failure['display_fifo_underflow_observed'] = True
(ref / 'first-runtime-validation.json').write_text(json.dumps(failure, indent=2) + '\n')
(out / 'rejected-boot-id-private.txt').write_bytes((out / 'embedded-boot-id-private.txt').read_bytes())

def write(name, text):
    assert not (ref / name).exists()
    if name.endswith('.py'):
        ast.parse(text)
    (ref / name).write_text(text)

t = (ref / 'quiesce-current136.sh').read_text()
t = t.replace('before=/var/lib/samurai/k137-preflash', 'before=/var/lib/samurai/k137-first-runtime')
t = t.replace('k137-quiesce', 'k137-rollback-quiesce').replace("'^#136 '", "'^#137 '")
t = t.replace('"$(cat /proc/sys/kernel/tainted)" = 512', '"$(cat /proc/sys/kernel/tainted)" = 0')
t = t.replace('"$before/old132-module-tree.sha256"', '/var/lib/samurai/k132-preflash/new-module-tree.sha256')
t = t.replace('CURRENT136_PREFLASH', 'REJECTED137_ROLLBACK')
write('quiesce-for-rollback.sh', t)

t = (ref / 'verify-quiesce.py').read_text()
t = t.replace('quiesce-private.tar', 'rollback-quiesce-private.tar').replace('source-boot-id-private.txt', 'rejected-boot-id-private.txt')
t = t.replace("==b'512'", "==b'0'").replace('current_kernel=136,target_kernel=137', 'current_kernel=137,target_kernel=132')
t = t.replace('taint=512,preexisting_wcd_warning_preserved=True,', 'taint=0,rejected_display_error_boot=True,')
t = t.replace('quiesce-validation.json', 'rollback-quiesce-validation.json').replace('CURRENT132', 'REJECTED137')
write('verify-rollback-quiesce.py', t)

t = (ref / 'freeze-for-bootloader.sh').read_text()
t = t.replace('before=/var/lib/samurai/k137-preflash', 'before=/var/lib/samurai/k137-first-runtime').replace('k137-quiesce', 'k137-rollback-quiesce')
t = t.replace("'^#136 '", "'^#137 '").replace('"$(cat /proc/sys/kernel/tainted)" = 512', '"$(cat /proc/sys/kernel/tainted)" = 0')
t = t.replace('"$before/old132-module-tree.sha256"', '/var/lib/samurai/k132-preflash/new-module-tree.sha256')
write('freeze-for-rollback.sh', t)

t = (ref / 'enter-bootloader.ps1').read_text()
t = t.replace('mfd-cleanup-first', 'rollback132-first').replace('source-boot-id-private.txt', 'rejected-boot-id-private.txt')
t = t.replace('quiesce-validation.json', 'rollback-quiesce-validation.json').replace('/tmp/k137-freeze-for-bootloader.sh', '/tmp/k137-freeze-for-rollback.sh')
write('enter-rollback-bootloader.ps1', t)

t = (ref / 'flash-audio-logdump.ps1').read_text()
t = t.replace('mfd-cleanup-first', 'rollback132-first').replace('audio-build-package-validation.json', 'stable-build-package-validation.json')
t = t.replace('!$build.upstream_mfd_cleanup_applied', '!$build.stable132_bundle_verified')
t = t.replace('source-boot-id-private.txt', 'rejected-boot-id-private.txt').replace('quiesce-validation.json', 'rollback-quiesce-validation.json')
t = t.replace('$image="$out/logdump-k137-audio-cleanup.img"', '$image="E:/edk2-samurai-out/kernel132/logdump-k132-charger.img"')
t = t.replace('kernel_build=137', 'kernel_build=132').replace('upstream_mfd_cleanup_applied=$true', 'rollback_target=132')
t = t.replace('flash-validation.json', 'rollback-flash-validation.json').replace('AUDIO_CLEANUP_LOGDUMP', 'STABLE132_ROLLBACK_LOGDUMP')
write('flash-stable132-rollback.ps1', t)

t = (ref / 'poll-new-boot.ps1').read_text().replace('audio-ssh-', 'rollback-ssh-').replace("'^#137 '", "'^#132 '").replace('AUDIO_CLEANUP', 'STABLE132_ROLLBACK')
write('poll-rollback-boot.ps1', t)

t = (ref / 'collect-runtime.sh').read_text().replace('k137-first-runtime', 'k137-rollback132-runtime').replace("'^#137 '", "'^#132 '")
t = t.replace('/var/lib/samurai/k137-preflash/boot-id-private.txt', '/var/lib/samurai/k137-first-runtime/boot-id-private.txt')
t = t.replace('rc-service bluetooth status >', 'rc-service bluetooth status >').replace(' > "$dest/bluez-service.txt"', ' > "$dest/bluez-service.txt" || true')
t = '\n'.join(line for line in t.splitlines() if 'vm-update-format' not in line and 'vm-switch-format' not in line and 'vm-events-default' not in line) + '\n'
t = t.replace('AUDIO_CLEANUP132_FIRST_RUNTIME', 'STABLE132_ROLLBACK_RUNTIME')
write('collect-rollback-runtime.sh', t)

t = (ref / 'verify-runtime.py').read_text().replace("out / 'first-runtime-private.tar.gz'", "out / 'rollback132-runtime-private.tar.gz'")
t = t.replace('#137 SMP', '#132 SMP').replace("out / 'preflash-private.tar.gz'", "out / 'first-runtime-private.tar.gz'")
t = t.replace('audio-build-package-validation.json', 'stable-build-package-validation.json')
start = t.index("assert data['vm-events-default.txt']")
end = t.index("(out / 'embedded-boot-id-private.txt')")
t = t[:start] + t[end:]
t = t.replace('stage=137, kernel_build=137', 'stage=137, kernel_build=132').replace('boot132_and_logdump137_readback_exact', 'boot132_and_logdump132_readback_exact')
t = t.replace('new_tracepoints_present_and_default_disabled=True', 'diagnostic136_tracepoints_not_in_baseline=True')
t = t.replace('first-runtime-validation.json', 'rollback-runtime-validation.json')
write('verify-rollback-runtime.py', t)
print('K137_REJECTED_DISPLAY_CANDIDATE_EXACT_BOOT_ROLLBACK_TOOLS_READY', flush=True)
