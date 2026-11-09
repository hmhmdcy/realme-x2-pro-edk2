#!/bin/sh
# Read-only Plasma Mobile and board-interface inventory.
set -u

failures=0
ok()
{
	echo "ok: $*"
}
bad()
{
	echo "FAIL: $*" >&2
	failures=$((failures + 1))
}
note()
{
	echo "note: $*"
}

user=cy122
uid=$(awk -F: -v user="$user" '$1 == user { print $3; exit }' /etc/passwd)
home=$(awk -F: -v user="$user" '$1 == user { print $6; exit }' /etc/passwd)
[ -n "${uid:-}" ] || {
	echo "FAIL: local user $user is missing" >&2
	exit 1
}
runtime=/run/user/$uid
session_pid=$(pgrep -u "$uid" -x plasmashell 2>/dev/null | tail -n 1)
[ -n "$session_pid" ] ||
	session_pid=$(pgrep -u "$uid" -x kwin_wayland 2>/dev/null | tail -n 1)
wayland=
bus_address=
if [ -n "$session_pid" ] && [ -r "/proc/$session_pid/environ" ]; then
	while IFS='=' read -r key value; do
		case $key in
		WAYLAND_DISPLAY) wayland=$value ;;
		DBUS_SESSION_BUS_ADDRESS) bus_address=$value ;;
		esac
	done <<-EOF
	$(tr '\0' '\n' <"/proc/$session_pid/environ")
	EOF
fi
[ -n "$wayland" ] ||
	wayland=$(basename "$(ls -d "$runtime"/wayland-[0-9]* 2>/dev/null | head -n 1)" 2>/dev/null || true)
[ -n "$wayland" ] || wayland=wayland-0

run_user()
{
	if [ -n "$bus_address" ]; then
		runuser -u "$user" -- env \
			HOME="$home" USER="$user" LOGNAME="$user" \
			XDG_RUNTIME_DIR="$runtime" \
			WAYLAND_DISPLAY="$wayland" \
			DBUS_SESSION_BUS_ADDRESS="$bus_address" \
			DISPLAY="${DISPLAY:-:0}" \
			"$@"
	else
		runuser -u "$user" -- env \
			HOME="$home" USER="$user" LOGNAME="$user" \
			XDG_RUNTIME_DIR="$runtime" \
			WAYLAND_DISPLAY="$wayland" \
			DISPLAY="${DISPLAY:-:0}" \
			"$@"
	fi
}

for proc in kwin_wayland plasmashell; do
	count=$(pgrep -u "$uid" -x "$proc" 2>/dev/null | wc -l)
	if [ "$count" -eq 1 ]; then
		ok "single $proc instance"
	else
		bad "expected one $proc instance, found $count"
	fi
done
if pgrep -u "$uid" -f '/org_kde_powerdevil' >/dev/null 2>&1; then
	ok "org_kde_powerdevil running"
else
	bad "org_kde_powerdevil not running"
fi
powerkey_count=$(pgrep -f '^python3 /usr/libexec/samurai-powerkey$' 2>/dev/null |
	wc -l)
if [ "$powerkey_count" -eq 1 ]; then
	ok "single samurai-powerkey instance"
else
	bad "expected one samurai-powerkey instance, found $powerkey_count"
fi
if rc-service samurai-powerkey status >/dev/null 2>&1; then
	ok "samurai-powerkey service running"
else
	bad "samurai-powerkey service is not running"
fi
if grep -q 'grabbed .*power-key handling' /var/log/samurai-powerkey.log \
	2>/dev/null; then
	ok "exclusive power-key event grab"
else
	bad "power-key event device was not grabbed"
fi

if [ -S "$runtime/$wayland" ]; then
	ok "Wayland socket $runtime/$wayland"
else
	bad "Wayland socket missing ($runtime/$wayland)"
fi
seat_sessions=$(loginctl list-sessions --no-legend 2>/dev/null |
	awk -v uid="$uid" '$2 == uid && $4 == "seat0" { count++ } END { print count + 0 }')
if [ "$seat_sessions" -eq 1 ]; then
	ok "single active seat session"
