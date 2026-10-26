#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k119-current118-observation
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test -s "$dest/dmesg-after.txt"
test "$(grep -Ec '(^20[0-9][0-9]-| UTC 2026$)' "$dest/samples.txt")" = 10
date -u '+%s' > "$dest/finished-epoch.txt"
test "$(cat /proc/sys/kernel/tainted)" = 0
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
card=$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)
test -c "$card"
card_name=${card##*/}
minor=${card_name#card}
case "$minor" in *[!0-9]*|'') exit 2;; esac
cat /sys/kernel/debug/dri/$minor/state > "$dest/drm-state.txt"
cat /sys/kernel/debug/dri/$minor/clients > "$dest/drm-clients.txt"
printf '%s\n' "$card_name" > "$dest/drm-card-name.txt"

test -c /dev/dri/renderD128
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/sensor-power.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-verify.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-verify.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-verify.txt"
cat /sys/class/drm/$card_name-DSI-1/status > "$dest/connector.txt"
cat /sys/class/net/wlan0/operstate > "$dest/wlan.txt"
cat /proc/swaps > "$dest/swaps.txt"
cat /sys/kernel/tracing/instances/display/tracing_on /sys/kernel/tracing/instances/radio/tracing_on > "$dest/traces.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partition-check.sha256"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
timeout 10 mmcli -m 0 -J > "$dest/modem-private.json" 2>&1 || true
cp /home/cy122/.local/state/samurai-phosh-session.log "$dest/phosh-session-private.txt"
cd "$dest"

find . -type f ! -name SHA256SUMS -exec sha256sum {} \; > SHA256SUMS
tar -czf /tmp/k119-current118-health-private.tar.gz .
echo CURRENT118_300_SECOND_NATIVE_HEALTH_ARCHIVED
