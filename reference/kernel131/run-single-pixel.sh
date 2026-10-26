#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k131-single-pixel
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test ! -e "$dest/validation-private.txt"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -S /run/user/10000/wayland-0
test "$(stat -c %u /run/user/10000/wayland-0)" = 10000
pgrep -x phosh > "$dest/phosh-before.txt"
pgrep -x phoc > "$dest/phoc-before.txt"
sha256sum -c "$dest/binary.sha256" > "$dest/binary-check.txt"
dmesg > "$dest/dmesg-before.txt"
cat /proc/uptime > "$dest/uptime-before.txt"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-before-private.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dest/encoder-before.txt"
set +e
timeout -s TERM -k 2 20 su -s /bin/sh cy122 -c 'ulimit -t 10; ulimit -v 786432; exec env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 /tmp/k131-glmark2/usr/bin/glmark2-es2-wayland --off-screen --validate --debug --benchmark build:use-vbo=true --data-path /tmp/k131-glmark2/usr/share/glmark2' > "$dest/validation-private.txt" 2>&1
result=$?
set -e
printf '%s\n' "$result" > "$dest/validation-exit.txt"
cat /proc/uptime > "$dest/uptime-exit.txt"
dmesg > "$dest/dmesg-immediate.txt"
# Observe delayed fault reports without issuing another render, reset or replay.
for sample in 0 1 2 3 4 5 6; do
 printf '%s ' "$sample" >> "$dest/samples.txt"
 cat /proc/uptime >> "$dest/samples.txt"
 cat /proc/sys/kernel/tainted >> "$dest/taint-samples.txt"
 if test "$sample" != 6; then sleep 5; fi
done
pgrep -x phosh > "$dest/phosh-after.txt" || true
pgrep -x phoc > "$dest/phoc-after.txt" || true
dmesg > "$dest/dmesg-delayed.txt"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-after-private.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dest/encoder-after.txt"
if pgrep -f '^/tmp/k131-glmark2/usr/bin/glmark2-es2-wayland' > "$dest/remaining-processes.txt"; then echo BENCHMARK_PROCESS_REMAINS;exit 2;fi
for item in /sys/class/devcoredump/devcd*; do
 test -d "$item" || continue
 name=${item##*/}
 readlink -f "$item/device" > "$dest/$name-device-private.txt"
 timeout -k 2 15 cat "$item/data" > "$dest/$name-private.data"
done
sha256sum -c "$dest/package-db-before.sha256" > "$dest/package-db-final-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
iw dev wlan0 link > "$dest/wifi-link-private.txt"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
rc-service bluetooth status > "$dest/bluetooth-service.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k131-single-pixel-private.tar.gz .
sha256sum /tmp/k131-single-pixel-private.tar.gz > /tmp/k131-single-pixel-private.tar.gz.sha256
echo K131_SINGLE_BUILD_VBO_PIXEL_AND_DELAYED_FAULT_OBSERVATION_CAPTURED
