#!/bin/bash
# The original complaint was that Firefox, the app store and other apps
# disappeared from the desktop.  Prove they are actually in the delivery
# image, not just in the device's world file.
set -eu
IMG=/mnt/e/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261119-clean/samurai-stable-f2fs-partuuid.simg
W=/root/apps
cleanup() { umount "$W/root" 2>/dev/null || true; losetup -D 2>/dev/null || true; }
trap cleanup EXIT
rm -rf "$W"; mkdir -p "$W/root"
simg2img "$IMG" "$W/a.img"
losetup -D 2>/dev/null || true
L=$(losetup -f --show -r "$W/a.img")
mount -t f2fs -o ro,norecovery "$L" "$W/root"
R="$W/root"

echo '== packages the user missed =='
for p in firefox-esr mobile-config-firefox discover discover-backend-apk \
	plasma-camera plasma-dialer plasma-phonebook dolphin konsole kate \
	kclock kweather krecorder qmlkonsole spacebar alligator audiotube \
	elisa itinerary kalgebra kalk kasts kdeconnect keysmith arianna koko \
	neochat okular-mobile tokodon; do
	awk -v want="$p" '/^P:/{if (substr($0,3)==want) f=1} END{exit !f}' \
		"$R/lib/apk/db/installed" &&
		printf '  ok      %s\n' "$p" || printf '  MISSING %s\n' "$p"
done

echo '== key entry points exist on disk =='
for f in /usr/bin/firefox-esr /usr/bin/plasma-discover \
	/usr/bin/plasma-camera /usr/bin/plasma-dialer /usr/bin/dolphin; do
	[ -e "$R$f" ] && printf '  ok      %s\n' "$f" || printf '  MISSING %s\n' "$f"
done
