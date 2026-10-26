#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k119-post-pixel-fault
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k119-first-runtime/boot-id-private.txt)"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
sleep 5
dmesg > "$dest/dmesg.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
pgrep -x phosh > "$dest/phosh.txt" || true
pgrep -x phoc > "$dest/phoc.txt" || true
card=$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)
test -c "$card"
card_name=${card##*/}
minor=${card_name#card}
case "$minor" in *[!0-9]*|'') exit 2;; esac
cat /sys/kernel/debug/dri/$minor/state > "$dest/drm-state.txt"
cat /sys/kernel/debug/dri/$minor/clients > "$dest/drm-clients.txt"
timeout -s TERM -k 2 10 cat /sys/kernel/debug/dri/$minor/gpu > "$dest/gpu-debug-private.txt" 2> "$dest/gpu-debug.err" || true
mkdir -m700 "$dest/devcoredump"
for data in /sys/class/devcoredump/devcd*/data; do
    test -f "$data" || continue
    name=${data%/data};name=${name##*/}
    timeout -s TERM -k 2 10 cat "$data" > "$dest/devcoredump/$name-private.data" 2> "$dest/devcoredump/$name.err" || true
done
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensors.txt"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
cat /sys/class/net/wlan0/operstate > "$dest/wlan.txt"
cat /proc/swaps > "$dest/swaps.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
sha256sum -c /var/lib/samurai/k119-benchmark-source/package-db-before.sha256 > "$dest/package-db-check.txt"
cat /sys/kernel/tracing/instances/display/tracing_on /sys/kernel/tracing/instances/radio/tracing_on > "$dest/traces.txt"
cp /home/cy122/.local/state/samurai-phosh-session.log "$dest/phosh-session-private.txt"
cd "$dest"
find . -type f ! -name SHA256SUMS -exec sha256sum {} \; > SHA256SUMS
tar -czf /tmp/k119-post-pixel-fault-private.tar.gz .
sha256sum /tmp/k119-post-pixel-fault-private.tar.gz
echo POST_PIXEL_DELAYED_FAULT_NATIVE_AND_COREDUMP_CAPTURED_NO_RESET
