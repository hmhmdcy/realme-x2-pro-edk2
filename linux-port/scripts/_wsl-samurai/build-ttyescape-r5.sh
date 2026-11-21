#!/bin/bash
# Rebuild ttyescape 1.0.1-r5 from the *official* pmaports recipe.
#
# The official v26.06 APK is signed by pmos@local-6a19ae2a.  That key is not
# published anywhere (postmarketos-keys ships only build.postmarketos.org),
# so the official artifact is permanently UNTRUSTED on every postmarketOS
# install.  This script rebuilds the same noarch payload from the pinned
# upstream tarball and signs it with the board key the image already trusts,
# so the package is installable and updatable like every other board package.
#
# The two installed files are proven byte-identical to the official APK:
#   togglevt.sh           729280a4...
#   ttyescape-hkdm.toml   88034b54...
set -eu

APK=/root/apkstatic/sbin/apk.static
SIGN_KEY=/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa
KEYS=/root/installed_keys
SRC=/root/ttybuild/ttyescape-1.0.1
OUT=/root/ttyescape-out
STAGE=/root/ttyescape-stage

rm -rf "$OUT" "$STAGE"
mkdir -p "$OUT" "$STAGE/root/usr/bin" \
	"$STAGE/root/etc/hkdm/config.d"

install -Dm755 "$SRC/togglevt.sh" "$STAGE/root/usr/bin/togglevt.sh"
install -Dm755 "$SRC/ttyescape-hkdm.toml" \
	"$STAGE/root/etc/hkdm/config.d/ttyescape.toml"
find "$STAGE/root" -exec touch -d @1780067889 {} +

"$APK" mkpkg --compat 3.0.0 \
	--sign-key "$SIGN_KEY" \
	--output "$OUT/ttyescape-1.0.1-r5.apk" \
	--files "$STAGE/root" \
	--info name:ttyescape \
	--info version:1.0.1-r5 \
	--info arch:noarch \
	--info description:'Daemon to allow users to escape to a tty' \
	--info license:GPL-2.0 \
	--info origin:ttyescape \
	--info url:https://gitlab.postmarketos.org/postmarketOS/ttyescape \
	--info 'depends:hkdm buffyboard terminus-font kbd' \
	--info build-time:1780067889

"$APK" --keys-dir "$KEYS" verify "$OUT/ttyescape-1.0.1-r5.apk"
"$APK" --keys-dir "$KEYS" adbdump "$OUT/ttyescape-1.0.1-r5.apk" 2>/dev/null |
	grep -e 'name:' -e 'version:' -e 'hash:' -e 'size:'
sha256sum "$OUT/ttyescape-1.0.1-r5.apk"