else
	bad "expected one active seat session, found $seat_sessions"
fi

if run_user kscreen-doctor -o >/tmp/samurai-kscreen.out 2>/tmp/samurai-kscreen.err; then
	ok "KScreen output query"
	grep -q 'enabled' /tmp/samurai-kscreen.out &&
		ok "KScreen output enabled" || bad "KScreen output not enabled"
	grep -q 'Brightness control:.*supported' /tmp/samurai-kscreen.out &&
		ok "KScreen brightness control" ||
		note "KScreen does not report brightness control in this frame"
	if run_user kscreen-doctor --dpms show >/tmp/samurai-dpms.out 2>&1 &&
		grep -q 'screen DSI-1: on' /tmp/samurai-dpms.out; then
		ok "DSI-1 DPMS on"
	elif [ "${SAMURAI_ALLOW_DPMS_OFF:-0}" = 1 ] &&
		grep -q 'screen DSI-1: off' /tmp/samurai-dpms.out; then
		note "DSI-1 DPMS off (intentional; SAMURAI_ALLOW_DPMS_OFF=1)"
	else
		bad "DSI-1 DPMS is not on"
	fi
else
	bad "KScreen output query failed"
fi

if command -v gdbus >/dev/null 2>&1; then
	for pair in \
		'org.freedesktop.portal.Desktop /org/freedesktop/portal/desktop' \
		'org.freedesktop.impl.portal.desktop.kde /org/freedesktop/portal/desktop'; do
		set -- $pair
		if run_user gdbus introspect --session --dest "$1" --object-path "$2" >/dev/null 2>&1; then
			ok "portal $1"
		else
			bad "portal $1 unavailable"
		fi
	done
fi

for name in \
	sm.puri.Chatty \
	org.gnome.Calls \
	org.ofono.mms \
	org.mobian_project.CallAudio \
	org.sigxcpu.Feedback; do
	if run_user gdbus call --session \
		--dest org.freedesktop.DBus \
		--object-path /org/freedesktop/DBus \
		--method org.freedesktop.DBus.NameHasOwner \
		"$name" 2>/dev/null | grep -q 'true'; then
		ok "session D-Bus name $name"
	else
		bad "session D-Bus name missing: $name"
	fi
done

modem_attempt=0
while [ "$modem_attempt" -lt 35 ]; do
	mmcli -L 2>/dev/null | grep -q '/Modem/' && break
	modem_attempt=$((modem_attempt + 1))
	[ "$modem_attempt" -lt 35 ] && sleep 1
done
if mmcli -L 2>/dev/null | grep -q '/Modem/'; then
	ok "ModemManager modem object"
else
	bad "ModemManager modem object missing after 35s"
fi
modemmanager_count=$(pgrep -x ModemManager 2>/dev/null | wc -l)
if [ "$modemmanager_count" -eq 1 ]; then
	ok "single ModemManager instance"
else
	bad "expected one ModemManager instance, found $modemmanager_count"
fi
if grep -q '^Exec=/bin/false$' \
	/usr/local/share/dbus-1/system-services/org.freedesktop.ModemManager1.service \
	2>/dev/null; then
	ok "ModemManager D-Bus activation masked"
else
	bad "ModemManager D-Bus activation is not masked"
fi
if nmcli device status >/dev/null 2>&1; then
	ok "NetworkManager CLI"
else
	bad "NetworkManager CLI unavailable"
fi
if command -v upower >/dev/null 2>&1 &&
	upower -e 2>/dev/null | grep -q '/battery_'; then
	ok "UPower battery interface"
else
	bad "UPower battery interface missing"
fi
if command -v powerprofilesctl >/dev/null 2>&1 &&
	powerprofilesctl get >/dev/null 2>&1; then
	ok "PowerProfiles interface"
else
	bad "PowerProfiles interface missing"
fi
if command -v bluetoothctl >/dev/null 2>&1 &&
	bluetoothctl show >/dev/null 2>&1; then
	ok "BlueZ controller query"
else
	bad "BlueZ controller query failed"
