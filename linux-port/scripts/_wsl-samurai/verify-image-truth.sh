#!/bin/bash
# Ground truth for the published image: is every declared package actually
# installed, and do the two /etc/xdg files have real packge owners?
set -eu
IMG=/mnt/e/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261119-clean/samurai-stable-f2fs-partuuid.simg
W=/root/truth
cleanup() { umount "$W/root" 2>/dev/null || true; losetup -D 2>/dev/null || true; }
trap cleanup EXIT
rm -rf "$W"; mkdir -p "$W/root"
simg2img "$IMG" "$W/a.img"
losetup -D 2>/dev/null || true
L=$(losetup -f --show -r "$W/a.img")
mount -t f2fs -o ro,norecovery "$L" "$W/root"
R="$W/root"

echo '== powerdevilrc owner, read straight from the DB =='
awk '
/^P:/ { pkg = substr($0, 3) }
/^F:etc\/xdg$/ { inxdg = 1; next }
/^F:/ { inxdg = 0 }
inxdg && /^R:powerdevilrc$/ { print "  owner:", pkg }
' "$R/lib/apk/db/installed"

echo '== official recommends recorded =='
for p in hkdm hkdm-systemd ttyescape plasma-mobile-sounds vvmd vvmplayer; do
	awk -v want="$p" '/^P:/{if (substr($0,3)==want) f=1} END{exit !f}' \
		"$R/lib/apk/db/installed" &&
		printf '  ok      %s\n' "$p" || printf '  MISSING %s\n' "$p"
done

echo '== broken flags =='
grep -n -F 'f:' "$R/lib/apk/db/installed" | head -4

echo '== repo dir contents =='
ls "$R/usr/share/samurai/packages/aarch64" | wc -l

echo '== recommend payloads actually on disk =='
for f in /usr/bin/togglevt.sh /usr/sbin/hkdm \
	/usr/share/sounds/plasma-mobile/index.theme; do
	p="$R$f"
	if [ -e "$p" ]; then
		printf '  ok      %-42s %s bytes\n' "$f" "$(stat -c %s "$p")"
	else
		printf '  MISSING %s\n' "$f"
	fi
done

echo '== ttyescape payload hashes (must match the official APK) =='
sha512sum "$R/usr/bin/togglevt.sh" "$R/etc/hkdm/config.d/ttyescape.toml"
