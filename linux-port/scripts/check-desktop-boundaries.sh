#!/bin/sh
# Read-only check of the board/desktop package boundary on the device.
set -eu

failures=0
note()
{
	echo "ok: $*"
}
problem()
{
	echo "FAIL: $*" >&2
	failures=$((failures + 1))
}
has_file()
{
	apk info -L "$1" 2>/dev/null | grep -Fq "$2"
}

for pkg in samurai-platform samurai-platform-pulse samurai-desktop; do
	if apk info -e "$pkg" >/dev/null 2>&1; then
		note "package installed: $pkg"
	else
		problem "package missing: $pkg"
	fi
done

if apk info -e samurai-platform >/dev/null 2>&1; then
	for path in etc/phoc etc/phosh etc/pulse; do
		if has_file samurai-platform "$path"; then
			problem "samurai-platform contains desktop/audio adapter file: $path"
		fi
	done
	note "samurai-platform has no Phosh/Phoc/PulseAudio payload"
fi

if apk info -e samurai-platform-pulse >/dev/null 2>&1; then
	if has_file samurai-platform-pulse \
		etc/pulse/daemon.conf.d/90-samurai.conf; then
		note "PulseAudio adapter payload present"
	else
		problem "samurai-platform-pulse is missing its PulseAudio config"
	fi
fi

if apk info -e samurai-desktop >/dev/null 2>&1; then
	if has_file samurai-desktop usr/libexec/samurai-powerkey; then
		problem "retired samurai-powerkey bridge is still packaged"
	else
		note "retired samurai-powerkey bridge absent"
	fi
	if has_file samurai-desktop usr/libexec/samurai-tinydm-stop; then
		note "tinydm stale-session cleanup present"
	else
		problem "samurai-desktop is missing samurai-tinydm-stop"
	fi
	if has_file samurai-desktop etc/init.d/samurai-powerkey; then
		problem "retired samurai-powerkey service is still packaged"
	else
		note "retired samurai-powerkey service absent"
	fi
fi

udc=
if [ -e /sys/class/udc/a600000.usb ]; then
	udc=a600000.usb
else
	for candidate in /sys/class/udc/*; do
		[ -e "$candidate" ] || continue
		udc=${candidate##*/}
		break
	done
fi
if [ -n "$udc" ]; then
	note "mainline UDC present: $udc"
else
	problem "mainline UDC missing"
fi
set -- /sys/class/drm/card*-DSI-*
[ -e "$1" ] &&
	note "DSI DRM connector present" ||
	problem "DSI DRM connector missing"
set -- /sys/class/backlight/*/brightness
[ -e "$1" ] &&
	note "backlight class device present" ||
	problem "backlight class device missing"
test -d /usr/lib/udev/rules.d &&
	note "standard udev rules directory present" ||
	problem "standard udev rules directory missing"
for rule in 99-realme-rmx1931-sensors.rules 99-realme-rmx1931-haptics.rules; do
	if [ -f "/usr/lib/udev/rules.d/$rule" ]; then
		note "standard udev rule present: $rule"
	else
		problem "standard udev rule missing: $rule"
	fi
	if [ -f "/etc/udev/rules.d/$rule" ] &&
		cmp -s "/etc/udev/rules.d/$rule" "/usr/lib/udev/rules.d/$rule"; then
		echo "note: legacy /etc udev copy can be removed: $rule"
	fi
done
test -d /usr/share/alsa/ucm2/conf.d &&
	note "ALSA UCM directory present" ||
	problem "ALSA UCM directory missing"

if [ -e /usr/libexec/samurai-usb-sleep-guard ]; then
	problem "debug carrier guard is installed in production"
else
	note "debug carrier guard is absent"
fi
if [ -e /etc/samurai/sleep-inhibitor.conf ]; then
	problem "board sleep-inhibitor configuration is installed in production"
else
	note "board sleep-inhibitor configuration is absent"
fi
if [ -f /etc/sleep-inhibitor.conf ]; then
	if grep -q '^[[:space:]]*-[[:space:]]*path:[[:space:]]*ssh-session-open$' \
		/etc/sleep-inhibitor.conf &&
		grep -q '^[[:space:]]*-[[:space:]]*path:[[:space:]]*apk-running$' \
		/etc/sleep-inhibitor.conf; then
		note "official sleep-inhibitor plugins present"
	else
		problem "official sleep-inhibitor plugins missing"
	fi
else
	problem "official /etc/sleep-inhibitor.conf missing"
fi
if command -v rc-service >/dev/null 2>&1; then
	if rc-service sleep-inhibitor status >/dev/null 2>&1; then
		note "official sleep-inhibitor service running"
	else
		problem "official sleep-inhibitor service not running"
	fi
	if rc-service samurai-sleep-inhibitor status >/dev/null 2>&1; then
		problem "board samurai-sleep-inhibitor service still exists"
	else
		note "board samurai-sleep-inhibitor service retired"
	fi
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: $failures problem(s)" >&2
	exit 1
fi
echo "RESULT: desktop boundary check passed"
