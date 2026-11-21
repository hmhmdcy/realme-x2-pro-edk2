#!/bin/bash
# Build samurai-platform 6-r24 with the stock `wifi.powersave=2` default,
# signing with the key the running image already trusts (APKv3, because the
# device ships apk-tools 3.0.9).
#
# The package must stay COMPLETE: apk replaces the whole file list on
# upgrade, so a package carrying only the changed conf (a smaller version of
# this script did exactly that) would silently delete the other 14 files on
# the device when installed.
set -eu

REPO="/mnt/e/RealmeX2Pro edk2"
PKG_SRC="$REPO/linux-port/packages/samurai-platform"
WORK=/root/platform-r24
OUT=/root/platform-r24-out
SIGN_KEY="/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa"
KEYS=/root/installed_keys
APK=/root/apkstatic/sbin/apk.static

rm -rf "$WORK" "$OUT"
mkdir -p "$WORK/root" "$OUT"

install -Dm755 "$PKG_SRC"/usr_sbin_samurai-bluetooth      "$WORK/root/usr/sbin/samurai-bluetooth"
install -Dm755 "$PKG_SRC"/usr_sbin_samurai-modem-configs   "$WORK/root/usr/sbin/samurai-modem-configs"
install -Dm755 "$PKG_SRC"/usr_sbin_samurai-modem-remoteproc "$WORK/root/usr/sbin/samurai-modem-remoteproc"
install -Dm755 "$PKG_SRC"/usr_sbin_samurai-radio-address   "$WORK/root/usr/sbin/samurai-radio-address"
install -Dm755 "$PKG_SRC"/usr_sbin_samurai-wifi            "$WORK/root/usr/sbin/samurai-wifi"
install -Dm755 "$PKG_SRC"/usr_sbin_samurai-usb-recover     "$WORK/root/usr/sbin/samurai-usb-recover"
install -Dm755 "$PKG_SRC"/usr_sbin_samurai-usb-network-watchdog \
	"$WORK/root/usr/sbin/samurai-usb-network-watchdog"
install -Dm644 "$PKG_SRC"/etc_samurai_usb-dhcp.conf \
	"$WORK/root/etc/samurai/usb-dhcp.conf"
install -Dm644 "$PKG_SRC"/etc_NetworkManager_conf.d_20-samurai-wlan.conf \
	"$WORK/root/etc/NetworkManager/conf.d/20-samurai-wlan.conf"
install -Dm644 "$PKG_SRC"/etc_usb-signaller.d_90-samurai.toml \
	"$WORK/root/etc/usb-signaller.d/90-samurai.toml"
install -Dm644 "$PKG_SRC"/99-realme-rmx1931-sensors.rules \
	"$WORK/root/usr/lib/udev/rules.d/99-realme-rmx1931-sensors.rules"
install -Dm644 "$PKG_SRC"/99-realme-rmx1931-haptics.rules \
	"$WORK/root/usr/lib/udev/rules.d/99-realme-rmx1931-haptics.rules"
install -Dm644 "$PKG_SRC"/usr_local_share_dbus-1_system-services_org.freedesktop.ModemManager1.service \
	"$WORK/root/usr/local/share/dbus-1/system-services/org.freedesktop.ModemManager1.service"
install -Dm644 "$PKG_SRC"/usr_share_alsa_ucm2_conf.d_Realme_X2_Pro_HiFi.conf \
	"$WORK/root/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/HiFi.conf"
install -Dm644 "$PKG_SRC"/usr_share_alsa_ucm2_conf.d_Realme_X2_Pro_Realme_X2_Pro.conf \
	"$WORK/root/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf"

find "$WORK/root" -exec touch -d @1793836800 {} +

echo '=== 1. build (APKv3) ==='
"$APK" mkpkg --compat 3.0.0 \
	--sign-key "$SIGN_KEY" \
	--output "$OUT/samurai-platform-6-r24.apk" \
	--files "$WORK/root" \
	--info name:samurai-platform \
	--info version:6-r24 \
	--info arch:noarch \
	--info description:'Realme X2 Pro platform' \
	--info license:LicenseRef-Local-Project \
	--info origin:samurai-platform \
	--info url:https://github.com/hmhmdcy/realme-x2-pro-pmaports \
	--info 'depends:python3 eudev iproute2 util-linux libqmi qmi-utils networkmanager bluez wpa_supplicant openssh-server-pam alsa-ucm-conf alsa-utils sleep-inhibitor dnsmasq usb-signaller>=0.4.3-r9 unudhcpd>=0.5.0-r2 qrtr /bin/sh' \
	--info build-time:1793836800

echo '=== 2. verify against the image key set ==='
"$APK" --keys-dir "$KEYS" verify "$OUT/samurai-platform-6-r24.apk"
sha256sum "$OUT/samurai-platform-6-r24.apk"
stat -c '%s bytes' "$OUT/samurai-platform-6-r24.apk"

echo '=== 3. manifest ==='
echo "  file count: $(find "$WORK/root" -type f | wc -l)  (must be 15)"
find "$WORK/root" -type f | sed "s|$WORK/root||" | sort
