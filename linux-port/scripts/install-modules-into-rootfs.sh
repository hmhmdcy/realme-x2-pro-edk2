#!/bin/bash
# Install the matching kernel modules into a built rootfs image.
#
# The device runs with kernel=none, so /lib/modules is not part of the
# pmaports rootfs.  Without it samurai-bluetooth cannot insmod hci_uart,
# the Wi-Fi helpers cannot modprobe their drivers, and OpenRC's modules
# service has nothing to work with.
#
# Usage:
#   install-modules-into-rootfs.sh RAW_IMG MODULE_DIR

set -euo pipefail

raw="${1:?usage: $0 RAW_IMG MODULE_DIR}"
modules="${2:?usage: $0 RAW_IMG MODULE_DIR}"

release_dir=$(basename "$(ls -d "$modules"/lib/modules/*/ | head -1)")
[ -n "$release_dir" ] || { echo "no lib/modules/<release> under $modules" >&2; exit 1; }

mountpoint=$(mktemp -d)
trap 'umount "$mountpoint" 2>/dev/null || true; rmdir "$mountpoint" 2>/dev/null || true' EXIT

mount -t f2fs,loop "$raw" "$mountpoint"
root="$mountpoint"

dest="$root/lib/modules/$release_dir"
mkdir -p "$dest"

# Skip build/ and source/ links: they point at this host's kernel tree and
# would be dangling on the phone.
tar -C "$modules/lib/modules/$release_dir" --exclude=build --exclude=source -cf - . \
	| tar -C "$dest" -xf -

echo "installed $release_dir into $root/lib/modules"
echo "module files: $(find "$dest" -name '*.ko' | wc -l)"

[ -f "$dest/modules.dep" ] || echo "warning: modules.dep missing" >&2

sync
umount "$root"
trap - EXIT
rmdir "$mountpoint"
