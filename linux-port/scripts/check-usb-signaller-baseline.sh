#!/bin/sh
# Read-only postmarketOS USB mode checks for the RMX1931 board layer.
set -eu

CONFIGFS=/sys/kernel/config/usb_gadget
UDC=a600000.usb
fail=0

ok() {
	printf 'ok: %s\n' "$*"
}

bad() {
	printf 'FAIL: %s\n' "$*" >&2
	fail=1
}

expect() {
	path=$1
	want=$2
	got=$(cat "$path" 2>/dev/null || true)
	[ "$got" = "$want" ] &&
		ok "${path##*/}=$want" ||
		bad "${path##*/}: expected '$want', got '$got' ($path)"
}

mode=$(dbus-send --system --type=method_call --print-reply \
	--dest=com.meego.usb_moded /com/meego/usb_moded \
	com.meego.usb_moded.mode_request 2>/dev/null |
	sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1)

[ -n "$mode" ] && ok "usb-moded mode=$mode" || bad 'usb-moded D-Bus unavailable'

apk info -e usb-signaller >/dev/null 2>&1 ||
	bad 'usb-signaller package missing'
apk info -e postmarketos-usb-moded >/dev/null 2>&1 ||
	bad 'postmarketos-usb-moded package missing'
rc-service usb-signaller status >/dev/null 2>&1 ||
	bad 'usb-signaller service is not started'

[ "$(cat "/sys/class/udc/$UDC/state" 2>/dev/null || true)" = configured ] ||
	bad "UDC $UDC is not configured"

case "$mode" in
developer_mode)
	g=$CONFIGFS/usb-signaller-developer
	expect "$g/idVendor" 0x0525
	expect "$g/idProduct" 0xa4a1
	expect "$g/bDeviceClass" 0xef
	expect "$g/bDeviceSubClass" 0x02
	expect "$g/bDeviceProtocol" 0x01
	expect "$g/configs/c.1/MaxPower" 500
	expect "$g/functions/ncm.usb0/qmult" 20
	expect "$g/strings/0x409/manufacturer" Realme
	expect "$g/strings/0x409/product" SamuraiNCM
	expect "$g/configs/c.1/strings/0x409/configuration" 'Samurai NCM'
	ip -4 addr show dev usb0 | grep -q '172\.16\.42\.1/16 ' &&
		ok 'usb0=172.16.42.1/16' ||
		bad 'usb0 is not configured for developer mode'
	nmcli -t -f NAME,DEVICE,STATE connection show |
		grep -qx 'Samurai NCM:usb0:activated' &&
		ok 'NetworkManager developer connection active' ||
		bad 'NetworkManager developer connection is not active'
	pgrep -f '^/usr/bin/unudhcpd .* -s 172\.16\.42\.1 -c 172\.16\.42\.2$' \
		>/dev/null &&
		ok 'unudhcpd advertises 172.16.42.1/.2' ||
		bad 'unudhcpd address pair is incorrect'
	;;
tethering_mode)
	g=$CONFIGFS/usb-signaller-tethering
	expect "$g/idVendor" 0x0525
	expect "$g/idProduct" 0xa4a1
	expect "$g/bDeviceClass" 0xef
	expect "$g/configs/c.1/MaxPower" 500
	expect "$g/functions/ncm.usb0/qmult" 20
	ip -4 addr show dev usb0 | grep -q '10\.42\.0\.1/24 ' &&
		ok 'usb0=10.42.0.1/24' ||
		bad 'usb0 is not configured for tethering mode'
	nmcli -t -f NAME,DEVICE,STATE connection show |
		grep -qx 'Samurai Tethering:usb0:activated' &&
		ok 'NetworkManager tethering connection active' ||
		bad 'NetworkManager tethering connection is not active'
	[ "$(cat /proc/sys/net/ipv4/ip_forward)" = 1 ] &&
		ok 'IPv4 forwarding enabled' ||
		bad 'IPv4 forwarding is disabled'
	;;
mtp_ffs_mode)
	g=$CONFIGFS/usb-signaller-mtp
	expect "$g/idVendor" 0x0525
	expect "$g/idProduct" 0xa4a2
	expect "$g/bDeviceClass" 0x00
	expect "$g/configs/c.1/MaxPower" 500
	for ep in 0 1 2 3; do
		[ -e "/dev/mtp/ep$ep" ] ||
			bad "missing FunctionFS endpoint /dev/mtp/ep$ep"
	done
	rc-service umtprd status >/dev/null 2>&1 &&
		ok 'umtprd is running' ||
		bad 'umtprd is not running'
	;;
charging_only)
	for gadget in "$CONFIGFS"/*; do
		[ -d "$gadget" ] || continue
		[ -z "$(cat "$gadget/UDC" 2>/dev/null || true)" ] ||
			bad "charging mode still has bound gadget ${gadget##*/}"
	done
	;;
*)
	bad "unexpected mode '$mode'"
	;;
esac

if [ "$fail" -ne 0 ]; then
	printf 'RESULT: postmarketOS USB baseline failed\n' >&2
	exit 1
fi

printf 'RESULT: postmarketOS USB baseline passed (mode=%s)\n' "$mode"
