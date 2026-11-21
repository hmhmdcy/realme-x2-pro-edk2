#!/bin/sh
# Extract the delivered rootfs into a local ext4 tree, preserving EMPTY DIRECTORIES.
#
# tar-based extraction loses /var/empty, which made sshd report
# "Missing privilege separation directory" in an earlier session -- a false
# positive. cp -a from the mounted image keeps it.
#
# Usage: extract-image-tree.sh <image.simg> <dest>
set -eu
IMG=${1:?image}
DEST=${2:?dest}
RAW=$(mktemp -u /tmp/rootfs-XXXXXX.raw)
MOUNT=$(mktemp -d /tmp/rootfs-mnt-XXXXXX)
cleanup() { umount "$MOUNT" 2>/dev/null || true; losetup -D 2>/dev/null || true
            rm -f "$RAW"; rmdir "$MOUNT" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

simg2img "$IMG" "$RAW"
LOOP=$(losetup -f --show -r "$RAW")
mount -t f2fs -o ro,norecovery "$LOOP" "$MOUNT"

rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "$MOUNT"/. "$DEST"/

echo "extracted to $DEST"
echo "empty-dir check:"
ls -ld "$DEST/var/empty" || { echo "FATAL: /var/empty missing in source image"; exit 1; }