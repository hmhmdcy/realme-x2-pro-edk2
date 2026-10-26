#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k136-preflash
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k132+
test "$(cat /proc/sys/kernel/tainted)" = 0
test -f "$dest/phosh.txt"
test ! -s "$dest/phosh.txt"
test ! -f "$dest/phoc.txt"
test ! -f "$dest/SHA256SUMS"
# The original collection stopped when Phosh exited after the saved GPU fault.
# Continue only its remaining read-only fields; retain the empty original file.
pgrep -x phoc > "$dest/phoc.txt" || true
cat /sys/class/drm/card1-DSI-1/status > "$dest/connector.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensors.txt"
for name in display radio; do cat "/sys/kernel/tracing/instances/$name/tracing_on"; done > "$dest/traces.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg.txt"
cp /home/cy122/.local/state/samurai-phosh-session.log "$dest/phosh-post-fault-private.txt"
cat /proc/mounts > "$dest/mounts.txt"
uname -a > "$dest/uname.txt"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k136-preflash-private.tar.gz .
echo K136_READONLY_PREFLASH_REMAINING_FIELDS_SAVED_DESKTOP_FAILURE_RETAINED
