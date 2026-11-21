#!/bin/sh
# Board glue for the rootfs NCM netdev (L6).
#
# Layering: usb-signaller owns the configfs gadget (L4/L6).  This port cannot
# hand usb0 to NetworkManager alone: NM only activates an ethernet profile
# when carrier is already 1, but u_ether only raises carrier after
# gether_connect() enables the endpoints, and the endpoints are only
# re-enabled by eth_open() -> eth_start() after the netdev is brought UP.
# With carrier=0 and usb0 DOWN the two wait for each other forever.  The
# pre-usb-signaller rootfs backend avoided this by explicitly marking usb0
# unmanaged and doing `ip link set up` + address + DHCP itself.
#
# We keep the standard gadget owner (usb-signaller) and keep DHCP/SSH in the
# distro (unudhcpd.usb0, sshd).  The glue owns exactly the link enablement
# and the deterministic address, because that is what cannot be expressed in
# a profile that only activates on carrier.

set -u

IFACE=${SAMURAI_NCM_IFACE:-usb0}
LOG=${SAMURAI_NCM_LOG:-/var/log/samurai/usb-network.log}
LINKLOCAL=169.254.42.1
SERVER=172.16.42.1
DHCP_SERVICE=${SAMURAI_DHCP_SERVICE:-unudhcpd.usb0}
# Tethering subnet served by dnsmasq from /etc/samurai/usb-dhcp.conf.
TETHER_ADDR=${SAMURAI_TETHER_ADDR:-10.42.0.1}
WAIT_LIMIT=${SAMURAI_NCM_WAIT:-120}
CONFIGFS=${SAMURAI_CONFIGFS:-/sys/kernel/config/usb_gadget}
# sysfs root, overridable so the watchdog can be exercised against a fake
# tree in tests (see test-ncm-watchdog-behaviour.sh).
SYSFS=${SAMURAI_SYSFS:-/sys}
# 0 means run forever (production).  Tests set a small positive value so the
# loop terminates and its side effects can be asserted.
MAX_ITERATIONS=${SAMURAI_NCM_ITERATIONS:-0}
# Last gadget mode seen by a previous watchdog run.  The handover from
# developer to tethering must survive a watchdog restart (supervise-daemon
# respawn, service restart, or crash), so it cannot live only in a shell
# variable.
STATE_FILE=${SAMURAI_NCM_STATE:-/run/samurai-usb-network.mode}

# Which usb-signaller gadget is currently bound?  Only developer mode hands
# 172.16.42.1 + unudhcpd to this port; tethering mode deliberately uses
# NetworkManager's ipv4.method=shared (10.42.0.1/24 + dnsmasq) and a dummy
# interface for the uplink, so taking usb0 away from NetworkManager there
# would break tethering outright.
current_mode()
{
	for gadget in "$CONFIGFS"/*; do
		[ -d "$gadget" ] || continue
		[ -n "$(cat "$gadget/UDC" 2>/dev/null)" ] || continue
		case ${gadget##*/} in
		*developer*) printf '%s\n' developer; return 0 ;;
		*tethering*) printf '%s\n' tethering; return 0 ;;
		*mtp*) printf '%s\n' mtp; return 0 ;;
		*accessory*) printf '%s\n' accessory; return 0 ;;
		*mass_storage*) printf '%s\n' mass_storage; return 0 ;;
		esac
	done
	printf '%s\n' other
}

log()
{
	mkdir -p "${LOG%/*}" 2>/dev/null || true
	printf '%s %s\n' "$(date -Is)" "$*" >>"$LOG" 2>/dev/null || true
}

wait_for_iface()
{
	start=$(date +%s)
	while [ ! -e "$SYSFS/class/net/$IFACE" ]; do
		[ $(( $(date +%s) - start )) -lt "$WAIT_LIMIT" ] || return 1
		sleep 2
	done
	return 0
}

have_linklocal()
{
	ip -4 addr show dev "$IFACE" 2>/dev/null | grep -q "inet $LINKLOCAL/16 "
}

