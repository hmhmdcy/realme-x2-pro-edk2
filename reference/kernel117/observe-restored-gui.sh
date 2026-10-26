#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k117-restored-gui-observation
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-final-health/boot-id-private.txt)"
test -c /dev/dri/card0;test -c /dev/dri/renderD128
pgrep -x phosh >/dev/null;pgrep -x phoc >/dev/null
mkdir -m700 "$dest"
dmesg > "$dest/dmesg-before-private.txt"
cat /proc/uptime > "$dest/uptime-before.txt"
sleep 45
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -v > "$dest/uname.txt"
cat /proc/uptime > "$dest/uptime-after.txt"
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
pgrep -x phosh > "$dest/phosh.txt" || true
pgrep -x phoc > "$dest/phoc.txt" || true
cat /sys/class/drm/card0-DSI-1/status > "$dest/connector.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensors.txt"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
rc-status default > "$dest/services.txt"
cat /proc/swaps > "$dest/zram.txt"
cat /sys/class/net/wlan0/operstate > "$dest/wlan.txt"
mmcli -m 0 -J > "$dest/modem-private.json"
cat /sys/kernel/tracing/instances/display/tracing_on /sys/kernel/tracing/instances/radio/tracing_on > "$dest/traces.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partition-check.sha256"
tail -n 180 /home/cy122/.local/state/samurai-phosh-session.log > "$dest/session-tail-private.txt"
dmesg > "$dest/dmesg-after-private.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k117-restored-gui-observation-private.tar.gz .
sha256sum /tmp/k117-restored-gui-observation-private.tar.gz
echo SAME_BOOT_GUI45S_OBSERVATION_SAVED
