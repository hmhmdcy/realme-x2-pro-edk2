#!/bin/bash
# Recreate the kernel work tree that the running Image was built from:
#   linux-7.3-rc6 tarball  +  linux-port/patches/v7.3.1 series
# The previous work tree (~/x2pro-linux/linux) was removed during disk
# cleanup, so this is the reproducible path back to a buildable tree.
#
# Usage: prepare-kernel-tree.sh [--check] [--force]
#   --check   copy+patch into a scratch dir under /root and report whether
#             every patch applies, without leaving a build tree behind.
#   --force   replace an existing work tree instead of reusing it.
#
# The tarball defaults to the exact upstream release the running kernel
# reports, v7.3.1, not the -rc6 snapshot used for the first bring-up.  Mixing
# them changes kernel.release and every module then fails to load with a
# vermagic mismatch, so the version is not a detail here.
set -eu

REPO="/mnt/e/RealmeX2Pro edk2"
SRC_TAR="${SRC_TAR:-/mnt/e/Realme X2 Pro移植主线Linux/sources/linux-7.3.1.tar.gz}"
PATCHDIR="$REPO/linux-port/patches/v7.3.1"

mode=build
force=0
for arg in "$@"; do
	case "$arg" in
	--check) mode=check ;;
	--force) force=1 ;;
	esac
done

if [ "$mode" = check ]; then
	LK=/root/kern-check
	rm -rf "$LK"
else
	LK=/home/cy122/x2pro-linux/linux
	EXPECT=/home/cy122/x2pro-linux
	mkdir -p "$EXPECT"
	if [ -d "$LK" ] && [ "$force" -eq 0 ]; then
		echo "work tree already present: $LK (pass --force to rebuild)" >&2
		exit 1
	fi
	rm -rf "$LK"
fi

echo "=== 1. unpack $SRC_TAR into $LK ==="
mkdir -p "$LK"
tar -xzf "$SRC_TAR" -C "$LK" --strip-components=1
du -sh "$LK"
ls "$LK/Makefile" >/dev/null || { echo 'unpack failed'; exit 1; }

echo '=== 2. apply the board patch series in order ==='
# 0010 supersedes 0003/0005/0009 for the panel; the README is explicit
# that stacking them corrupts the panel driver, so skip the superseded trio.
# 0014 only removes a keep-connect opt-in that 0001's final form never adds,
# so it is already satisfied and its hunk does not apply.
skip_names="0003-arm64-panel-sofef03f-reapply-backlight.patch
0005-arm64-panel-sofef03f-post-on-after-first-frame.patch
0009-arm64-panel-sofef03f-serialize-brightness.patch
0014-arm64-dts-samurai-disable-usb-keep-connect.patch"

is_skipped() {
	printf '%s\n' "$skip_names" | grep -qxF "$1"
}

fail=0
for p in "$PATCHDIR"/*.patch; do
	[ -f "$p" ] || continue
	name=${p##*/}
	if is_skipped "$name"; then
		echo "  skip (superseded by 0010): $name"
		continue
	fi
	if (cd "$LK" && patch -p1 --forward --batch -s < "$p") 2>/dev/null; then
		echo "  ok   $name"
	else
		echo "  FAIL $name"
		fail=$((fail + 1))
	fi
done

echo "=== patch failures: $fail ==="
if [ "$mode" = check ]; then
	du -sh "$LK"
	exit "$([ "$fail" -eq 0 ] && echo 0 || echo 1)"
fi
[ "$fail" -eq 0 ] || { echo 'refusing to keep a partially patched tree'; exit 1; }
echo "kernel tree ready: $LK"
