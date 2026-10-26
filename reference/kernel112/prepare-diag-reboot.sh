#!/bin/sh
set -eu
umask 077
[ "$#" = 3 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -v | grep -q '^#111 '
# This is the RAM diagnostic root; no block filesystem may still be mounted.
test "$(awk '$2=="/" {print $3}' /proc/mounts)" = rootfs
! grep -q '^/dev/sd' /proc/mounts
test "$(cat /sys/class/remoteproc/remoteproc0/name)" = slpi
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test ! -e /dev/fastrpc-sdsp
test "$(grep -c ': OK$' /tmp/k111-source-check.txt)" = 4
test "$(grep -c ': OK$' /tmp/k111-nv-check.txt)" = 6
test "$(sha256sum /dev/sde11 | cut -d ' ' -f 1)" = "$2"
test "$(sha256sum /dev/sde32 | cut -d ' ' -f 1)" = "$3"
sync
# Restore info-level console receipts for the one F1 transition.
echo 7 > /proc/sys/kernel/printk
echo KERNEL112_DIAGNOSTIC_ROOT_NO_BLOCK_MOUNTS_REBOOT_READY
