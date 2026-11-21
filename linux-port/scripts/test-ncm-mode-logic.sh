#!/bin/sh
# Test the mode-selection logic of samurai-ncm-watchdog.sh.
#
# The watchdog must never take usb0 away from NetworkManager in tethering
# mode (that mode relies on nmcli ipv4.method=shared), while developer mode
# must own the link so carrier can rise before any profile activates.
#
# This exercises current_mode() and the dispatch conditions against a fake
# configfs tree; it does not touch real hardware.

set -eu

script=${1:?usage: $0 WATCHDOG_SCRIPT}
iface=${SAMURAI_NCM_IFACE:-usb0}
fake=$(mktemp -d)
trap 'rm -rf "$fake"' EXIT

configfs=$fake/configfs
mkdir -p "$configfs/usb-signaller-developer" \
	"$configfs/usb-signaller-tethering" \
	"$configfs/usb-signaller-mtp"

# Extract current_mode() so we can call it directly.
func=$(awk '/^current_mode\(\)/,/^}/' "$script")
[ -n "$func" ] || { echo "FAIL: current_mode() not found"; exit 1; }

# shellcheck disable=SC2086
eval "$func"

check()
{
	bound=$1
	want=$2
	for gadget in "$configfs"/*; do
		: > "$gadget/UDC"
	done
	if [ "$bound" != none ]; then
		: > "$configfs/usb-signaller-$bound/UDC"
		printf '%s\n' "${gadget##*/}" > /dev/null
	fi
	# Mark only the requested gadget as bound with a real UDC value.
	for gadget in "$configfs"/*; do
		printf '\n' > "$gadget/UDC"
	done
	if [ "$bound" != none ]; then
		printf 'a600000.usb\n' > "$configfs/usb-signaller-$bound/UDC"
	fi
	got=$(CONFIGFS=$configfs current_mode)
	if [ "$got" = "$want" ]; then
		echo "OK   bound=$bound -> $got"
	else
		echo "FAIL bound=$bound -> want $want, got $got"
		return 1
	fi
}

rc=0
check developer developer || rc=1
check tethering tethering || rc=1
check mtp mtp || rc=1
check none other || rc=1

# Mode ownership: developer must be marked unmanaged; others must not.
if grep -q 'nmcli device set "$IFACE" managed no' "$script"; then
	echo "OK   developer path marks usb0 unmanaged"
else
	echo "FAIL developer path never marks usb0 unmanaged"
	rc=1
fi
if grep -q 'nmcli device set "$IFACE" managed yes' "$script"; then
	echo "OK   leaving developer mode returns usb0 to NetworkManager"
else
	echo "FAIL no path returns usb0 to NetworkManager"
	rc=1
fi

exit $rc
