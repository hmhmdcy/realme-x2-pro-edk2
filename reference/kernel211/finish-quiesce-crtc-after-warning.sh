#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k211-before-reboot
dest=/var/lib/samurai/k211-quiesce
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 512
test ! -e "$dest/quiesce-validation.json"
test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 0
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
test ! -e "$dest/explicit-crtc-first-failure-private.txt"
cp "$dest/explicit-crtc-disable.txt" "$dest/explicit-crtc-first-failure-private.txt"
python3 /tmp/k211-disable-crtc-after-warning.py > "$dest/explicit-crtc-disable.txt" 2>&1
for sample in 1 2 3; do
 sleep 1
 cat /sys/kernel/debug/dri/1/state > "$dest/drm-detached-sample-$sample.txt"
 test "$(grep -c 'active=1' "$dest/drm-detached-sample-$sample.txt" || true)" = 0
done
python3 /tmp/k211-check-quiesce-recovery.py --record
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg-after.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k211-quiesce-private.tar .
echo K202_CURRENT183_QUIESCE_COMPLETE
