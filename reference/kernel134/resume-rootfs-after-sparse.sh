#!/bin/bash
set -euo pipefail
umask 077
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel134'
out='/mnt/e/edk2-samurai-out/kernel134'
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel129/ensure-rootfs-volume.py'
test -f "$out/sparse-fixed-validation.json"
test ! -e "$out/fsck-fixed-restored-private.log"
fsck.f2fs --dry-run /home/cy122/pmos-samurai-rootfs129/samurai-rootfs-f2fs-k134-device-fixed-restored.raw.img > "$out/fsck-fixed-restored-private.log" 2>&1
echo K134_EXISTING_RECONSTRUCTION_SECOND_READONLY_FSCK_COMPLETE
python3 "$ref/export-rootfs-image-fixed.py"
python3 "$ref/verify-image-export-fixed.py"
python3 "$ref/finalize-rootfs-image.py"
echo K134_FULL_ROOTFS_RESUMED_RECONSTRUCT_DUAL_FSCK_AND_REVERSE_METADATA_PASS
