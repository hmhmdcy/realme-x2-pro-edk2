#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k115-vendor-camera-bins-v3
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-final-health/boot-id-private.txt)"
uname -v | grep -q '^#115 '
test "$(cat /proc/sys/kernel/tainted)" = 0
grep -qx PARTNAME=vendor /sys/class/block/sda9/uevent
test "$(cat /sys/class/block/sda9/size)" = 3342336
mkdir -m700 "$dest"
sha256sum /dev/sda9 > "$dest/vendor-before.sha256"
mp=/run/k115-camera-bins-vendor-readonly-v3
test ! -e "$mp"
mkdir -m700 "$mp"
mount -t ext4 -o ro,noload,nosuid,nodev,noexec /dev/sda9 "$mp"
trap 'umount "$mp"' EXIT
grep -F "$mp" /proc/mounts > "$dest/mount-options.txt"
test -d "$mp/lib64/camera"
find "$mp/lib64/camera" -maxdepth 4 -type f -name 'com.qti.sensormodule.*.bin' > "$dest/module-paths-private.txt"
test "$(wc -l < "$dest/module-paths-private.txt")" -le 100
test "$(wc -l < "$dest/module-paths-private.txt")" -gt 0
total=0
find "$mp/lib64/camera" -maxdepth 4 -type f -exec stat -c "%s %n" '{}' ';' > "$dest/camera-file-list-private.txt"
mkdir -m700 "$dest/modules"
while IFS= read -r file; do
    test -f "$file"; test ! -L "$file"
    size=$(stat -c %s "$file")
    total=$((total+size))
    test "$total" -le 100663296
    relative=${file#"$mp/lib64/camera/"}
    mkdir -p "$dest/modules/$(dirname "$relative")"
    test ! -e "$dest/modules/$relative"
    cp -p "$file" "$dest/modules/$relative"
done < "$dest/module-paths-private.txt"
umount "$mp"
trap - EXIT
sha256sum -c "$dest/vendor-before.sha256" > "$dest/vendor-after-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k115-vendor-camera-bins-v3-private.tar.gz .
sha256sum /tmp/k115-vendor-camera-bins-v3-private.tar.gz
echo SAME_HANDSET_CAMERA_SENSOR_BINARIES_EXTRACTED_READONLY
