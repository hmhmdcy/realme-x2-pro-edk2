#!/bin/bash
# Put the official Plasma Mobile recommends into the signed board
# repository so a clean image can install them offline and keep them
# upgradeable.
#
# Provenance of each file:
#   gst-libav, gst-plugins-ugly, hkdm, plasma-mobile-sounds, vvmd,
#   vvmplayer      -> Alpine release key 616ae350 (official, untouched)
#   ttyescape      -> rebuilt from the official upstream tarball; the
#                     official APK is signed by pmos@local-6a19ae2a, a key
#                     that is not published anywhere, so it can never verify
set -eu

APK=/root/apkstatic/sbin/apk.static
STORAGE=/root/recommends-repo
SOURCE_DATE_EPOCH=1793836800

rm -rf "$STORAGE"
mkdir -p "$STORAGE"

for p in gst-libav gst-plugins-ugly hkdm plasma-mobile-sounds vvmd vvmplayer; do
	f=$(ls /root/extra-apks/"$p"-*.apk 2>/dev/null | head -1)
	[ -n "$f" ] || { echo "MISSING official apk: $p"; exit 1; }
	install -m0644 "$f" "$STORAGE/$(basename "$f")"
done
install -m0644 /root/ttyescape-out/ttyescape-1.0.1-r5.apk "$STORAGE/"

echo '=== every staged file must verify against the image trust set ==='
# --keys-dir accepts exactly one directory (a second one silently replaces
# the first), so merge the board keys and the Alpine release key.
TRUST=/root/recommends-trust
rm -rf "$TRUST"
mkdir -p "$TRUST"
cp /root/installed_keys/*.rsa.pub "$TRUST"/
cp /root/akeys/*.rsa.pub "$TRUST"/
for f in "$STORAGE"/*.apk; do
	"$APK" --keys-dir "$TRUST" verify "$f" >/dev/null 2>&1 ||
		{ echo "UNTRUSTED: $f"; exit 1; }
	echo "  ok $(basename "$f")"
done

echo '=== stage complete ==='
ls -l "$STORAGE" | tail -8
