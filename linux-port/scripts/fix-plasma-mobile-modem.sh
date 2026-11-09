#!/bin/sh
# Start ModemManager only after the samurai radio stack is ready.
# Run as root on the device.
set -eu

if [ "$(id -u)" -ne 0 ]; then
	echo "run as root" >&2
	exit 1
fi

conf=/etc/conf.d/modemmanager
override=/usr/local/share/dbus-1/system-services/org.freedesktop.ModemManager1.service
stamp=$(date +%Y%m%d-%H%M%S)
backup=/root/pre-modemmanager-order-$stamp

if ! rc-service samurai-radio status >/dev/null 2>&1; then
	echo "samurai-radio is not started; refusing to start ModemManager early" >&2
	exit 1
fi

mkdir -p "$backup"
cp -a "$conf" "$backup/modemmanager.conf"
if [ -f "$override" ]; then
	cp -a "$override" "$backup/org.freedesktop.ModemManager1.service"
fi

# rc_need augments the init script's existing "need dbus polkit" dependency.
if ! grep -q '^rc_need=.*samurai-radio' "$conf"; then
	if grep -q '^rc_need=' "$conf"; then
		sed -i 's/^rc_need="\(.*\)"$/rc_need="\1 samurai-radio"/' "$conf"
	else
		printf '\n# Wait for the board radio/QRTR services before probing.\nrc_need="samurai-radio"\n' >> "$conf"
	fi
fi

if ! grep -q '^rc_need=.*samurai-radio' "$conf"; then
	echo "failed to add samurai-radio dependency to $conf" >&2
	exit 1
fi

# Older revisions installed a permanent /usr/local D-Bus override with
# Exec=/bin/false. That hides the standard activation file and breaks any
# later manual or desktop-initiated activation. The OpenRC rc_need above is
# the only ordering mechanism needed at boot.
if [ -f "$override" ]; then
	if grep -q '^Exec=/bin/false$' "$override"; then
		rm -f "$override"
		pkill -HUP -u root -x dbus-daemon 2>/dev/null || true
		echo "removed legacy /bin/false D-Bus override"
	else
		echo "warning: leaving unknown local override in place: $override" >&2
	fi
fi

rc-update add modemmanager default >/dev/null
if ! rc-service modemmanager status >/dev/null 2>&1; then
	rc-service modemmanager start
fi

attempt=0
while [ "$attempt" -lt 30 ]; do
	if mmcli -L 2>/dev/null | grep -q '/Modem/'; then
		break
	fi
	attempt=$((attempt + 1))
	sleep 1
done

if ! mmcli -L 2>/dev/null | grep -q '/Modem/'; then
	echo "ModemManager started but did not enumerate a modem" >&2
	echo "backup: $backup" >&2
	exit 1
fi

if [ ! -f "$override" ]; then
	printf 'standard D-Bus activation: '
	if [ -f /usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service ]; then
		echo "available"
	else
		echo "missing system service file" >&2
		exit 1
	fi
fi

echo "ModemManager is ordered after samurai-radio and enumerated:"
mmcli -L
echo "backup: $backup"
