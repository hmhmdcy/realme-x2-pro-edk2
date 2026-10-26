#!/bin/sh
set -eu
exec >/tmp/k81-wifi-extraction.txt 2>&1
[ "$(cat /proc/sys/kernel/random/boot_id)" = 87753933-4992-45d2-aaf5-d9db9c11d1a3 ]
grep -qx 'PARTNAME=modem' /sys/class/block/sde4/uevent
[ "$(cat /sys/class/block/sde4/size)" = 524288 ]
[ "$(cat /sys/class/block/sde/device/model)" = KLUDG4UHDB-B2D1\  ]
! grep -qE '/dev/sde4 | /tmp/k81-modem-ro ' /proc/mounts
[ ! -e /tmp/k81-wifi-firmware-stock.tar ]
mkdir -p /tmp/k81-modem-ro
cleanup() { if grep -q ' /tmp/k81-modem-ro ' /proc/mounts; then umount /tmp/k81-modem-ro; fi; }
trap cleanup EXIT HUP INT TERM
expected=88af46265a4f23c634b2a3c0a4be6815caf796f4b3bb398a6223a565c9e132f0
hash=$(sha256sum /dev/sde4)
[ "${hash%% *}" = "$expected" ]
printf 'before_partition_sha256=%s\n' "$expected"
mount -t vfat -o ro /dev/sde4 /tmp/k81-modem-ro
grep ' /tmp/k81-modem-ro ' /proc/mounts
grep -qE ' /tmp/k81-modem-ro vfat ro,' /proc/mounts
cd /tmp/k81-modem-ro/image
[ -f wlanmdsp.mbn ]; [ ! -L wlanmdsp.mbn ]; [ "$(stat -c %s wlanmdsp.mbn)" = 4069824 ]
for f in bdwlan.*; do [ -f "$f" ]; [ ! -L "$f" ]; [ "$(stat -c %s "$f")" = 26328 ]; done
sha256sum wlanmdsp.mbn bdwlan.*
tar -cf /tmp/k81-wifi-firmware-stock.tar wlanmdsp.mbn bdwlan.*
cd /tmp
cleanup
hash=$(sha256sum /dev/sde4)
[ "${hash%% *}" = "$expected" ]
printf 'after_partition_sha256=%s\n' "$expected"
sha256sum /tmp/k81-wifi-firmware-stock.tar
! grep -q ' /tmp/k81-modem-ro ' /proc/mounts
printf 'PASS fixed Wi-Fi firmware files archived privately; source partition hash unchanged and unmounted\n'
