#!/bin/bash
set -euo pipefail
umask 077
stage=/home/cy122/pmos-samurai-rootfs114
out=/mnt/e/edk2-samurai-out/kernel114
root="$stage/rootfs"
image="$stage/samurai-rootfs-f2fs-final.raw.img"
test -f "$out/userspace-complete.json"
test ! -e "$image"
test -z "$(findmnt -rn -o TARGET | grep -F "$root/" || true)"
rootfs_uuid=$(cat /mnt/e/edk2-samurai-out/kernel109/rootfs-uuid-private.txt)
[[ "$rootfs_uuid" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
printf 'rootfs114-current-hardware-kernel113\n' > "$root/etc/samurai-rootfs-stage"
truncate -s 119033245696 "$image"
mkfs.f2fs -f -t 0 -w 4096 -l pmos_root -U "$rootfs_uuid" "$image" > "$out/mkfs-private.log" 2>&1
sload.f2fs -P -f "$root" "$image" > "$out/sload-private.log" 2>&1
fsck.f2fs --dry-run "$image" > "$out/fsck-raw-private.log" 2>&1
img2simg -s "$image" "$out/samurai-rootfs-f2fs.simg" 4096
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel114/verify-sparse.py' > "$out/sparse-check.log"
fsck.f2fs --dry-run "$stage/samurai-rootfs-f2fs-restored.raw.img" > "$out/fsck-restored-private.log" 2>&1
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel114/finalize-rootfs.py'
echo ROOTFS114_PACK_SPARSE_COMPARE_AND_BOTH_FSCK_PASS
