#!/bin/sh
set -eu
prefix=/tmp/k89-preflash
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar.gz" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = 32bf2d8f-8dde-47dc-9b88-e87db9e95198 ]
uname -a | grep -q '#86 SMP PREEMPT'
grep -qx 'PARTNAME=boot' /sys/class/block/sde11/uevent
grep -qx 'PARTNAME=logdump' /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
{
 cat /proc/sys/kernel/random/boot_id
 uname -a
 cat /proc/uptime
 cat /proc/sys/kernel/tainted
 cat /sys/kernel/debug/dri/1/encoder-0/status
 cat "$trace/tracing_on"
 cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
 ls /sys/class/net
} >"$prefix-state.txt"
cat "$trace/snapshot" >"$prefix-snapshot.txt"
cat "$trace/trace" >"$prefix-trace.txt"
cat /sys/kernel/debug/dri/1/state >"$prefix-drm-state.txt"
cat /sys/kernel/debug/dri/1/kms >"$prefix-kms.txt"
dmesg >"$prefix-dmesg.txt"
# Complete backups, including boot partition padding, before any deployment.
dd if=/dev/sde11 of=/tmp/k89-boot-partition-before.img bs=1048576
dd if=/dev/sde32 of=/tmp/k89-logdump-before.img bs=1048576
{
 head -c 6682624 /dev/sde11 | sha256sum
 sha256sum /dev/sde11 /dev/sde32 /tmp/k89-boot-partition-before.img /tmp/k89-logdump-before.img
} >"$prefix-partition-hashes.txt"
grep -q '^08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405 ' "$prefix-partition-hashes.txt"
grep -q '^cf11644e32a138ff1319fe9e44529f1ef7b2a1907c1f8876c597f970a526d286 ' "$prefix-partition-hashes.txt"
sha256sum "$prefix"-*.txt >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix"-*.txt
gzip -c "$prefix.tar" >"$prefix.tar.gz"
sha256sum "$prefix.tar.gz"
cat "$prefix-state.txt"
cat "$prefix-partition-hashes.txt"
