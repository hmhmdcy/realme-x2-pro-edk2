#!/bin/sh
set -eu
umask 077
build=/tmp/k131-native-sdk/build
dest=/var/lib/samurai/k131-native-fbo-comparison
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k130-warmboot-r2/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /var/lib/samurai/k131-native-build/build-r3-exit.txt)" = 0
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cp /var/lib/samurai/k131-native-build/package-db-before.sha256 "$dest/"
cp "$build/build-receipts.json" "$build/fbo-size-only.patch" "$dest/"
for variant in control fixed; do
 binary="$build/glmark2-es2-wayland-$variant"
 test -f "$binary"
 test -x "$binary"
 sha256sum "$binary" >> "$dest/binary-hashes.txt"
 env LD_LIBRARY_PATH=/tmp/k131-native-sdk/sdk/usr/lib /tmp/k131-native-sdk/sdk/usr/bin/readelf -d "$binary" > "$dest/$variant-dynamic.txt"
 if grep -E 'RPATH|RUNPATH' "$dest/$variant-dynamic.txt"; then echo UNEXPECTED_RUNTIME_LIBRARY_PATH;exit 2;fi
done
for variant in control fixed; do
 scene="$dest/$variant"
 mkdir -m700 "$scene"
 test "$(cat /proc/sys/kernel/tainted)" = 0
 dmesg > "$scene/dmesg-before.txt"
 if grep -Ei 'gpu.*fault|FAULT.*gpu|CCU.*TRANSLATION|CP.*FAULT' "$scene/dmesg-before.txt" > "$scene/existing-gpu-faults.txt"; then echo GPU_FAULT_PRESENT_DO_NOT_TEST;exit 2;fi
 pgrep -x phosh > "$scene/phosh-before.txt"
 pgrep -x phoc > "$scene/phoc-before.txt"
 cat /sys/kernel/debug/dri/1/state > "$scene/drm-before-private.txt"
 cat /proc/uptime > "$scene/uptime-before.txt"
 set +e
 timeout -s TERM -k 2 20 su -s /bin/sh cy122 -c "ulimit -t 10; ulimit -v 786432; exec env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 $build/glmark2-es2-wayland-$variant --off-screen --validate --debug --benchmark build:use-vbo=true --data-path /tmp/k131-glmark2/usr/share/glmark2" > "$scene/validation-private.txt" 2>&1
 result=$?
 set -e
 echo "$result" > "$scene/exit.txt"
 cat /proc/uptime > "$scene/uptime-exit.txt"
 dmesg > "$scene/dmesg-immediate.txt"
 for sample in 0 1 2 3 4 5 6; do
  printf '%s ' "$sample" >> "$scene/samples.txt"
  cat /proc/uptime >> "$scene/samples.txt"
  cat /proc/sys/kernel/tainted >> "$scene/taints.txt"
  if test "$sample" != 6; then sleep 5;fi
 done
 dmesg > "$scene/dmesg-delayed.txt"
 pgrep -x phosh > "$scene/phosh-after.txt" || true
 pgrep -x phoc > "$scene/phoc-after.txt" || true
 cat /sys/kernel/debug/dri/1/state > "$scene/drm-after-private.txt"
 if pgrep -f '^/tmp/k131-native-sdk/build/glmark2-es2-wayland-' > "$scene/remaining-processes.txt"; then echo TOOL_PROCESS_REMAINS;exit 2;fi
 if grep -Ei 'gpu.*fault|FAULT.*gpu|CCU.*TRANSLATION|CP.*FAULT' "$scene/dmesg-delayed.txt" > "$scene/final-gpu-faults.txt"; then echo GPU_FAULT_CAPTURED_STOP_COMPARISON;exit 2;fi
done
sha256sum -c "$dest/package-db-before.sha256" > "$dest/package-db-final-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
iw dev wlan0 link > "$dest/wifi-link-private.txt"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
rc-service bluetooth status > "$dest/bluetooth-service.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k131-native-fbo-comparison-private.tar.gz .
sha256sum /tmp/k131-native-fbo-comparison-private.tar.gz > /tmp/k131-native-fbo-comparison-private.tar.gz.sha256
echo NATIVE_CONTROL_AND_FIXED_SINGLE_SCENE_CAPTURED
