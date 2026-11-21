#!/bin/bash
# Add the marker the initramfs uses to accept a rootfs before switch_root.
#
# /usr/sbin/samurai-rootfs in the embedded initramfs refuses to switch root
# unless /etc/samurai-rootfs-release contains
#   ROOTFS_ID=samurai-f2fs-rootfs01
# and /sbin/init is executable.  Rootfs builds made by finalize-rootfs.py
# get the file; the Plasma path (finalize-plasma.py) did not, so every boot
# fell back to the diagnostic initramfs and never reached the distribution.
#
# Usage:
#   mark-rootfs-release.sh RAW_IMG [IN_SIMG OUT_SIMG]

set -euo pipefail

raw="${1:?usage: $0 RAW_IMG [IN_SIMG OUT_SIMG]}"

mountpoint=$(mktemp -d)
trap 'umount "$mountpoint" 2>/dev/null || true; rmdir "$mountpoint" 2>/dev/null || true' EXIT

mount -t f2fs,loop "$raw" "$mountpoint"
root="$mountpoint"

# This tree is usr-merged: /sbin -> usr/bin and init -> /bin/busybox.
# Plain test -e/-x does not resolve that on every host, so resolve first.
init=$(readlink "$root/sbin/init" 2>/dev/null || true)
case "$init" in
/*) init_path="$root$init" ;;
"") init_path="" ;;
*) init_path="$root/sbin/$init" ;;
esac
if [ -z "$init_path" ] || [ ! -f "$init_path" ]; then
	echo "missing /sbin/init target in rootfs" >&2
	exit 1
fi
[ -f "$root/etc/inittab" ] || { echo "missing /etc/inittab in rootfs" >&2; exit 1; }

release="$root/etc/samurai-rootfs-release"
printf 'ROOTFS_ID=samurai-f2fs-rootfs01\nBUILD_PROFILE=github-pmaports-samurai-userspace\n' > "$release"
chmod 644 "$release"

echo "wrote $release"
cat "$release"

sync
umount "$root"
trap - EXIT
rmdir "$mountpoint"

if [ $# -ge 3 ]; then
	img2simg "$2" "$3"
	echo "wrote $3"
fi
