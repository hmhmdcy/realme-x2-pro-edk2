#!/bin/sh
# Read-only checks for the board service boot-order hardening.
set -eu

failures=0
platform_version=
ok()
{
	echo "ok: $*"
}
bad()
{
	echo "FAIL: $*" >&2
	failures=$((failures + 1))
}
has()
{
	file=$1
	pattern=$2
	label=$3
	if [ -f "$file" ] && grep -Eq "$pattern" "$file"; then
		ok "$label"
	else
		bad "$label"
	fi
}
lacks()
{
	file=$1
	pattern=$2
	label=$3
	if [ -f "$file" ] && ! grep -Eq "$pattern" "$file"; then
		ok "$label"
	else
		bad "$label"
	fi
}

if command -v apk >/dev/null 2>&1; then
	versions=$(apk info -v 2>/dev/null || true)
	platform_version=$(printf '%s\n' "$versions" | \
		sed -n 's/^samurai-platform-//p' | head -n 1)
	echo "$versions" | grep -qxE 'samurai-platform-5-r(17|18|19|20|21|22|23)' &&
		ok 'a supported samurai-platform package is installed' ||
		bad 'a supported samurai-platform package is not installed'
	echo "$versions" | grep -qxE 'samurai-desktop-4-r(8|9|10|11)' &&
		ok 'a supported samurai-desktop package is installed' ||
		bad 'a supported samurai-desktop package is not installed'
fi

if [ "$platform_version" = "5-r20" ] || [ "$platform_version" = "5-r21" ] ||
	[ "$platform_version" = "5-r22" ] || [ "$platform_version" = "5-r23" ]; then
	lacks /etc/conf.d/networkmanager \
		'^rc_(need|use|after)=.*samurai-radio' \
		'NetworkManager is independent of samurai-radio'
	lacks /etc/conf.d/sshd \
		'^rc_(need|use|after)=.*samurai-usb' \
		'sshd is independent of samurai-usb'
	lacks /etc/conf.d/modemmanager \
		'^rc_need=.*samurai-radio' \
		'ModemManager does not hard-require samurai-radio'
	lacks /etc/init.d/samurai-usb \
		'before[[:space:]]+sshd' \
		'samurai-usb does not gate sshd startup'
	lacks /etc/init.d/samurai-radio \
		'before[[:space:]]+networkmanager' \
		'samurai-radio does not gate NetworkManager startup'
else
	has /etc/conf.d/networkmanager \
		'^rc_use="[^"]*samurai-radio' \
		'NetworkManager orders samurai-radio as a soft dependency'
	lacks /etc/conf.d/networkmanager \
		'^rc_need=.*samurai-radio' \
		'NetworkManager does not hard-require samurai-radio'
	has /etc/conf.d/sshd \
		'^rc_use="[^"]*samurai-usb' \
		'sshd orders samurai-usb as a soft dependency'
	lacks /etc/conf.d/sshd \
		'^rc_need=.*samurai-usb' \
		'sshd does not hard-require samurai-usb'
fi

lacks /etc/conf.d/wpa_supplicant \
	'^rc_(need|use|after)=.*samurai-radio' \
	'wpa_supplicant uses the official base-ui ordering'

if [ -f /etc/conf.d/tinydm ]; then
	lacks /etc/conf.d/tinydm \
		'^rc_(need|use|after)=.*(samurai-sleep-inhibitor|iio-sensor-proxy)' \
		'tinydm has no board debug dependencies'
fi
lacks /etc/conf.d/tinydm \
	'^rc_need=.*iio-sensor-proxy' \
	'tinydm does not hard-require SensorProxy'
lacks /etc/conf.d/tinydm \
	'^rc_need=.*(bluetooth|modemmanager|samurai-sleep-inhibitor)' \
	'tinydm does not hard-require optional radio or sleep services'
lacks /etc/conf.d/tinydm \
	'^rc_after=.*(bluetooth|modemmanager)' \
	'tinydm does not wait for Bluetooth or ModemManager enumeration'
if [ -f /etc/sleep-inhibitor.conf ]; then
	grep -q '^[[:space:]]*-[[:space:]]*path:[[:space:]]*ssh-session-open$' \
		/etc/sleep-inhibitor.conf &&
		ok 'official sleep-inhibitor keeps the SSH-session lock' ||
		bad 'official sleep-inhibitor is missing ssh-session-open'
	grep -q '^[[:space:]]*-[[:space:]]*path:[[:space:]]*apk-running$' \
		/etc/sleep-inhibitor.conf &&
		ok 'official sleep-inhibitor keeps the apk lock' ||
		bad 'official sleep-inhibitor is missing apk-running'
	if grep -q 'samurai-usb-sleep-guard' /etc/sleep-inhibitor.conf; then
		bad 'debug USB carrier guard is enabled in production'
	else
		ok 'debug USB carrier guard is not enabled'
	fi