fi
if gdbus call --system \
	--dest org.freedesktop.GeoClue2 \
	--object-path /org/freedesktop/GeoClue2/Manager \
	--method org.freedesktop.DBus.Properties.GetAll \
	org.freedesktop.GeoClue2.Manager >/dev/null 2>&1; then
	ok "GeoClue manager interface"
else
	bad "GeoClue manager interface missing"
fi
if run_user gdbus call --session \
	--dest org.freedesktop.portal.Desktop \
	--object-path /org/freedesktop/portal/desktop \
	--method org.freedesktop.DBus.Properties.Get \
	org.freedesktop.portal.Location version 2>/dev/null | grep -q 'uint32'; then
	ok "location portal interface"
else
	bad "location portal interface missing"
fi

for path in /sys/bus/iio/devices /sys/class/input; do
	[ -d "$path" ] && ok "kernel interface $path" ||
		bad "kernel interface missing: $path"
done
touchscreen=0
haptics=0
for event in /sys/class/input/event*; do
	[ -e "$event" ] || continue
	props=$(udevadm info -q property -p "$event" 2>/dev/null || true)
	case "$props" in
	*ID_INPUT_TOUCHSCREEN=1*) touchscreen=1 ;;
	esac
	case "$props" in
	*FEEDBACKD_TYPE=vibra*) haptics=1 ;;
	esac
done
[ "$touchscreen" -eq 1 ] && ok "touchscreen udev interface" ||
	bad "touchscreen udev interface missing"
[ "$haptics" -eq 1 ] && ok "haptics feedbackd interface" ||
	bad "haptics feedbackd interface missing"
if pgrep -f '/iio-sensor-proxy' >/dev/null 2>&1; then
	ok "iio-sensor-proxy running"
else
	bad "iio-sensor-proxy not running"
fi
if gdbus call --system \
	--dest net.hadess.SensorProxy \
	--object-path /net/hadess/SensorProxy \
	--method org.freedesktop.DBus.Properties.GetAll \
	net.hadess.SensorProxy 2>/dev/null | grep -q "'HasAccelerometer': <true>"; then
	ok "sensor proxy accelerometer interface"
else
	bad "sensor proxy accelerometer interface missing"
fi
if command -v feedbackd >/dev/null 2>&1; then
	pgrep -f '/feedbackd' >/dev/null 2>&1 &&
		ok "feedbackd running" || bad "feedbackd not running"
fi

if run_user pactl info >/tmp/samurai-pactl.out 2>/tmp/samurai-pactl.err; then
	ok "PulseAudio-compatible control socket"
	note "$(sed -n 's/^Default Sink:[[:space:]]*//p' /tmp/samurai-pactl.out | head -n 1)"
else
	note "pactl unavailable; check PipeWire session manager directly"
fi
if command -v wpctl >/dev/null 2>&1 &&
	run_user wpctl status >/dev/null 2>&1; then
	ok "WirePlumber/PipeWire status"
fi

for service in samurai-usb sleep-inhibitor samurai-radio modemmanager bluetooth; do
	if [ ! -x "/etc/init.d/$service" ]; then
		bad "OpenRC service missing: $service"
	elif rc-service "$service" status >/dev/null 2>&1; then
		ok "OpenRC $service running"
	else
		bad "OpenRC $service not running"
	fi
done
if rc-service samurai-sleep-inhibitor status >/dev/null 2>&1; then
	bad "board samurai-sleep-inhibitor still exists"
else
	ok "board samurai-sleep-inhibitor is retired"
fi
if [ -e /usr/libexec/samurai-usb-sleep-guard ]; then
	bad "debug USB carrier guard is installed in production"
else
	ok "debug USB carrier guard is absent"
fi

for stale in phosh phoc; do
	if pgrep -f "/usr/bin/$stale" >/dev/null 2>&1; then
		bad "stale $stale process"
	else
		ok "no $stale process"
	fi
done
if command -v rc-service >/dev/null 2>&1 &&
	rc-service greetd status >/dev/null 2>&1; then
	bad "greetd is still running"
else
	ok "greetd is not running"
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: $failures Plasma/board check(s) failed" >&2
	exit 1
fi
echo "RESULT: Plasma Mobile/board check passed"
