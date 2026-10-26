from pathlib import Path
import ast

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel139'
base = r / 'reference/kernel136'
assert not (ref / 'collect-preflash.sh').exists()

def write(name, t):
    if name.endswith('.py'):
        ast.parse(t)
    (ref / name).write_text(t)

def adapt(name):
    return (base / name).read_text().replace('kernel136', 'kernel139').replace('k136', 'k139').replace('K136', 'K139')

t = adapt('collect-preflash.sh')
t = t.replace('/var/lib/samurai/k139-current132/boot-id-private.txt', '/var/lib/samurai/k137-rollback132-runtime/boot-id-private.txt')
write('collect-preflash.sh', t)
t = adapt('verify-preflash.py')
a = t.index("with tarfile.open(out / 'current132-private.tar.gz') as archive:")
b = t.index("assert data['boot-id-private.txt'] == boot", a)
t = t[:a] + "boot = (out.parent / 'kernel137/embedded-boot-id-private.txt').read_bytes()\n" + t[b:]
t = t.replace('stage=136,', 'stage=139,').replace('gpu_fault_already_saved_desktop_no_longer_accepted=True', 'current_gpu_fault_count_zero=True')
write('verify-preflash.py', t)
for name in ['quiesce-current132.sh', 'freeze-for-bootloader.sh']:
    write(name, adapt(name))
t = adapt('verify-quiesce.py').replace('target_kernel=136', 'target_kernel=139')
write('verify-quiesce.py', t)
t = adapt('enter-bootloader.ps1').replace('vm-trace-first', 'unwind-first')
t = t.replace("$eudLines[0].Value -notmatch '\\bShared\\s*$'", "$eudLines[0].Value.TrimEnd() -notlike '*Shared'")
write('enter-bootloader.ps1', t)
t = adapt('flash-trace-logdump.ps1').replace('vm-trace-first', 'unwind-first')
t = t.replace('trace-build-package-validation', 'unwind-build-package-validation').replace('instrumentation_only', 'unsubmitted_unwind_applied')
t = t.replace('logdump-k139-vm-trace.img', 'logdump-k139-unwind.img').replace('stage=136', 'stage=139').replace('kernel_build=136', 'kernel_build=139').replace('DIAGNOSTIC_LOGDUMP', 'UNWIND_LOGDUMP')
write('flash-unwind-logdump.ps1', t)
t = adapt('poll-new-boot.ps1').replace("'^#136 '", "'^#139 '").replace('trace-ssh-', 'unwind-ssh-').replace('NATIVE_DIAGNOSTIC', 'UNWIND')
write('poll-new-boot.ps1', t)
t = adapt('collect-runtime.sh').replace("'^#136 '", "'^#139 '")
t = t.replace('rc-service bluetooth status > "$dest/bluez-service.txt"', 'rc-service bluetooth status > "$dest/bluez-service.txt" 2>&1 || true')
t = t.replace('iw dev wlan0 link > "$dest/wifi-link-private.txt"', 'iw dev wlan0 link > "$dest/wifi-link-private.txt" 2>&1 || true')
a = t.index('cat /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_update/format')
b = t.index('dmesg > "$dest/dmesg.txt"', a)
t = t[:a] + 'test ! -d /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_update\ntest ! -d /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_switch_enqueue\necho BASELINE132_GPU_EVENTS > "$dest/gpu-events.txt"\n' + t[b:]
t = t.replace('sha256sum /tmp/k139-first-runtime-private.tar.gz\n', '').replace('DIAGNOSTIC132', 'UNWIND132')
write('collect-runtime.sh', t)
t = adapt('verify-runtime.py').replace('#136 SMP', '#139 SMP').replace('trace-build-package-validation', 'unwind-build-package-validation')
a = t.index("assert data['vm-events-default.txt']")
b = t.index("(out / 'embedded-boot-id-private.txt')", a)
t = t[:a] + "assert data['gpu-events.txt'].strip() == b'BASELINE132_GPU_EVENTS'\n" + t[b:]
t = t.replace("('codec_enospc', r'Failed to read.*-28')", "('codec_enospc', r'Failed to read.*-28'), ('dma_tx_prepare_failure', r'unable to prepare channel')")
t = t.replace('stage=136, kernel_build=136', 'stage=139, kernel_build=139').replace('boot132_and_logdump136', 'boot132_and_logdump139')
t = t.replace('new_tracepoints_present_and_default_disabled=True', 'baseline132_gpu_events_preserved=True, unsubmitted_unwind_applied=True')
t = t.replace("gpu_probe_allowed=taint == 0 and counts['gpu_faults'] == 0", "gpu_probe_allowed=taint == 0 and counts['gpu_faults'] == 0 and counts['dsi_errors'] == 0")
write('verify-runtime.py', t)
# Passive observation captures only current runtime; it neither starts services nor changes display.
t = (r / 'reference/kernel137/observe-rollback-health.py').read_text()
t = t.replace('kernel137', 'kernel139').replace('k137-rollback132', 'k139-first').replace('K137', 'K139')
t = t.replace("'#132 '", "'#139 '").replace('rollback-health', 'first-health')
t = t.replace('stage=137, current_kernel=132', 'stage=139, current_kernel=139')
write('observe-first-health.py', t)
print('K139_DISTINCT_BASE132_PREFLASH_TRANSITION_AND_RUNTIME_TOOLS_READY')
