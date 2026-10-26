#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k131-native-fbo-comparison
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test ! -e "$dest/SHA256SUMS"
printf '%s\n' 2 > "$dest/run-exit.txt"
cat /proc/uptime > "$dest/capture-uptime.txt"
dmesg > "$dest/dmesg-capture.txt"
cat /proc/sys/kernel/tainted > "$dest/taint-final.txt"
pgrep -x phosh > "$dest/phosh-final.txt" || true
pgrep -x phoc > "$dest/phoc-final.txt" || true
cat /sys/kernel/debug/dri/1/state > "$dest/drm-final-private.txt"
for item in /sys/class/devcoredump/devcd*; do
 test -d "$item" || continue
 name=${item##*/}
 readlink -f "$item/device" > "$dest/$name-device-private.txt"
 timeout -k 2 20 cat "$item/data" > "$dest/$name-private.data"
done
sha256sum -c "$dest/package-db-before.sha256" > "$dest/package-db-final-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
iw dev wlan0 link > "$dest/wifi-link-private.txt"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
rc-service bluetooth status > "$dest/bluetooth-service.txt"
build=/var/lib/samurai/k131-native-build
cp /tmp/k131-native-sdk/build/build-receipts.json /tmp/k131-native-sdk/build/fbo-size-only.patch /tmp/k131-native-sdk/build/common-reuse-private.json "$build/"
cp /tmp/k131-native-sdk/build/canvas-control.cpp /tmp/k131-native-sdk/build/canvas-fixed.cpp /tmp/k131-native-sdk/build/xdg-shell-client-protocol.h /tmp/k131-native-sdk/build/xdg-shell-protocol.c "$build/"
cp /tmp/k131-native-sdk/build/glmark2-es2-wayland-control /tmp/k131-native-sdk/build/glmark2-es2-wayland-fixed "$build/"
(cd "$build" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$build/SHA256SUMS"
tar -C "$build" -czf /tmp/k131-native-build-private.tar.gz .
sha256sum /tmp/k131-native-build-private.tar.gz > /tmp/k131-native-build-private.tar.gz.sha256
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k131-native-fbo-comparison-private.tar.gz .
sha256sum /tmp/k131-native-fbo-comparison-private.tar.gz > /tmp/k131-native-fbo-comparison-private.tar.gz.sha256
echo FBO_COMPARISON_GPU_FAULT_AND_BUILD_EVIDENCE_PRESERVED