ensure_dhcpd()
{
	if pidof unudhcpd >/dev/null 2>&1; then
		return 0
	fi
	log "unudhcpd not running; restarting $DHCP_SERVICE"
	rc-service "$DHCP_SERVICE" restart >/dev/null 2>&1 ||
		log "restart of $DHCP_SERVICE failed"
}

start_tether_dhcp()
{
	# The image ships /etc/samurai/usb-dhcp.conf (port=0, interface=usb0,
	# dhcp-range 10.42.0.2-.10) plus nftables rules for usb* interfaces.
	# There is no dnsmasq.usb0 init template, so drive dnsmasq directly from
	# that config and keep a single instance under this watchdog.
	conf=/etc/samurai/usb-dhcp.conf
	[ -f "$conf" ] || return 0
	pidfile=/run/samurai-tether-dnsmasq.pid
	leasefile=/var/lib/misc/dnsmasq-usb.leases
	mkdir -p /var/lib/misc 2>/dev/null || true

	if [ -r "$pidfile" ] && kill -0 "$(cat "$pidfile" 2>/dev/null)" 2>/dev/null; then
		return 0
	fi
	command -v dnsmasq >/dev/null 2>&1 || {
		log "dnsmasq not installed; tethering has no DHCP"
		return 0
	}
	dnsmasq --conf-file="$conf" --pid-file="$pidfile" \
		--dhcp-leasefile="$leasefile" >/dev/null 2>&1 ||
		log "dnsmasq failed for tethering on $IFACE"
	log "tethering DHCP started on $IFACE"
}

assert_unmanaged()
{
	# The usb-signaller mode script asks NetworkManager to manage usb0 at
	# mode start.  NetworkManager then creates the profile but cannot
	# activate it while carrier is 0, and once it manages the device it may
	# also bring the link down.  Re-assert board ownership while the link is
	# unproven; it is a no-op when NM is already ignoring usb0.
	command -v nmcli >/dev/null 2>&1 || return 0
	nmcli device set "$IFACE" managed no >/dev/null 2>&1 || true
}

configure_developer()
{
	ip link set "$IFACE" up 2>/dev/null || log "ip link set $IFACE up failed"
	have_linklocal || ip addr add "$LINKLOCAL/16" dev "$IFACE" 2>/dev/null ||
		log "adding $LINKLOCAL to $IFACE failed"
	ip -4 addr show dev "$IFACE" 2>/dev/null | grep -q "inet $SERVER/24 " ||
		ip addr add "$SERVER/24" dev "$IFACE" 2>/dev/null ||
		log "adding $SERVER to $IFACE failed"
	# The DHCP server binds the interface when it starts.  unudhcpd.usb0 is a
	# boot service, so on this port it usually starts before usb0 exists and
	# keeps a dead socket; restart it once the real netdev is present.
	rc-service "$DHCP_SERVICE" restart >/dev/null 2>&1 ||
		log "restart of $DHCP_SERVICE failed"
	log "configured $IFACE"
}

enable_link_only()
{
	# Tethering on this port is served entirely from the board side: the
	# image ships /etc/samurai/usb-dhcp.conf (dnsmasq, 10.42.0.1/24) and
	# nftables rules for usb* interfaces.  NetworkManager cannot be the owner
	# here because its ethernet profiles only activate once carrier is 1,
	# while carrier requires usb0 to be UP - a deadlock that left the port
	# with 0 received bytes and no address at all.
	#
	# Board owns the link and both addresses:
	#   172.16.42.1/24 is only added in developer mode (unudhcpd's subnet);
	#   169.254.42.1/16 is the out-of-band maintenance path and is kept in
	#   every NCM mode, so a mode switch can never strand the device.
	ip link set "$IFACE" up 2>/dev/null ||
		log "ip link set $IFACE up failed in mode $mode"
	have_linklocal || ip addr add "$LINKLOCAL/16" dev "$IFACE" 2>/dev/null ||
		log "adding $LINKLOCAL to $IFACE failed in mode $mode"
	ip -4 addr show dev "$IFACE" 2>/dev/null | grep -q "inet $TETHER_ADDR/24 " ||
		ip addr add "$TETHER_ADDR/24" dev "$IFACE" 2>/dev/null ||
		log "adding $TETHER_ADDR to $IFACE failed in mode $mode"
	command -v nmcli >/dev/null 2>&1 &&
		nmcli device set "$IFACE" managed no >/dev/null 2>&1 ||
		true
	start_tether_dhcp
	log "tethering link ready on $IFACE ($TETHER_ADDR, $LINKLOCAL)"
}

