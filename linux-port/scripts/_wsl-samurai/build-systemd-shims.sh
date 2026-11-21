#!/bin/bash
# hkdm-systemd and vvmd-systemd are listed in the v26.06 index but their
# blobs 404 on every public mirror (the redirect target serves an HTML
# error page).  They contain exactly one systemd unit each.  Rebuild those
# two tiny packages from the units the image already extracted, and sign
# them with the board key so both the image and the device can install
# them offline and keep them upgradable.
set -eu
IMG=/mnt/e/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261119-clean/samurai-stable-f2fs-partuuid.simg
W=/root/shimbuild
OUT=/root/recommends-repo
APK=/root/apkstatic/sbin/apk.static
SIGN_KEY=/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa
TRUST=/root/recommends-trust

cleanup() { umount "$W/root" 2>/dev/null || true; losetup -D 2>/dev/null || true; }
trap cleanup EXIT
rm -rf "$W"; mkdir -p "$W/root"
simg2img "$IMG" "$W/a.img"
losetup -D 2>/dev/null || true
L=$(losetup -f --show -r "$W/a.img")
mount -t f2fs -o ro,norecovery "$L" "$W/root"

stage_one() {
	name=$1 version=$2 origin=$3 unit=$4 dest=$5 desc=$6
	root="$W/stage/$name"
	rm -rf "$root"
	install -Dm644 "$W/root$unit" "$root$dest"
	find "$root" -exec touch -d @1793836800 {} +
	"$APK" mkpkg --compat 3.0.0 --sign-key "$SIGN_KEY" \
		--output "$OUT/$name-$version.apk" --files "$root" \
		--info "name:$name" --info "version:$version" \
		--info arch:aarch64 --info "description:$desc" \
		--info "license:GPL-3.0-only" --info "origin:$origin" \
		--info url:https://gitlab.postmarketos.org/postmarketOS/$origin \
		--info build-time:1793836800
	"$APK" --keys-dir "$TRUST" verify "$OUT/$name-$version.apk"
	"$APK" --keys-dir "$TRUST" adbdump "$OUT/$name-$version.apk" 2>/dev/null |
		grep -e 'name:' -e 'version:'
}

stage_one hkdm-systemd 0.3.2-r0 hkdm \
	/usr/lib/systemd/system/hkdm.service \
	/usr/lib/systemd/system/hkdm.service \
	'Lighter-weight hotkey daemon (systemd files)'

stage_one vvmd-systemd 1.1-r31 vvmd \
	/usr/lib/systemd/user/vvmd.service \
	/usr/lib/systemd/user/vvmd.service \
	'Verizon VVM daemon (systemd files)'
