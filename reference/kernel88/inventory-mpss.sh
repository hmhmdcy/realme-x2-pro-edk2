#!/bin/sh
# Fixed same-handset firmware partition; no NV/storage service or DSP start.
set -eu
prefix=/tmp/k88-mpss-inventory
mountpoint=/tmp/k88-modem-ro
[ ! -e "$prefix.txt" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = 32bf2d8f-8dde-47dc-9b88-e87db9e95198 ]
grep -qx 'PARTNAME=modem' /sys/class/block/sde4/uevent
[ "$(cat /sys/class/block/sde4/size)" = 524288 ]
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
! grep -qE '/dev/sde4 | /tmp/k88-modem-ro ' /proc/mounts
mkdir -p "$mountpoint"
cleanup() {
    if grep -q ' /tmp/k88-modem-ro ' /proc/mounts; then umount "$mountpoint"; fi
}
trap cleanup EXIT HUP INT TERM
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    sha256sum /dev/sde4
    mount -t vfat -o ro /dev/sde4 "$mountpoint"
    grep -qE ' /tmp/k88-modem-ro vfat ro,' /proc/mounts
    grep ' /tmp/k88-modem-ro ' /proc/mounts
    find "$mountpoint/image" -maxdepth 2 -type f \( -name 'modem.*' -o -name 'qdsp6*' -o -name 'mba.*' -o -name '*.jsn' \) -exec ls -ln {} \;
    cleanup
    sha256sum /dev/sde4
    printf 'PASS firmware partition unmounted; no remoteproc/NV operation\n'
} >"$prefix.txt"
sha256sum "$prefix.txt" >"$prefix-hashes.txt"
cat "$prefix.txt"
