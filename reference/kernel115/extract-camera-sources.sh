#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k115-vendor-camera-source
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-final-health/boot-id-private.txt)"
uname -v | grep -q '^#115 '
test "$(cat /proc/sys/kernel/tainted)" = 0
grep -qx PARTNAME=vendor /sys/class/block/sda9/uevent
test "$(cat /sys/class/block/sda9/size)" = 3342336
mkdir -m700 "$dest"
sha256sum /dev/sda9 > "$dest/vendor-before.sha256"
mp=/run/k115-camera-vendor-readonly
test ! -e "$mp"
mkdir -m700 "$mp"
mount -t ext4 -o ro,noload,nosuid,nodev,noexec /dev/sda9 "$mp"
trap 'umount "$mp"' EXIT
grep -F "$mp" /proc/mounts > "$dest/mount-options.txt"
test -d "$mp/lib64/camera"
find "$mp/lib64/camera" -maxdepth 1 -type f -name 'com.qti.sensor.*.so' > "$dest/module-paths-private.txt"
test "$(wc -l < "$dest/module-paths-private.txt")" -le 100
test "$(wc -l < "$dest/module-paths-private.txt")" -gt 0
total=0
mkdir -m700 "$dest/modules"
while IFS= read -r file; do
    test -f "$file"; test ! -L "$file"
    size=$(stat -c %s "$file")
    total=$((total+size))
    test "$total" -le 100663296
    cp -p "$file" "$dest/modules/"
done < "$dest/module-paths-private.txt"
umount "$mp"
trap - EXIT
sha256sum -c "$dest/vendor-before.sha256" > "$dest/vendor-after-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k115-vendor-camera-source-private.tar.gz .
sha256sum /tmp/k115-vendor-camera-source-private.tar.gz
echo SAME_HANDSET_CAMERA_SENSOR_MODULES_EXTRACTED_READONLY
