#!/bin/bash
set -euo pipefail
umask 077
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel132'
bash "$ref/pack-rootfs-fixed.sh"
python3 "$ref/export-rootfs-image-fixed.py"
python3 "$ref/verify-image-export-fixed.py"
python3 "$ref/finalize-rootfs-image.py"
echo K132_FULL_ROOTFS_ENCODE_RECONSTRUCT_DUAL_FSCK_AND_REVERSE_METADATA_PASS
