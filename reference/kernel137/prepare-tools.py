from pathlib import Path
import ast

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel137'
base = r / 'reference/kernel136'
assert not (ref / 'collect-preflash.sh').exists()

def write(name, text):
    if name.endswith('.py'):
        ast.parse(text)
    (ref / name).write_text(text)

t = (base / 'collect-runtime.sh').read_text()
t = t.replace('k136-first-runtime', 'k137-preflash').replace('K136_DIAGNOSTIC132_FIRST_RUNTIME_CAPTURED', 'K137_CURRENT136_PREFLASH_CAPTURED')
t = t.replace('test "$(cat /proc/sys/kernel/random/boot_id)" != "$(cat /var/lib/samurai/k136-preflash/boot-id-private.txt)"',
              'test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k136-first-runtime/boot-id-private.txt)"')
t = t.replace('sha256sum /tmp/k137-preflash-private.tar.gz', '')
t = t.replace('sync\n(cd', 'cp /var/lib/samurai/k132-preflash/new-module-tree.sha256 "$dest/old132-module-tree.sha256"\nsync\n(cd')
write('collect-preflash.sh', t)

t = (base / 'quiesce-current132.sh').read_text().replace('k136', 'k137').replace('K136', 'K137')
t = t.replace("'^#132 '", "'^#136 '").replace('CURRENT132', 'CURRENT136')
t = t.replace('"$(cat /proc/sys/kernel/tainted)" = 0', '"$(cat /proc/sys/kernel/tainted)" = 512')
write('quiesce-current136.sh', t)

t = (base / 'verify-quiesce.py').read_text().replace('kernel136', 'kernel137').replace('K136', 'K137')
t = t.replace("==b'0'", "==b'512'").replace('current_kernel=132,target_kernel=136', 'current_kernel=136,target_kernel=137')
t = t.replace('taint=0,', 'taint=512,preexisting_wcd_warning_preserved=True,clean_runtime_accepted=False,')
write('verify-quiesce.py', t)

t = (base / 'freeze-for-bootloader.sh').read_text().replace('k136', 'k137').replace('K136', 'K137')
t = t.replace("'^#132 '", "'^#136 '").replace('"$(cat /proc/sys/kernel/tainted)" = 0', '"$(cat /proc/sys/kernel/tainted)" = 512')
write('freeze-for-bootloader.sh', t)

t = (base / 'enter-bootloader.ps1').read_text().replace('kernel136', 'kernel137').replace('k136', 'k137').replace('K136', 'K137')
t = t.replace('vm-trace-first', 'mfd-cleanup-first').replace("$eudLines[0].Value -notmatch '\\bShared\\s*$'", "$eudLines[0].Value.TrimEnd() -notlike '*Shared'")
write('enter-bootloader.ps1', t)

t = (base / 'flash-trace-logdump.ps1').read_text().replace('kernel136', 'kernel137').replace('k136', 'k137').replace('K136', 'K137')
t = t.replace('vm-trace-first', 'mfd-cleanup-first').replace('trace-build-package-validation', 'audio-build-package-validation')
t = t.replace('!$build.instrumentation_only', '!$build.upstream_mfd_cleanup_applied')
t = t.replace('logdump-k137-vm-trace.img', 'logdump-k137-audio-cleanup.img')
t = t.replace('kernel_build=136', 'kernel_build=137').replace('stage=136', 'stage=137').replace('instrumentation_only=$true', 'upstream_mfd_cleanup_applied=$true')
t = t.replace('DIAGNOSTIC_LOGDUMP', 'AUDIO_CLEANUP_LOGDUMP')
write('flash-audio-logdump.ps1', t)

t = (base / 'poll-new-boot.ps1').read_text().replace('kernel136', 'kernel137').replace('K136', 'K137').replace("'^#136 '", "'^#137 '")
t = t.replace('trace-ssh-', 'audio-ssh-').replace('NATIVE_DIAGNOSTIC', 'AUDIO_CLEANUP')
write('poll-new-boot.ps1', t)

t = (base / 'collect-runtime.sh').read_text().replace('k136', 'k137').replace('K136', 'K137').replace("'^#136 '", "'^#137 '")
t = t.replace('DIAGNOSTIC132', 'AUDIO_CLEANUP132').replace('sha256sum /tmp/k137-first-runtime-private.tar.gz', '')
write('collect-runtime.sh', t)

t = (base / 'verify-runtime.py').read_text().replace('kernel136', 'kernel137').replace('#136 SMP', '#137 SMP')
t = t.replace('trace-build-package-validation', 'audio-build-package-validation').replace('stage=136, kernel_build=136', 'stage=137, kernel_build=137')
t = t.replace('boot132_and_logdump136_readback_exact', 'boot132_and_logdump137_readback_exact')
t = t.replace("('codec_enospc', r'Failed to read.*-28')", "('codec_enospc', r'Failed to read.*-28'), ('dma_tx_prepare_failure', r'unable to prepare channel')")
write('verify-runtime.py', t)

t = (base / 'record-trace-build.py').read_text().replace('kernel136', 'kernel137')
# Reuse the archived C-drive build tree; stable132 and 136 artifacts are kept.
t = t.replace("stage = Path('/home/cy122/pmos-samurai-kernel137')", "stage = Path('/home/cy122/pmos-samurai-kernel136')")
t = t.replace('#136 SMP PREEMPT', '#137 SMP PREEMPT').replace('trace-', 'audio-').replace('vm-trace-private', 'audio-cleanup-private').replace('vm-trace.img', 'audio-cleanup.img')
t = t.replace("stage / 'modules-root'", "stage / 'modules-root137'")
t = t.replace("['audio-msm-build-private.log', 'audio-image-build-private.log']", "['audio-objects-build-private.log', 'audio-image-build-private.log']")
t = t.replace('stage=136, kernel_build=136', 'stage=137, kernel_build=137')
t = t.replace('instrumentation_only=True,', 'upstream_mfd_cleanup_applied=True, dma_failure_diagnostics_added=True,')
t = t.replace('K136_', 'K137_')
t = t.replace('Image-k136-vm-audio-private', 'Image-k137-audio-cleanup-private').replace('logdump-k136-audio-cleanup.img', 'logdump-k137-audio-cleanup.img')
write('record-audio-build.py', t)
print('K137_DISTINCT_PREFLASH_QUIESCE_FLASH_RUNTIME_TOOLS_PREPARED', flush=True)
