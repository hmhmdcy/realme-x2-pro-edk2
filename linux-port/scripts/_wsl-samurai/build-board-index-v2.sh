#!/bin/bash
# Extend the signed board repository with the official Plasma Mobile
# recommends that the earlier image build never installed, then rebuild
# and re-sign the index.
#
# The extends are exactly the two missing entries of the official
# _pmb_recommends list (verified against pmaports v26.06):
#   plasma-mobile-sounds, ttyescape
# Their dependencies (hkdm/buffyboard/terminus-font/kbd, vvmd, gst-*) are
# staged as well, because the offline image cannot download them.
set -eu

APK=/root/apkstatic/sbin/apk.static
SIGN_KEY=/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa
KEYS=/root/installed_keys
BASE=/root/boardrepo-r17
STAGE=/root/boardrepo-final
RECOMMENDS=/root/recommends-repo

rm -rf "$STAGE"
mkdir -p "$STAGE"
cp "$BASE"/*.apk "$STAGE"/
# Only ttyescape ships here.  The other recommends exist in the official
# repositories under the same name and version; copying them into the board
# repository creates two index entries for one package, and apk then picks
# whichever index it loaded first.  If that turns out to be the remote one,
# an offline image cannot fetch it ("package mentioned in index not found").
# Two packages are exceptions and do ship here:
#   ttyescape         official signature uses a key that is not published
#                     anywhere, so the official artifact is always UNTRUSTED
#   hkdm-systemd,     the index advertises them but no mirror serves the
#   vvmd-systemd      blobs (404); they are one systemd unit each, rebuilt
#                     here from the units the official packages install
cp "$RECOMMENDS"/ttyescape-1.0.1-r5.apk "$STAGE"/
cp "$RECOMMENDS"/hkdm-systemd-0.3.2-r0.apk "$STAGE"/
cp "$RECOMMENDS"/vvmd-systemd-1.1-r31.apk "$STAGE"/

echo '=== staged package set ==='
ls "$STAGE" | wc -l

echo '=== rebuild + sign index (APKv3) ==='
# One merged trust dir: mkndx verifies every packed APK, and --keys-dir
# only accepts a single directory.
TRUST=/root/boardrepo-trust
rm -rf "$TRUST"
mkdir -p "$TRUST"
cp "$KEYS"/*.rsa.pub "$TRUST"/
cp /root/akeys/*.rsa.pub "$TRUST"/
rm -f "$STAGE/APKINDEX.tar.gz"
"$APK" --keys-dir "$TRUST" --sign-key "$SIGN_KEY" mkndx \
	--pkgname-spec '${name}-${version}.apk' \
	--description 'Realme X2 Pro board packages (official v26.06 base)' \
	--output "$STAGE/APKINDEX.tar.gz" \
	"$STAGE"/*.apk
"$APK" --keys-dir "$TRUST" verify "$STAGE/APKINDEX.tar.gz"

echo '=== index entries ==='
"$APK" --keys-dir "$KEYS" adbdump "$STAGE/APKINDEX.tar.gz" 2>/dev/null |
	grep -e '  - name:' | sed 's/^/  /'
