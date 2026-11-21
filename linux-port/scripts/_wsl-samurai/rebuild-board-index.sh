#!/bin/bash
# Rebuild the board repository index in APKv3 (adb) format, because the
# running image uses apk-tools 3.0.9 and rejects gzip/v2 indexes.
set -eu

REPO=/root/boardrepo-installed
OUT=/root/desktop-r17-out
SIGN_KEY=/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa
KEYS=/root/installed_keys
APK=/root/apkstatic/sbin/apk.static
STAGE=/root/boardrepo-r17

rm -rf "$STAGE"
mkdir -p "$STAGE"

echo '=== copy current board repo, replace samurai-desktop ==='
for f in "$REPO"/*.apk; do
	base=$(basename "$f")
	[ "$base" = samurai-desktop-4-r16.apk ] && continue
	cp "$f" "$STAGE/$base"
done
cp "$OUT/samurai-desktop-4-r17.apk" "$STAGE/"

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
sha256sum "$STAGE/APKINDEX.tar.gz" "$STAGE/samurai-desktop-4-r17.apk"
