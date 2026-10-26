#!/bin/sh
set -eu
prefix=/tmp/k88-mpss-extract
mountpoint=/tmp/k88-modem-extract-ro
[ ! -e "$prefix.tar" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = 32bf2d8f-8dde-47dc-9b88-e87db9e95198 ]
grep -qx 'PARTNAME=modem' /sys/class/block/sde4/uevent
[ "$(cat /sys/class/block/sde4/size)" = 524288 ]
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
! grep -qE '/dev/sde4 | /tmp/k88-modem-extract-ro ' /proc/mounts
mkdir -p "$mountpoint"
cleanup() {
    if grep -q ' /tmp/k88-modem-extract-ro ' /proc/mounts; then umount "$mountpoint"; fi
}
trap cleanup EXIT HUP INT TERM
sha256sum /dev/sde4 >"$prefix-partition-before.txt"
grep -q '^88af46265a4f23c634b2a3c0a4be6815caf796f4b3bb398a6223a565c9e132f0 ' "$prefix-partition-before.txt"
mount -t vfat -o ro /dev/sde4 "$mountpoint"
grep -qE ' /tmp/k88-modem-extract-ro vfat ro,' /proc/mounts
cd "$mountpoint/image"
[ -f modem.mdt ] && [ -f modemr.jsn ] && [ -f modemuw.jsn ]
find . -maxdepth 1 -type f \( -name 'modem.mdt' -o -name 'modem.b[0-9][0-9]' -o -name 'modemr.jsn' -o -name 'modemuw.jsn' \) | sort >"$prefix-files.txt"
while read -r name; do sha256sum "$name"; done <"$prefix-files.txt" >"$prefix-firmware-hashes.txt"
tar -cf "$prefix.tar" -T "$prefix-files.txt"
cd /
cleanup
sha256sum /dev/sde4 >"$prefix-partition-after.txt"
cmp "$prefix-partition-before.txt" "$prefix-partition-after.txt"
sha256sum "$prefix"-*.txt "$prefix.tar" >"$prefix-hashes.txt"
cat "$prefix-files.txt"
cat "$prefix-partition-after.txt"
sha256sum "$prefix.tar"
