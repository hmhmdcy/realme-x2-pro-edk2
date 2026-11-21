#!/bin/bash
# Build samurai-desktop 4-r17 with the board-wide "never auto-suspend"
# default, using the same signer the running image already trusts.
#
# The running image is apk-tools 3.0.9 (APKv3, adb/sha256 manifests), so the
# package must be built with --compat 3.0.0.  Older tooling produced the
# gzip/v2 format, which this apk cannot install.
set -eu

REPO_DIR=/mnt/e/RealmeX2Pro\ edk2
PKG_SRC="$REPO_DIR/linux-port/packages/samurai-desktop"
WORK=/root/desktop-r17
OUT=/root/desktop-r17-out
SIGN_KEY=/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa
KEYS=/root/installed_keys
APK=/root/apkstatic/sbin/apk.static

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
	--output "$OUT/samurai-desktop-4-r17.apk" \
	--files "$WORK/root" \
	--info name:samurai-desktop \
	--info version:4-r17 \
	--info arch:noarch \
	--info description:'Realme X2 Pro Plasma Mobile defaults' \
	--info license:LicenseRef-Local-Project \
	--info origin:samurai-desktop \
	--info url:https://github.com/hmhmdcy/edk2-realme-x2-pro \
	--info 'depends:postmarketos-ui-plasma-mobile tinydm samurai-platform modemmanager bluez samurai-platform-pulse calls chatty mmsd-tng callaudiod xdg-desktop-portal-kde elogind' \
	--info build-time:1793836800

echo '=== 2. verify with the image key set ==='
"$APK" --keys-dir "$KEYS" verify "$OUT/samurai-desktop-4-r17.apk"
sha256sum "$OUT/samurai-desktop-4-r17.apk"
stat -c '%s bytes' "$OUT/samurai-desktop-4-r17.apk"

echo '=== 3. manifest must list both files ==='
"$APK" info -a --all "$OUT/samurai-desktop-4-r17.apk" 2>/dev/null |
	grep -E '^(P|V|A|D|F):' | head -20 ||
	python3 - "$OUT/samurai-desktop-4-r17.apk" <<'PY'
PY
