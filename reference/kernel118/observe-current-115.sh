#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k118-current115-observation
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-final-health/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
pgrep -x phosh >/dev/null
pgrep -x phoc >/dev/null
test -c /dev/dri/card0
test -c /dev/dri/renderD128
mkdir -m 700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before.txt"
count=0
while test "$count" -lt 10; do
    date -u '+%Y-%m-%dT%H:%M:%SZ'
    cat /proc/uptime /proc/sys/kernel/tainted
    pgrep -x phosh
    pgrep -x phoc
    test -c /dev/dri/card0
    test -c /dev/dri/renderD128
    sleep 30
    count=$((count+1))
done > "$dest/samples.txt"
dmesg > "$dest/dmesg-after.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/sensor-power.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-verify.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-verify.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-verify.txt"
echo CURRENT115_READONLY_300_SECOND_WINDOW_COMPLETE
