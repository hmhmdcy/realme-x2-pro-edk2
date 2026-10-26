#!/bin/sh
set -eu
umask 077
dir=/var/lib/samurai/k167-quiesce
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dir/boot-id-private.txt")"
uname -v | grep -q '^#166 '
test "$(cat /proc/sys/kernel/tainted)" = 640
test -z "$(pgrep -u 10000 || true)"
test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 0
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
for sample in 1 2 3; do
 cat /sys/kernel/debug/dri/1/state > "$dir/drm-detached-sample-$sample.txt"
 sleep 1
done
python3 /tmp/k167-check-quiesce.py --record
dmesg > "$dir/dmesg-after.txt"
sync
tar -C "$dir" -cf /tmp/k167-quiesce-private.tar .
echo K167_FAILED166_STATE_RECORDED_FOR_ROLLBACK
