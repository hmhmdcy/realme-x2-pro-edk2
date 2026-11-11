#!/bin/sh
# Exercise usbwake-guard without touching the host's real power supplies.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
guard=$here/usbwake-guard
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' 0 1 2 15

make_power() {
	name=$1
	type=$2
	online=$3
	status=${4:-}
	mkdir -p "$tmp/power/$name"
	printf '%s\n' "$type" >"$tmp/power/$name/type"
	if [ -n "$online" ]; then
		printf '%s\n' "$online" >"$tmp/power/$name/online"
	fi
	if [ -n "$status" ]; then
		printf '%s\n' "$status" >"$tmp/power/$name/status"
	fi
}

make_ncm() {
	mkdir -p "$tmp/udc/fake-udc" \
		"$tmp/gadget/g1/functions/ncm.usb0" "$tmp/net/usb0"
	printf 'configured\n' >"$tmp/udc/fake-udc/state"
	printf 'fake-udc\n' >"$tmp/gadget/g1/UDC"
	printf 'usb0\n' >"$tmp/gadget/g1/functions/ncm.usb0/ifname"
	printf '1\n' >"$tmp/net/usb0/carrier"
}

make_function() {
	function_name=$1
	ifname=$2
	mkdir -p "$tmp/udc/fake-udc" \
		"$tmp/gadget/g1/functions/$function_name" "$tmp/net/$ifname"
	printf 'configured\n' >"$tmp/udc/fake-udc/state"
	printf 'fake-udc\n' >"$tmp/gadget/g1/UDC"
	printf '%s\n' "$ifname" >"$tmp/gadget/g1/functions/$function_name/ifname"
	printf '1\n' >"$tmp/net/$ifname/carrier"
}

reset_env() {
	rm -rf "$tmp/power" "$tmp/udc" "$tmp/gadget" "$tmp/net"
	export USBWAKE_POWER_SUPPLY_DIR="$tmp/power"
	export USBWAKE_UDC_DIR="$tmp/udc"
	export USBWAKE_GADGET_ROOT="$tmp/gadget"
	export USBWAKE_NET_CLASS="$tmp/net"
}

check() {
	expected=$1
	name=$2
	set +e
	"$guard"
	actual=$?
	set -e
	if [ "$actual" -ne "$expected" ]; then
		printf 'FAIL %s: expected %s, got %s\n' "$name" "$expected" "$actual" >&2
		exit 1
	fi
	printf 'ok   %s\n' "$name"
}

reset_env
make_power mains Mains 1
USBWAKE_GUARD_MODE=power check 254 'Mains online'

reset_env
make_power usb USB 1
USBWAKE_GUARD_MODE=power check 254 'USB online'

reset_env
make_power usb USB 0
USBWAKE_GUARD_MODE=power check 0 'USB offline'

reset_env
make_power battery Battery '' Full
USBWAKE_GUARD_MODE=power check 0 'battery is not external power'

reset_env
make_power usb USB '' Charging
USBWAKE_GUARD_MODE=power check 254 'status fallback'

reset_env
make_power unknown Unknown 1
USBWAKE_GUARD_MODE=power check 0 'unknown supply type'

reset_env
make_ncm
USBWAKE_GUARD_MODE=ncm check 254 'NCM configured and carrier up'

reset_env
make_function ecm.usb0 eth0
USBWAKE_GUARD_MODE=ncm check 254 'ECM function discovered'

reset_env
make_function rndis.usb1 usb1
USBWAKE_GUARD_MODE=ncm check 254 'RNDIS function discovered'

reset_env
make_ncm
printf '0\n' >"$tmp/net/usb0/carrier"
USBWAKE_GUARD_MODE=ncm check 0 'carrier down'

reset_env
make_ncm
printf 'other-udc\n' >"$tmp/gadget/g1/UDC"
USBWAKE_GUARD_MODE=ncm check 0 'gadget not bound to configured UDC'

reset_env
mkdir -p "$tmp/udc/fake-udc" "$tmp/gadget/g1"
printf 'configured\n' >"$tmp/udc/fake-udc/state"
printf 'fake-udc\n' >"$tmp/gadget/g1/UDC"
USBWAKE_GUARD_MODE=ncm check 0 'configured UDC without a network function'

reset_env
make_power usb USB 1
make_ncm
USBWAKE_GUARD_MODE=ncm check 254 'NCM with external power online'

reset_env
USBWAKE_GUARD_MODE=ncm check 0 'no NCM'

reset_env
make_power usb USB 1
USBWAKE_GUARD_MODE=either check 254 'either: power only'

reset_env
make_ncm
USBWAKE_GUARD_MODE=either check 254 'either: NCM only'

reset_env
USBWAKE_GUARD_MODE=either check 0 'either: neither'

reset_env
make_ncm
set +e
USBWAKE_POWER_SUPPLY_DIR="$tmp/power" ./usb-sleep-guard
rc=$?
set -e
[ "$rc" -eq 254 ] || {
	printf 'FAIL legacy NCM wrapper: expected 254, got %s\n' "$rc" >&2
	exit 1
}
printf 'ok   legacy NCM wrapper\n'

printf 'usbwake-guard: all checks passed\n'
