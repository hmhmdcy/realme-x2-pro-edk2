#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k137-first-runtime
test -d "$dest"
test ! -e "$dest/SHA256SUMS"
test -e "$dest/bluez-service.txt"
test ! -e "$dest/gui-config-check.txt"
uname -v | grep -q '^#137 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
rc-service bluetooth status > "$dest/bluez-service-resume.txt"
sha256sum -c /var/lib/samurai/k135-preflash/gui-config.sha256 > "$dest/gui-config-check.txt"
iw dev wlan0 link > "$dest/wifi-link-private.txt"
cat /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_update/format > "$dest/vm-update-format.txt"
cat /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_switch_enqueue/format > "$dest/vm-switch-format.txt"
cat /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_update/enable /sys/kernel/tracing/events/drm_msm_gpu/msm_gpu_vm_switch_enqueue/enable > "$dest/vm-events-default.txt"
dmesg > "$dest/dmesg.txt"
cp /home/cy122/.local/state/samurai-phosh-session.log "$dest/phosh-session-private.txt" 2>/dev/null || true
printf '%s\n' '{"initial_collection_exit":3,"initial_bluetooth_status_not_ready":true,"remaining_collection_only":true,"partition_i2c_or_boot_operations_replayed":false}' > "$dest/resumption.json"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/resume-state.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k137-first-runtime-private.tar.gz .
echo K137_INITIAL_RUNTIME_REMAINING_CAPTURED_SAME_BOOT_NO_OPERATION_REPLAY
