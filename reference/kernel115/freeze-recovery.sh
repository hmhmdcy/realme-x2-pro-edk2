#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -v | grep -q '^#115 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-delay-fix-runtime/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -e /var/lib/samurai/k115-recovery-quiesce/remoteproc-final-state.txt
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test -z "$(pgrep -u 10000 || true)"
test -z "$(pidof wpa_supplicant || true)"
test "$(grep -c 'powered=0 muted=1' /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status | cut -d: -f2 | awk '{s+=$1} END {print s}')" = 2
test -e /var/lib/samurai/k115-runtime-stage/package-check.txt
sha256sum -c /var/lib/samurai/k115-delay-fix-runtime/partition-check.sha256 > /run/k115-preflash-partition-check.txt
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > /run/k115-preflash-nv-check.txt
sync
echo QUIESCED > /run/k115-bootloader-state
fsfreeze -f /
echo FROZEN > /run/k115-bootloader-state
echo KERNEL115_F2FS_FROZEN_FOR_BOOTLOADER
