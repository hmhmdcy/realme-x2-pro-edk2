#!/bin/sh
# A bounded GNSS session. Position and satellite output stays private.
set -eu
umask 077
dest=/var/lib/samurai/k114-gnss-window
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k114-rootfs-export/boot-id-private.txt)"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
started=0
cleanup() {
    stop_result=0
    if test "$started" = 1; then
        timeout -s TERM -k 3 30 qmicli -d qrtr://0 --loc-session-id=114 --loc-stop > "$dest/stop-private.txt" 2>&1 || stop_result=$?
        printf '%s\n' "$stop_result" > "$dest/stop-result.txt"
    fi
}
trap cleanup EXIT
timeout -s TERM -k 3 55 qmicli -d qrtr://0 --loc-follow-position-report --loc-follow-gnss-sv-info --loc-follow-nmea > "$dest/monitor-private.txt" 2>&1 &
monitor=$!
sleep 2
start_result=0
timeout -s TERM -k 3 30 qmicli -d qrtr://0 --loc-session-id=114 --loc-start > "$dest/start-private.txt" 2>&1 || start_result=$?
printf '%s\n' "$start_result" > "$dest/start-result.txt"
if test "$start_result" = 0; then started=1; fi
monitor_result=0
wait "$monitor" || monitor_result=$?
printf '%s\n' "$monitor_result" > "$dest/monitor-result.txt"
cleanup
trap - EXIT
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state /proc/sys/kernel/tainted > "$dest/state-after.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k114-gnss-window-private.tar.gz .
sha256sum /tmp/k114-gnss-window-private.tar.gz
cat "$dest/start-result.txt" "$dest/monitor-result.txt" "$dest/stop-result.txt"
