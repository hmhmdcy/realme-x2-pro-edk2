#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k118-current115-observation
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test -s "$dest/dmesg-after.txt"
test "$(grep -Ec '(^20[0-9][0-9]-| UTC 2026$)' "$dest/samples.txt")" = 10
date -u '+%s' > "$dest/finished-epoch.txt"
test "$(cat /proc/sys/kernel/tainted)" = 0
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
test -c /dev/dri/card0
test -c /dev/dri/renderD128
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/sensor-power.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-verify.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-verify.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-verify.txt"
cat /sys/class/drm/card0-DSI-1/status > "$dest/connector.txt"
cat /sys/class/net/wlan0/operstate > "$dest/wlan.txt"
cat /proc/swaps > "$dest/swaps.txt"
cat /sys/kernel/tracing/instances/display/tracing_on /sys/kernel/tracing/instances/radio/tracing_on > "$dest/traces.txt"
cd "$dest"
find . -type f ! -name SHA256SUMS -exec sha256sum {} \; > SHA256SUMS
tar -czf /tmp/k118-current115-health-private.tar.gz .
echo CURRENT115_300_SECOND_NATIVE_HEALTH_ARCHIVED
