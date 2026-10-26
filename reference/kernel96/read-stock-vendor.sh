#!/bin/sh
# Read selected same-handset address-provisioning evidence. No journal replay.
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = 02ba5ffd-9768-43e4-9c6e-511bb1aeccd1 ]
grep -qx PARTNAME=vendor /sys/class/block/sda9/uevent
[ "$(cat /sys/class/block/sda9/size)" = 3342336 ]
[ "$(cat /sys/class/block/sda/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
dir=/tmp/k96-stock-vendor
test ! -e "$dir"
mkdir -m 700 "$dir" "$dir/mount" "$dir/files"
sha256sum /dev/sda9 > "$dir/vendor-before.sha"
mount -t ext4 -o ro,noload,nosuid,nodev,noexec /dev/sda9 "$dir/mount"
trap 'umount "$dir/mount"' EXIT
grep -F "$dir/mount" /proc/mounts > "$dir/mount-options.txt"
find "$dir/mount/etc" "$dir/mount/lib64" "$dir/mount/bin" -maxdepth 3 -type f | grep -Ei 'bluetooth|bt-vendor|btnv|wlan|cnss|wifi' > "$dir/relevant-paths.txt"
for name in lib64/libbt-vendor.so lib64/libbtnv.so lib64/libbt-qcom.so lib64/libqmi.so lib64/libqmi_common_so.so bin/cnss-daemon; do
    [ -f "$dir/mount/$name" ] || continue
    mkdir -p "$dir/files/${name%/*}"
    cp "$dir/mount/$name" "$dir/files/$name"
done
for name in etc/bluetooth/bt_vendor.conf etc/bluetooth/bt_stack.conf etc/init/android.hardware.bluetooth@1.0-service-qti.rc etc/init/cnss-daemon.rc; do
    [ -f "$dir/mount/$name" ] || continue
    mkdir -p "$dir/files/${name%/*}"
    cp "$dir/mount/$name" "$dir/files/$name"
done
umount "$dir/mount"
trap - EXIT
sha256sum -c "$dir/vendor-before.sha" > "$dir/vendor-after-check.txt"
(cd "$dir" && find files -type f -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k96-stock-vendor.tar k96-stock-vendor
sha256sum /tmp/k96-stock-vendor.tar
echo VENDOR_READ_ONLY_COMPLETE
