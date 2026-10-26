#!/bin/sh
# One normal DRM panel cycle after preserving the failing state.
set -eu
out=/tmp/k108-display-recovery-once
test ! -e "$out"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /tmp/k108-display-expected-boot-private.txt)"
uname -v | grep -q '^#106 '
test "$(cat /proc/sys/kernel/tainted)" = 0
test -s /tmp/k108-display-live-detail.tar
test -x /tmp/k108-display-cycle
test "$(sha256sum /tmp/k108-display-cycle | cut -d ' ' -f 1)" = "$(cat /tmp/k108-display-cycle.sha256)"
mkdir -m 700 "$out"
cat /proc/sys/kernel/random/boot_id > "$out/boot-id-private.txt"
cat /proc/uptime > "$out/uptime-before.txt"
cat /sys/kernel/debug/dri/1/kms > "$out/kms-before.txt"
cat /sys/kernel/debug/clk/clk_summary > "$out/clocks-before.txt"
cat /sys/kernel/debug/dri/1/state > "$out/drm-before.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$out/encoder-before.txt"
dmesg > "$out/dmesg-before.txt"
sha256sum /sys/kernel/tracing/instances/display/snapshot > "$out/snapshot-before.sha256"
set +e
/tmp/k108-display-cycle > "$out/kms-cycle.txt" 2>&1
result=$?
set -e
printf '%s\n' "$result" > "$out/cycle-exit.txt"
cat /proc/uptime > "$out/uptime-after.txt"
for seconds in 0 10 30 60; do
    case "$seconds" in 0) ;; 10) sleep 10 ;; 30) sleep 20 ;; 60) sleep 30 ;; esac
    cat /proc/uptime > "$out/uptime-$seconds.txt"
    dmesg > "$out/dmesg-$seconds.txt"
    cat /sys/kernel/debug/dri/1/encoder-0/status > "$out/encoder-$seconds.txt"
done
cat /sys/kernel/debug/dri/1/kms > "$out/kms-after.txt"
cat /sys/kernel/debug/clk/clk_summary > "$out/clocks-after.txt"
cat /sys/kernel/debug/dri/1/state > "$out/drm-after.txt"
cat /sys/class/backlight/ae94000.dsi.0/brightness > "$out/brightness-after.txt"
cat /proc/sys/kernel/tainted > "$out/taint-after.txt"
/usr/sbin/samurai-modem-remoteproc > "$out/modem-node-private.txt"
for node in /sys/class/remoteproc/remoteproc*; do
    cat "$node/name" "$node/state"
done > "$out/remoteprocs.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status | sed -n -e '/^wpa_state=/p' -e '/^freq=/p' > "$out/wifi-status.txt"
sha256sum /sys/kernel/tracing/instances/display/snapshot > "$out/snapshot-after.sha256"
tar -cf "$out.tar" -C /tmp "$(basename "$out")"
printf 'DISPLAY_CYCLE_EXIT=%s OBSERVATION_SECONDS=60\n' "$result"
exit "$result"
