from pathlib import Path

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel136'
t = (r / 'reference/kernel135/collect-rollback-final.sh').read_text()
t = t.replace('k135-rollback132-final', 'k136-first-runtime').replace('K135_STABLE132_AUTOMATIC_FINAL', 'K136_DIAGNOSTIC132_FIRST')
t = t.replace("grep -q '^#132 '", "grep -q '^#136 '")
t = t.replace('/var/lib/samurai/k135-first-runtime/boot-id-private.txt', '/var/lib/samurai/k136-preflash/boot-id-private.txt')
t = t.replace('dmesg > "$dest/dmesg.txt"', '''cat /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_update/format > "$dest/vm-update-format.txt"
cat /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_switch_enqueue/format > "$dest/vm-switch-format.txt"
cat /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_update/enable /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_switch_enqueue/enable > "$dest/vm-events-default.txt"
dmesg > "$dest/dmesg.txt"''')
assert not (ref / 'collect-runtime.sh').exists()
(ref / 'collect-runtime.sh').write_text(t)
print('K136_FIRST_BOOT_COLLECTOR_READY', flush=True)
