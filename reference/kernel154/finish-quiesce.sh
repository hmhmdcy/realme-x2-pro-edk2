#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k154-preflash
dest=/var/lib/samurai/k154-quiesce
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
uname -v | grep -q '^#153 '
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)" = /dev/dri/card1
test -z "$(pgrep -u 10000 || true)"
test "$(wc -l < /sys/kernel/debug/dri/1/clients)" = 1
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
test ! -e "$dest/fbcon-detach-started"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-late-unblank-private.txt"
test "$(cat /sys/class/vtconsole/vtcon1/name)" = '(M) frame buffer device'
test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 1
printf '%s\n' 'First quiesce audit rejected console reactivation; no F1 was sent.' > "$dest/first-audit-failure.txt"
echo started > "$dest/fbcon-detach-started"
echo 0 > /sys/class/vtconsole/vtcon1/bind
test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 0
timeout -s TERM -k 2 20 sh -c 'echo 4 > /sys/class/graphics/fb0/blank' > "$dest/fbcon-detached-blank.txt" 2>&1
for sample in 1 2 3 4 5; do
 sleep 1
 cat /sys/kernel/debug/dri/1/state > "$dest/drm-detached-sample-$sample.txt"
 test "$(grep -c 'active=1' "$dest/drm-detached-sample-$sample.txt" || true)" = 0
done
python3 /tmp/k154-check-quiesce.py --record
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg-after.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k154-quiesce-private.tar .
echo K154_CURRENT153_FBCON_DETACHED_QUIESCE_COMPLETE
