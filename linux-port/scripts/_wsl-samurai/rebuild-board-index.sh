#!/bin/bash
# Rebuild the board repository index in APKv3 (adb) format, because the
# running image uses apk-tools 3.0.9 and rejects gzip/v2 indexes.
set -eu

REPO=/root/boardrepo-installed
OUT=/root/desktop-r17-out
PKG_SRC=/mnt/e/RealmeX2Pro\ edk2/linux-port/packages/samurai-desktop
SIGN_KEY=/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa
KEYS=/root/installed_keys
APK=/root/apkstatic/sbin/apk.static
STAGE=/root/boardrepo-r17
VERSION=$(sed -n 's/^pkgver=//p' "$PKG_SRC/APKBUILD")-r$(sed -n 's/^pkgrel=//p' "$PKG_SRC/APKBUILD")

rm -rf "$STAGE"
mkdir -p "$STAGE"

echo '=== copy current board repo, replace samurai-desktop ==='
for f in "$REPO"/*.apk; do
	base=$(basename "$f")
	case "$base" in
	samurai-desktop-*.apk) continue ;;
	esac
	cp "$f" "$STAGE/$base"
done
cp "$OUT/samurai-desktop-$VERSION.apk" "$STAGE/"

# --sign-key is a *global* apk option and must precede the applet name;
# putting it after "mkndx" is silently ignored and yields an unsigned index.
echo '=== rebuild index (APKv3) + sign ==='
rm -f "$STAGE/APKINDEX.tar.gz"
"$APK" --keys-dir "$KEYS" --sign-key "$SIGN_KEY" mkndx \
	--pkgname-spec '${name}-${version}.apk' \
	--description 'Realme X2 Pro board packages' \
	--output "$STAGE/APKINDEX.tar.gz" \
	"$STAGE"/*.apk

"$APK" --keys-dir "$KEYS" verify "$STAGE/APKINDEX.tar.gz"
"$APK" --keys-dir "$KEYS" adbdump "$STAGE/APKINDEX.tar.gz" 2>/dev/null |
	grep -e 'name:' -e 'version:' | grep -A1 -F 'samurai-desktop'
ls -l "$STAGE" | tail -4
sha256sum "$STAGE/APKINDEX.tar.gz" "$STAGE/samurai-desktop-$VERSION.apk"
