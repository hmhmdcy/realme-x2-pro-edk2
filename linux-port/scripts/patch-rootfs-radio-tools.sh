#!/bin/bash
# Add samurai-radio-tools to an already-built rootfs image.
#
# The package was built but never pulled into the image, while the
# samurai-radio boot service calls its binaries unconditionally.  Installing
# it with apk is not possible offline: the bundled @samurai index is signed by
# a key that is not in the image.  So this unpacks the APK from the image's own
# repository, records it in the apk database, and regenerates the sparse image.
#
# Usage:
#   patch-rootfs-radio-tools.sh RAW_IMG OUT_SIMG

set -euo pipefail

raw="${1:?usage: $0 RAW_IMG OUT_SIMG}"
out="${2:?usage: $0 RAW_IMG OUT_SIMG}"

mountpoint=$(mktemp -d)
trap 'umount "$mountpoint" 2>/dev/null || true; rmdir "$mountpoint" 2>/dev/null || true' EXIT

mount -t f2fs,loop "$raw" "$mountpoint"
root="$mountpoint"

apk="$root/var/lib/samurai/apk/aarch64/samurai-radio-tools-1-r0.apk"
index="$root/var/lib/samurai/apk/aarch64/APKINDEX.tar.gz"

[ -f "$apk" ] || { echo "missing $apk" >&2; exit 1; }
[ -f "$index" ] || { echo "missing $index" >&2; exit 1; }

if grep -q "^P:samurai-radio-tools$" "$root/lib/apk/db/installed"; then
	echo "samurai-radio-tools already installed; nothing to do"
	exit 0
fi

staging=$(mktemp -d "$root/tmp/patchXXXXXX")
tar -xzf "$apk" -C "$staging"

install -Dm755 "$staging"/usr/sbin/samurai-tqftpserv "$root"/usr/sbin/samurai-tqftpserv
install -Dm755 "$staging"/usr/sbin/samurai-rmtfs-cow "$root"/usr/sbin/samurai-rmtfs-cow
install -Dm755 "$staging"/usr/sbin/samurai-dms-mac-read "$root"/usr/sbin/samurai-dms-mac-read
install -Dm755 "$staging"/usr/sbin/samurai-bt-address "$root"/usr/sbin/samurai-bt-address

# Register the package so the DB agrees with the files on disk.
record=$(awk 'BEGIN{RS="";FS="\n"} /^P:samurai-radio-tools$/' \
	"$root/var/lib/samurai/apk/aarch64/APKINDEX")
if [ -z "$record" ]; then
	echo "samurai-radio-tools not in bundled index" >&2
	exit 1
fi
printf '%s\n\n' "$record" >> "$root/lib/apk/db/installed"

rm -rf "$staging"

umount "$root"
trap - EXIT
rmdir "$mountpoint"

img2simg "$raw" "$out"
echo "wrote $out"
