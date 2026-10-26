#!/bin/bash
set -euo pipefail
umask 077
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py'
stage=/home/cy122/pmos-samurai-rootfs122
out=/mnt/e/edk2-samurai-out/kernel122
root="$stage/rootfs"
image="$stage/samurai-rootfs-f2fs-k121.raw.img"
test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel122/rootfs-content-validation.json'
test ! -e "$image"
test ! -e "$out/samurai-rootfs-f2fs-k121.simg"
test -z "$(findmnt -rn -o TARGET | grep -F "$root/" || true)"
rootfs_uuid=$(cat /mnt/e/edk2-samurai-out/kernel109/rootfs-uuid-private.txt)
[[ "$rootfs_uuid" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
truncate -s 119033245696 "$image"
mkfs.f2fs -f -t 0 -w 4096 -l pmos_root -U "$rootfs_uuid" "$image" > "$out/mkfs-private.log" 2>&1
echo K122_F2FS_FORMAT_COMPLETE
sload.f2fs -P -f "$root" "$image" > "$out/sload-private.log" 2>&1
echo K122_FULL_USERSPACE_AND_770_MODULES_LOADED
fsck.f2fs --dry-run "$image" > "$out/fsck-raw-private.log" 2>&1
echo K122_RAW_READONLY_FSCK_COMPLETE
img2simg -s "$image" "$out/samurai-rootfs-f2fs-k121.simg" 4096
echo K122_ANDROID_SPARSE_IMAGE_CREATED
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel122/verify-sparse.py' > "$out/sparse-check-private.log"
fsck.f2fs --dry-run "$stage/samurai-rootfs-f2fs-k121-restored.raw.img" > "$out/fsck-restored-private.log" 2>&1
echo K122_SPARSE_RECONSTRUCTION_AND_SECOND_FSCK_COMPLETE