link_is_up()
{
	ip link show "$IFACE" 2>/dev/null | grep -q "<[^>]*UP[^>]*>"
}

have_server()
{
	ip -4 addr show dev "$IFACE" 2>/dev/null |
		grep -q "inet $SERVER/24 "
}

generation=""
last_carrier=""
last_mode=""
# Seed from the persisted state so a respawn still knows the previous owner.
if [ -r "$STATE_FILE" ]; then
	last_mode=$(cat "$STATE_FILE" 2>/dev/null || true)
fi
iterations=0

while :; do
	if [ "$MAX_ITERATIONS" -gt 0 ] &&
		[ "$iterations" -ge "$MAX_ITERATIONS" ]; then
		log "iteration limit $MAX_ITERATIONS reached"
		exit 0
	fi
	iterations=$((iterations + 1))
	if ! wait_for_iface; then
		last_mode=""
		sleep 5
		continue
	fi

	mode=$(current_mode)

	# Mode transitions change who owns usb0.  Hand it back to NetworkManager
	# before leaving developer mode, otherwise tethering's shared profile
	# can never activate and 172.16.42.1 would linger on the interface.
	if [ -n "$last_mode" ] && [ "$last_mode" != "$mode" ]; then
		log "mode $last_mode -> $mode"
		case $mode in
		developer) ;;
		*)
			if [ "$last_mode" = developer ] &&
				command -v nmcli >/dev/null 2>&1; then
				nmcli device set "$IFACE" managed yes >/dev/null 2>&1 ||
					log "could not return $IFACE to NetworkManager"
			fi
			;;
		esac
		# Force a full reconfigure for the new owner.
		generation=""
	fi
	last_mode=$mode
	mkdir -p "${STATE_FILE%/*}" 2>/dev/null || true
	printf '%s\n' "$mode" >"$STATE_FILE" 2>/dev/null || true

	# usb-signaller rebinding a gadget recreates the netdev.  Track the
	# kernel object identity, not just the name.
	real=$(readlink -f "$SYSFS/class/net/$IFACE" 2>/dev/null || echo "$IFACE")
	if [ "$real" != "$generation" ]; then
		generation="$real"
		log "new netdev generation: $real (mode=$mode)"
		case $mode in
		developer)
			assert_unmanaged
			configure_developer
			ensure_dhcpd
			;;
		*)
			enable_link_only
			;;
		esac
	fi

	carrier=$(cat "$SYSFS/class/net/$IFACE/carrier" 2>/dev/null || echo 0)
	if [ "$carrier" != "$last_carrier" ]; then
		log "carrier=$carrier"
		last_carrier=$carrier
	fi

	if [ "$mode" != developer ]; then
		# Tethering and other modes: only guarantee the link is enabled.
		# A down link means carrier can never rise, so this is still
		# required; everything else is left to NetworkManager.
		link_is_up || ip link set "$IFACE" up 2>/dev/null ||
			log "re-raising $IFACE failed in mode $mode"
		sleep 10
		continue
	fi

	# Keep the invariants true on every pass.  A NetworkManager "managed yes"
	# override from the mode script, a suspend/resume cycle, or a failed
	# reconfiguration must not leave the port silently dead again.
	if [ "$carrier" = 0 ] || ! link_is_up || ! have_linklocal || ! have_server; then
		assert_unmanaged
		link_is_up || ip link set "$IFACE" up 2>/dev/null ||
			log "re-raising $IFACE failed"
		have_linklocal || ip addr add "$LINKLOCAL/16" dev "$IFACE" 2>/dev/null ||
			log "re-adding $LINKLOCAL to $IFACE failed"
		have_server || ip addr add "$SERVER/24" dev "$IFACE" 2>/dev/null ||
			log "re-adding $SERVER to $IFACE failed"
	fi
	ensure_dhcpd

	sleep 10
done
