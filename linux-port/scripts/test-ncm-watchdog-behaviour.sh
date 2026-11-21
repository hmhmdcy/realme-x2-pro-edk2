#!/bin/sh
# Exercise the watchdog's decision logic against a fake sysfs/configfs tree.
#
# It stubs `ip`, `nmcli`, `rc-service`, `readlink` and `sleep`, then runs
# samurai-ncm-watchdog.sh for a fixed number of iterations.  The resulting
# fake "ip" command log is the evidence: which ip operations ran for each
# gadget mode.
#
# This is an offline logic test, not hardware acceptance.

set -eu

script=${1:?usage: $0 WATCHDOG_SCRIPT}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

sysfs=$work/sys
configfs=$work/configfs
bin=$work/bin
mkdir -p "$sysfs/class/net" "$configfs" "$bin"

for mode in developer tethering mtp; do
	mkdir -p "$configfs/usb-signaller-$mode"
	printf '\n' > "$configfs/usb-signaller-$mode/UDC"
done

# Fake usb0: the symlink target stands in for the kernel object identity.
mkdir -p "$sysfs/kobj/usb0-1"
ln -s "$sysfs/kobj/usb0-1" "$sysfs/class/net/usb0"
printf '0\n' > "$sysfs/kobj/usb0-1/carrier"

# ip: log every call, and model `addr show` / `link show` from state files.
cat > "$bin/ip" <<'IP'
#!/bin/sh
root=$SAMURAI_TEST_SYSFS
echo "ip $*" >> "$SAMURAI_TEST_LOG"
case "$1" in
link)
	case "$2" in
	set)
		echo UP > "$root/link-state"
		;;
	show)
		state=$(cat "$root/link-state" 2>/dev/null || echo DOWN)
		if [ "$state" = UP ]; then
			echo "2: usb0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500"
		else
			echo "2: usb0: <BROADCAST,MULTICAST> mtu 1500"
		fi
		;;
	esac
	;;
addr)
	case "$2" in
	show)
		for entry in $(cat "$root/addr-list" 2>/dev/null); do
			echo "    inet $entry"
		done
		;;
	add)
		printf '%s\n' "$3" >> "$root/addr-list"
		;;
	esac
	;;
esac
IP

cat > "$bin/nmcli" <<'NM'
#!/bin/sh
echo "nmcli $*" >> "$SAMURAI_TEST_LOG"
NM

cat > "$bin/rc-service" <<'RC'
#!/bin/sh
echo "rc-service $*" >> "$SAMURAI_TEST_LOG"
RC

cat > "$bin/readlink" <<'RL'
#!/bin/sh
# Only used for -f on the fake netdev; let the real command handle the rest.
exec /bin/readlink "$@"
RL

cat > "$bin/sleep" <<'SL'
#!/bin/sh
SL

chmod +x "$bin"/*
export PATH=$bin:$PATH
export SAMURAI_TEST_LOG=$work/calls.log
export SAMURAI_TEST_SYSFS=$sysfs
: > "$SAMURAI_TEST_LOG"

# Bind one gadget and run the watchdog to completion.
bind_mode()
{
	for mode in developer tethering mtp; do
		printf '\n' > "$configfs/usb-signaller-$mode/UDC"
	done
	printf 'a600000.usb\n' > "$configfs/usb-signaller-$1/UDC"
}

run_once()
{
	: > "$SAMURAI_TEST_LOG"
	: > "$sysfs/addr-list"
	rm -f "$sysfs/link-state"
	SAMURAI_SYSFS=$sysfs \
	SAMURAI_CONFIGFS=$configfs \
	SAMURAI_NCM_LOG=$work/watchdog.log \
	SAMURAI_NCM_ITERATIONS=1 \
	SAMURAI_NCM_WAIT=1 \
	SAMURAI_NCM_STATE=$work/mode \
	sh "$script"
}

expect()
{
	desc=$1
	pattern=$2
	if grep -q -- "$pattern" "$SAMURAI_TEST_LOG"; then
		echo "OK   $desc"
	else
		echo "FAIL $desc (missing: $pattern)"
		echo "--- calls ---"
	cat "$SAMURAI_TEST_LOG"
		return 1
	fi
}

expect_absent()
{
	desc=$1
	pattern=$2
	if grep -q -- "$pattern" "$SAMURAI_TEST_LOG"; then
		echo "FAIL $desc (unexpected: $pattern)"
		return 1
	fi
	echo "OK   $desc"
}

rc=0

echo "== developer mode =="
bind_mode developer
run_once
expect "link is raised" "ip link set usb0 up" || rc=1
expect "link-local address added" "ip addr add 169.254.42.1/16" || rc=1
expect "server address added" "ip addr add 172.16.42.1/24" || rc=1
expect "usb0 taken from NetworkManager" "nmcli device set usb0 managed no" || rc=1
expect "unudhcpd restarted" "rc-service unudhcpd.usb0 restart" || rc=1

echo "== tethering mode =="
bind_mode tethering
run_once
expect "link is raised" "ip link set usb0 up" || rc=1
expect "link-local kept for maintenance" "ip addr add 169.254.42.1/16" || rc=1
expect "tethering subnet published" "ip addr add 10.42.0.1/24" || rc=1
expect_absent "developer address not added" "ip addr add 172.16.42.1/24" || rc=1
expect "NetworkManager kept out of the way" "nmcli device set usb0 managed no" || rc=1
expect_absent "no unudhcpd restart" "rc-service unudhcpd.usb0" || rc=1

echo "== mode transition developer -> tethering =="
bind_mode developer
SAMURAI_SYSFS=$sysfs SAMURAI_CONFIGFS=$configfs \
	SAMURAI_NCM_LOG=$work/watchdog.log SAMURAI_NCM_ITERATIONS=1 \
	SAMURAI_NCM_WAIT=1 SAMURAI_NCM_STATE=$work/mode sh "$script" >/dev/null
bind_mode tethering
: > "$SAMURAI_TEST_LOG"
SAMURAI_SYSFS=$sysfs SAMURAI_CONFIGFS=$configfs \
	SAMURAI_NCM_LOG=$work/watchdog.log SAMURAI_NCM_ITERATIONS=2 \
	SAMURAI_NCM_WAIT=1 SAMURAI_NCM_STATE=$work/mode sh "$script" >/dev/null
expect "board takes over after developer" "nmcli device set usb0 managed no" || rc=1

echo ""
if [ "$rc" -eq 0 ]; then
	echo "RESULT: PASS - developer and tethering both keep an addressable usb0"
else
	echo "RESULT: FAIL"
fi
exit $rc
