#!/bin/bash
# Build samurai-desktop with the board-wide "never auto-suspend"
# default, using the same signer the running image already trusts.
#
# The running image is apk-tools 3.0.9 (APKv3, adb/sha256 manifests), so the
# package must be built with --compat 3.0.0.  Older tooling produced the
# gzip/v2 format, which this apk cannot install.
#
# The version comes from APKBUILD, so the packaged control section and the
# file digests are produced together from the same source bytes.  Earlier
# builds hard-coded 4-r17 and produced an APK whose recorded digest did not
# match the installed file (caught by check-rootfs.py), which would have let
# `apk upgrade` replace the correct config with the stale one.
set -eu

REPO_DIR=/mnt/e/RealmeX2Pro\ edk2
PKG_SRC="$REPO_DIR/linux-port/packages/samurai-desktop"
WORK=/root/desktop-r17
OUT=/root/desktop-r17-out
SIGN_KEY=/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa
KEYS=/root/installed_keys
APK=/root/apkstatic/sbin/apk.static
VERSION=$(sed -n 's/^pkgver=//p' "$PKG_SRC/APKBUILD")-r$(sed -n 's/^pkgrel=//p' "$PKG_SRC/APKBUILD")
PKG="$OUT/samurai-desktop-$VERSION.apk"

rm -rf "$WORK" "$OUT"
mkdir -p "$WORK/root" "$OUT"

install -Dm755 "$PKG_SRC/samurai-tinydm-stop" \
	"$WORK/root/usr/libexec/samurai-tinydm-stop"
install -Dm644 "$PKG_SRC/powerdevilrc" \
	"$WORK/root/etc/xdg/powerdevilrc"

find "$WORK/root" -exec touch -d @1793836800 {} +

echo '=== 1. build (APKv3) ==='
"$APK" mkpkg --compat 3.0.0 \
	--script post-install:"$PKG_SRC/samurai-desktop.post-install" \
	--script post-upgrade:"$PKG_SRC/samurai-desktop.post-install" \
	--sign-key "$SIGN_KEY" \
	--output "$PKG" \
	--files "$WORK/root" \
	--info name:samurai-desktop \
	--info version:"$VERSION" \
	--info arch:noarch \
	--info description:'Realme X2 Pro Plasma Mobile defaults' \
	--info license:LicenseRef-Local-Project \
	--info origin:samurai-desktop \
	--info url:https://github.com/hmhmdcy/edk2-realme-x2-pro \
	--info 'depends:postmarketos-ui-plasma-mobile tinydm samurai-platform modemmanager bluez samurai-platform-pulse calls chatty mmsd-tng callaudiod xdg-desktop-portal-kde elogind' \
	--info build-time:1793836800

echo "=== 2. verify with the image key set ($VERSION) ==="
"$APK" --keys-dir "$KEYS" verify "$PKG"
sha256sum "$PKG"
stat -c '%s bytes' "$PKG"

# The packaged control section must describe the bytes we ship.  adbdump
# reads the manifest straight out of the APK, so this needs no target-root
# skeleton and no qemu-aarch64.  A mismatch here is exactly the defect that
# shipped in 4-r17: the recorded digest belonged to an older powerdevilrc,
# so a later `apk upgrade` would have restored stale content.
SRC_SHA=$(sha256sum "$PKG_SRC/powerdevilrc" | cut -d' ' -f1)
PKG_SHA=$("$APK" adbdump "$PKG" 2>/dev/null |
	awk '/name: powerdevilrc/ { found = 1; next }
	     found && /hash:/ { print $2; exit }')
echo "  source    sha256: $SRC_SHA"
echo "  packaged  sha256: ${PKG_SHA:-<missing>}"
if [ "$PKG_SHA" = "$SRC_SHA" ]; then
	echo '  ok: packaged powerdevilrc matches the source'
else
	echo '  FAIL: packaged powerdevilrc differs from the source' >&2
	exit 1
fi

echo '=== 3. manifest must list both files ==='
