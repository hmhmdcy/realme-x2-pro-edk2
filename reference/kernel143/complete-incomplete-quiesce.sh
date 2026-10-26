#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k143-quiesce
test ! -e /tmp/k143-quiesce-private.tar
test ! -e "$dest/SHA256SUMS"
test -z "$(pgrep -u 10000 || true)"
test -z "$(pgrep -x phosh || true)"
test -z "$(pgrep -x phoc || true)"
test -z "$(pidof wpa_supplicant || true)"
test -z "$(pidof ModemManager || true)"
test -z "$(pidof hexagonrpcd || true)"
test ! -e /proc/asound/card0
test ! -e /sys/bus/platform/devices/18800000.wifi/driver
test "$(wc -l < /sys/kernel/debug/dri/1/clients)" = 1
test "$(grep -c 'active=1' /sys/kernel/debug/dri/1/state || true)" = 0
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
for name in display radio; do test "$(cat /sys/kernel/tracing/instances/$name/tracing_on)" = 0; done
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(grep -c 'powered=0 muted=1' /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status | cut -d: -f2 | awk '{s+=$1} END {print s}')" = 2
python3 /tmp/k143-check-known-quiesce-warning.py --record
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k143-quiesce-private.tar .
echo K143_QUIESCE_COMPLETED_WITH_EXACT_OLD_WARNING_RETAINED
