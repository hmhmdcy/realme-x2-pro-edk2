#!/bin/sh
set -eu
report=/tmp/k81-firmware-inventory.txt
exec >"$report" 2>&1
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
[ "$(cat /proc/sys/kernel/random/boot_id)" = 87753933-4992-45d2-aaf5-d9db9c11d1a3 ]
grep -qx 'PARTNAME=vendor' /sys/class/block/sda9/uevent
grep -qx 'PARTNAME=modem' /sys/class/block/sde4/uevent
[ "$(cat /sys/class/block/sda9/size)" = 3342336 ]
[ "$(cat /sys/class/block/sde4/size)" = 524288 ]
[ "$(cat /sys/class/block/sda/device/model)" = KLUDG4UHDB-B2D1\  ]
[ "$(cat /sys/class/block/sde/device/model)" = KLUDG4UHDB-B2D1\  ]
! grep -qE '/dev/sda9 |/dev/sde4 | /tmp/k81-vendor-ro | /tmp/k81-modem-ro ' /proc/mounts
mkdir -p /tmp/k81-vendor-ro /tmp/k81-modem-ro
cleanup() {
    if grep -q ' /tmp/k81-modem-ro ' /proc/mounts; then umount /tmp/k81-modem-ro; fi
    if grep -q ' /tmp/k81-vendor-ro ' /proc/mounts; then umount /tmp/k81-vendor-ro; fi
}
trap cleanup EXIT HUP INT TERM
printf 'before_partition_hashes\n'
sha256sum /dev/sda9 /dev/sde4
mount -t ext4 -o ro,noload /dev/sda9 /tmp/k81-vendor-ro
mount -t vfat -o ro /dev/sde4 /tmp/k81-modem-ro
grep ' /tmp/k81-vendor-ro ' /proc/mounts
grep ' /tmp/k81-modem-ro ' /proc/mounts
grep -qE ' /tmp/k81-vendor-ro ext4 ro,[^ ]*norecovery' /proc/mounts
grep -qE ' /tmp/k81-modem-ro vfat ro,' /proc/mounts
printf 'fixed_firmware_candidates\n'
find /tmp/k81-vendor-ro/firmware /tmp/k81-modem-ro/image -maxdepth 2 -type f \( -name 'wlanmdsp.mbn' -o -name 'bdwlan.*' \) -exec ls -ln {} \;
cleanup
printf 'after_partition_hashes\n'
sha256sum /dev/sda9 /dev/sde4
printf 'remaining_mounts\n'
cat /proc/mounts
printf 'PASS source partitions unmounted\n'
