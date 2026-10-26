#!/bin/sh
# Read same-handset address evidence without journal replay or OEM execution.
# The expected current boot ID is supplied privately as the first argument.
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
grep -qx PARTNAME=persist /sys/class/block/sda2/uevent
grep -qx PARTNAME=vendor /sys/class/block/sda9/uevent
[ "$(cat /sys/class/block/sda2/size)" = 65536 ]
[ "$(cat /sys/class/block/sda9/size)" = 3342336 ]
[ "$(cat /sys/class/block/sda/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
dir=/tmp/k96-address-evidence
test ! -e "$dir"
mkdir -m 700 "$dir" "$dir/persist" "$dir/vendor" "$dir/files"
sha256sum /dev/sda2 /dev/sda9 > "$dir/partitions-before.sha"
mount -t ext4 -o ro,noload,nosuid,nodev,noexec /dev/sda2 "$dir/persist"
trap 'umount "$dir/persist"; umount "$dir/vendor" 2>/dev/null || true' EXIT
grep -F "$dir/persist" /proc/mounts > "$dir/persist-mount-options.txt"
find "$dir/persist" -type f | grep -Ei 'bluetooth|bt_nv|wlan|wifi|mac' > "$dir/persist-relevant-paths.txt" || true
if [ -f "$dir/persist/bluetooth/.bt_nv.bin" ]; then
    mkdir -p "$dir/files/persist/bluetooth"
    cp "$dir/persist/bluetooth/.bt_nv.bin" "$dir/files/persist/bluetooth/.bt_nv.bin"
    echo HIDDEN_BT_NV_PRESENT
else
    echo HIDDEN_BT_NV_ABSENT
fi
umount "$dir/persist"
trap - EXIT
mount -t ext4 -o ro,noload,nosuid,nodev,noexec /dev/sda9 "$dir/vendor"
trap 'umount "$dir/vendor"' EXIT
grep -F "$dir/vendor" /proc/mounts > "$dir/vendor-mount-options.txt"
for name in lib64/hw/android.hardware.bluetooth@1.0-impl-qti.so bin/hw/android.hardware.bluetooth@1.0-service-qti; do
    test -f "$dir/vendor/$name"
    mkdir -p "$dir/files/vendor/${name%/*}"
    cp "$dir/vendor/$name" "$dir/files/vendor/$name"
done
umount "$dir/vendor"
trap - EXIT
sha256sum -c "$dir/partitions-before.sha" > "$dir/partitions-after-check.txt"
(cd "$dir" && find files -type f -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k96-address-evidence.tar k96-address-evidence
sha256sum /tmp/k96-address-evidence.tar
echo ADDRESS_EVIDENCE_READ_ONLY_COMPLETE
