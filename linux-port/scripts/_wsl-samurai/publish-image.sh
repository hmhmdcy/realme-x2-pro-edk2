#!/bin/bash
# Publish the freshly packed image and record its hash for the flash scripts.
set -eu
WORK=/root/repack
OUTDIR=/mnt/e/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261119-clean

ls -l "$WORK/packed.simg"
sha256sum "$WORK/packed.simg"
stat -c '%s bytes' "$WORK/packed.simg"

mv -f "$WORK/packed.simg" "$OUTDIR/samurai-stable-f2fs-partuuid.simg"
sha256sum "$OUTDIR/samurai-stable-f2fs-partuuid.simg"
stat -c '%s bytes' "$OUTDIR/samurai-stable-f2fs-partuuid.simg"
