#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k114-final-health
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k114-rootfs-export/boot-id-private.txt)"
mkdir -m700 "$dest"
uname -v > "$dest/uname.txt"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensor.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
test -z "$(pidof qmicli || true)"
for trace in /sys/kernel/tracing/instances/*; do
    test -d "$trace" || continue
    printf '%s ' "${trace##*/}" >> "$dest/traces.txt"
    cat "$trace/tracing_on" >> "$dest/traces.txt"
done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
rc-status -a > "$dest/services.txt"
df -h / > "$dest/storage.txt"
dmesg > "$dest/dmesg.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k114-final-health-private.tar.gz .
sha256sum /tmp/k114-final-health-private.tar.gz
