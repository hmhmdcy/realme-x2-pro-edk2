#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k115-camera-config-list
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-final-health/boot-id-private.txt)"
grep -qx PARTNAME=vendor /sys/class/block/sda9/uevent
test "$(cat /sys/class/block/sda9/size)" = 3342336
mkdir -m700 "$dest"
mp=/run/k115-camera-config-list-readonly
test ! -e "$mp";mkdir -m700 "$mp"
mount -t ext4 -o ro,noload,nosuid,nodev,noexec /dev/sda9 "$mp"
trap 'umount "$mp"' EXIT
find "$mp/etc/camera" -maxdepth 4 -type f -exec stat -c '%s %n' '{}' ';' > "$dest/camera-files-private.txt"
find "$mp" -maxdepth 6 -type f -name '*.bin' -exec stat -c '%s %n' '{}' ';' > "$dest/bin-files-private.txt"
grep -F "$mp" /proc/mounts > "$dest/mount-options.txt"
umount "$mp";trap - EXIT
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k115-camera-config-list-private.tar.gz .
echo CAMERA_VENDOR_METADATA_LIST_SAVED_READONLY
