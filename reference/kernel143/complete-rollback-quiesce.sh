#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k143-rollback-quiesce
test ! -e /tmp/k143-rollback-quiesce-private.tar
test ! -e "$dest/SHA256SUMS"
test -z "$(pgrep -u 10000 || true)"
test ! -e /proc/asound/card0
test ! -e /sys/bus/platform/devices/18800000.wifi/driver
test "$(wc -l < /sys/kernel/debug/dri/1/clients)" = 1
test "$(grep -c 'active=1' /sys/kernel/debug/dri/1/state || true)" = 0
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(grep -c 'powered=0 muted=1' /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status | cut -d: -f2 | awk '{s+=$1} END {print s}')" = 2
python3 /tmp/k143-check-rollback-warning.py --record
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k143-rollback-quiesce-private.tar .
echo K143_ROLLBACK_QUIESCE_SEALED_RECORDED70_NULL_DOWN_DMA_ERRORS