else
	bad 'official /etc/sleep-inhibitor.conf missing'
fi
if [ -e /etc/samurai/sleep-inhibitor.conf ] ||
	[ -e /usr/libexec/samurai-usb-sleep-guard ]; then
	bad 'board debug sleep policy is still installed'
else
	ok 'board debug sleep policy is absent'
fi

has /etc/init.d/iio-sensor-proxy \
	'use samurai-ssc' \
	'SensorProxy treats samurai-ssc as a soft dependency'
lacks /etc/init.d/iio-sensor-proxy \
	'need[[:space:]]+dbus[[:space:]]+samurai-ssc|need[[:space:]]+samurai-ssc' \
	'SensorProxy does not hard-require samurai-ssc'

has /usr/sbin/samurai-usb \
	'modprobe socinfo' \
	'samurai-usb loads the standard socinfo driver on demand'
has /usr/sbin/samurai-usb \
	'SAMURAI_USB_SERIAL_WAIT:-60' \
	'samurai-usb keeps a bounded 60-second serial wait'
has /etc/samurai/usb-dhcp.conf \
	'^dhcp-range=10\.42\.0\.2,10\.42\.0\.10,' \
	'USB NCM DHCP range is configured'
has /etc/samurai/usb-dhcp.conf \
	'^dhcp-option=121,169\.254\.42\.1/32,10\.42\.0\.1$' \
	'USB NCM keeps the legacy 169.254.42.1 route'
has /usr/sbin/samurai-usb \
	'start_dhcp' \
	'samurai-usb owns the DHCP lifecycle'
has /usr/sbin/samurai-wifi \
	'SAMURAI_WIFI_SOURCE_WAIT:-120' \
	'samurai-wifi keeps a bounded 120-second source wait'
has /usr/sbin/samurai-wifi \
	'SAMURAI_WIFI_WLAN_WAIT:-120' \
	'samurai-wifi keeps a bounded 120-second WLAN wait'
has /usr/sbin/samurai-wifi \
	'SAMURAI_WIFI_STATE_WAIT:-45' \
	'samurai-wifi replaces the fixed post-start soak with a bounded state poll'
has /usr/sbin/samurai-ssc \
	'monotonic\(\) \+ 90' \
	'samurai-ssc keeps a bounded 90-second FastRPC wait'
has /usr/sbin/samurai-ssc \
	'wait_qrtr_service\(400' \
	'samurai-ssc waits for the standard QRTR SSC service'
lacks /usr/sbin/samurai-ssc \
	'time\.sleep\(20\)' \
	'samurai-ssc has no fixed 20-second readiness sleep'
has /usr/sbin/samurai-bluetooth \
	'SAMURAI_BT_BOOT_MIN_UPTIME' \
	'bluetooth boot isolation is opt-in and bounded'
lacks /usr/sbin/samurai-bluetooth \
	'sleep[[:space:]]+10' \
	'bluetooth boot has no fixed 10-second sleep'
has /etc/init.d/samurai-radio \
	'wifi-boot-failure\.log' \
	'samurai-radio persists a failed bootstrap log'

if command -v rc-service >/dev/null 2>&1; then
	for service in networkmanager sshd samurai-radio samurai-ssc \
		samurai-usb iio-sensor-proxy tinydm sleep-inhibitor; do
		if rc-service "$service" status >/dev/null 2>&1; then
			ok "service started: $service"
		else
			bad "service not started: $service"
		fi
	done
fi

if [ -e /sys/class/udc/a600000.usb/state ]; then
	udc=$(cat /sys/class/udc/a600000.usb/state)
	[ "$udc" = configured ] &&
		ok 'USB NCM UDC configured' ||
		bad "USB NCM UDC state: $udc"
	carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || true)
	[ "$carrier" = 1 ] &&
		ok 'USB NCM carrier up' ||
		bad "USB NCM carrier: ${carrier:-missing}"
	ip -4 addr show dev usb0 2>/dev/null | grep -q 'inet 10.42.0.1/24 ' &&
		ok 'USB NCM DHCP address present' ||
		bad 'USB NCM DHCP address missing'
	pgrep -x dnsmasq >/dev/null 2>&1 &&
		ok 'USB NCM dnsmasq running' ||
		bad 'USB NCM dnsmasq not running'
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: $failures problem(s)" >&2
	exit 1
fi
echo "RESULT: boot service boundary check passed"
