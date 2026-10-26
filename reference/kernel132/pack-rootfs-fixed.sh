#!/bin/bash
set -euo pipefail
umask 077
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel129/ensure-rootfs-volume.py'
stage=/home/cy122/pmos-samurai-rootfs129
out=/mnt/e/edk2-samurai-out/kernel132
root="$stage/rootfs132"
export LD_LIBRARY_PATH="$stage/tools/install-root/usr/local/lib"
test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel122/device-fixture-validation.json'
image="$stage/samurai-rootfs-f2fs-k132-device-fixed.raw.img"
test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel132/rootfs-stage-validation.json'
test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel132/rootfs-content-validation.json'
test ! -e "$image"
test ! -e "$out/samurai-rootfs-f2fs-k132-device-fixed.simg"
test -z "$(findmnt -rn -o TARGET | grep -F "$root/" || true)"
rootfs_uuid=$(cat /mnt/e/edk2-samurai-out/kernel109/rootfs-uuid-private.txt)
[[ "$rootfs_uuid" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
truncate -s 119033245696 "$image"
mkfs.f2fs -f -t 0 -w 4096 -l pmos_root -U "$rootfs_uuid" "$image" > "$out/mkfs-fixed-private.log" 2>&1
echo K132_F2FS_FORMAT_COMPLETE
"$stage/tools/install-root/usr/local/sbin/sload.f2fs" -P -f "$root" "$image" > "$out/sload-fixed-private.log" 2>&1
echo K132_FULL_USERSPACE_AND_770_MODULES_LOADED
fsck.f2fs --dry-run "$image" > "$out/fsck-fixed-raw-private.log" 2>&1
echo K132_RAW_READONLY_FSCK_COMPLETE
img2simg -s "$image" "$out/samurai-rootfs-f2fs-k132-device-fixed.simg" 4096
echo K132_ANDROID_SPARSE_IMAGE_CREATED
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel132/verify-sparse-fixed.py' > "$out/sparse-fixed-check-private.log"
fsck.f2fs --dry-run "$stage/samurai-rootfs-f2fs-k132-device-fixed-restored.raw.img" > "$out/fsck-fixed-restored-private.log" 2>&1
echo K132_SPARSE_RECONSTRUCTION_AND_SECOND_FSCK_COMPLETE
