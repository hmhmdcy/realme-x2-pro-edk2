#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -v | grep -q '^#115 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k119-preflash/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -e /var/lib/samurai/k119-flash-quiesce-2/remoteproc-final-state.txt
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test -z "$(pgrep -u 10000 || true)"
test -z "$(pidof wpa_supplicant || true)"
test "$(grep -c 'powered=0 muted=1' /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status | cut -d: -f2 | awk '{s+=$1} END {print s}')" = 2
test -e /var/lib/samurai/k115-runtime-stage/package-check.txt
test "$(cat /var/lib/samurai/k119-flash-quiesce-2/boot-id-private.txt)" = "$1"
test -z "$(pgrep -x phosh || true)"
test -z "$(pgrep -x phoc || true)"
test -z "$(pidof ModemManager || true)"
test ! -e /proc/asound/card0
test "$(grep -c 'active=1' /sys/kernel/debug/dri/0/state || true)" = 0
sha256sum -c /var/lib/samurai/k119-preflash/partition-check.sha256 > /run/k119-preflash-partition-check.txt
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > /run/k119-preflash-nv-check.txt
sync
echo QUIESCED > /run/k119-bootloader-state
fsfreeze -f /
echo FROZEN > /run/k119-bootloader-state
echo KERNEL119_F2FS_FROZEN_FOR_BOOTLOADER
