#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k145-preflash
dest=/var/lib/samurai/k145-quiesce
uname -v | grep -q '^#140 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test ! -e /tmp/k145-quiesce-private.tar
test ! -e "$dest/SHA256SUMS"
test ! -e "$dest/shutdown-state-validation.json"
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
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(grep -c 'powered=0 muted=1' /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status | cut -d: -f2 | awk '{s+=$1} END {print s}')" = 2
for name in display radio; do test "$(cat /sys/kernel/tracing/instances/$name/tracing_on)" = 0; done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/completion-nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/completion-source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/completion-vendor-check.txt"
sha256sum -c "$before/partition-check.sha256" > "$dest/completion-partition-check.txt"
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c "$before/old132-module-tree.sha256") > "$dest/completion-new-module-check.txt"
python3 /tmp/k145-check-quiesce-state.py --record
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k145-quiesce-private.tar .
echo K145_PREVIOUSLY_STOPPED140_QUIESCE_SEALED_NO_STOP_REPLAY
