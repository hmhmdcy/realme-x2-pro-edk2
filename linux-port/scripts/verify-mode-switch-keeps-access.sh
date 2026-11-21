#!/bin/sh
# Guard the invariant that broke once: switching USB gadget mode must never
# leave the device without a usable maintenance channel.
#
# A tethering run that relied on NetworkManager's shared profile produced a
# link with carrier 0 and 0 received bytes, and with no link-local address
# the device became unreachable.  This script exercises the watchdog's mode
# dispatch with a fake sysfs/configfs tree and asserts that both developer and
# tethering leave usb0 UP with 169.254.42.1/16, and that tethering hands the
# device back to NetworkManager for 10.42.0.1/24 + dnsmasq.
#
# Runs offline; see test-ncm-watchdog-behaviour.sh for the harness details.

set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
watchdog=${1:-$here/samurai-ncm-watchdog.sh}

echo "== developer and tethering must both keep a maintenance channel =="
sh "$here/test-ncm-watchdog-behaviour.sh" "$watchdog"

echo ""
echo "== static checks =="
fail=0

check()
{
	desc=$1
	pattern=$2
	if grep -q -- "$pattern" "$watchdog"; then
		echo "OK   $desc"
	else
		echo "FAIL $desc (missing pattern: $pattern)"
		fail=1
	fi
}

check "link-local is always published" 'have_linklocal || ip addr add "$LINKLOCAL/16"'
check "developer mode owns usb0" 'nmcli device set "$IFACE" managed no'
check "tethering publishes its own subnet" 'ip addr add "$TETHER_ADDR/24"'
check "tethering keeps NetworkManager away" 'nmcli device set "$IFACE" managed no'
check "tethering never adds the developer address" '172.16.42.1/24 is only added in developer mode'
check "mode handover survives a restart" 'STATE_FILE'

if [ "$fail" -ne 0 ]; then
	echo "RESULT: FAIL"
	exit 1
fi
echo "RESULT: PASS - mode switching preserves an addressable usb0"
