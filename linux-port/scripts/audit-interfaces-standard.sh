#!/bin/sh
# Interface audit: for every hardware block, report what the kernel
# actually exposes and whether it is a distribution-standard API
# (sysfs class, DRM/KMS, V4L2, IIO, BlueZ, NetworkManager, ALSA UCM) or a
# board-private path.  Read-only.
set -u

say() { printf '\n=== %s ===\n' "$*"; }
BAD=0
bad() { printf '  [private/absent] %s\n' "$*"; BAD=$((BAD + 1)); }

say "kernel / boot"
printf '  %s\n' "$(uname -r)"
printf '  cmdline: %s\n' "$(cat /proc/cmdline)"
printf '  initramfs in use: %s\n' \
	"$([ -e /etc/initrd-release ] && echo yes || echo no)"

say "display (DRM/KMS)"
for c in /sys/class/drm/card*-*/status; do
	[ -e "$c" ] || continue
	printf '  %s=%s\n' "${c%/status}" "$(cat "$c")"
done
ls /sys/class/backlight 2>/dev/null | sed 's/^/  backlight: /' ||
	bad 'no backlight class'

say "camera (V4L2 / media controller)"
printf '  media devices: %s\n' "$(ls /dev/media* 2>/dev/null | wc -l)"
printf '  video nodes:   %s\n' "$(ls /dev/video* 2>/dev/null | wc -l)"
# qcom-camss registers subdevices inside one platform device and wires the
# graph through DT `ports`, so /dev/v4l-subdev* may legitimately be empty;
# the real nodes are the msm_vfe*_video V4L2 devices plus /dev/media*.
printf '  v4l subdevs:   %s (camss builds its graph internally)\n' \
	"$(ls /dev/v4l-subdev* 2>/dev/null | wc -l)"
for s in /sys/bus/i2c/drivers/*/*; do
	case "${s##*/}" in
	# Only real I2C client addresses ("7-0010", "8-002d", ...); every
	# driver directory also holds bind/module/unbind/uevent entries, which
	# are not devices and used to be printed as bogus "sensor bound" rows.
	*[0-9]-[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F])
		case "$s" in
		*s5k3m5*|*imx319*|*imx471*|*s5kgw1*)
			printf '  sensor bound: %s\n' "${s##*/}" ;;
		esac ;;
	esac
done

say "sensors (IIO vs vendor SSC)"
printf '  iio devices: %s\n' "$(ls /sys/bus/iio/devices 2>/dev/null | wc -l)"
ls /sys/bus/iio/devices/*/name 2>/dev/null |
	while read -r f; do printf '    %s\n' "$(cat "$f")"; done
printf '  ssc daemon: %s\n' \
	"$(systemctl is-active samurai-ssc 2>/dev/null || echo n/a)"
# On this board the IMU and ALS are published by the SLPI sensor service
# and reached through libssc, so they never appear under /sys/bus/iio
# (that node holds only the three PMIC ADCs).  The distribution-standard
# interface for those is net.hadess.SensorProxy, which iio-sensor-proxy
# implements over libssc.  Counting IIO nodes alone would wrongly report
# the sensors as missing.
export DBUS_SYSTEM_BUS_ADDRESS="${DBUS_SYSTEM_BUS_ADDRESS:-unix:path=/run/dbus/system_bus_socket}"
if busctl --system get-property net.hadess.SensorProxy \
	/net/hadess/SensorProxy net.hadess.SensorProxy \
	HasAccelerometer HasAmbientLight HasProximity >/tmp/sensor-props 2>/dev/null
then
	while read -r line; do printf '  SensorProxy %s\n' "$line"; done \
		</tmp/sensor-props
# busctl prints one "b true|b false" line per property, in the order the
# properties were requested, but a bare "some line is true" test passes as
# soon as *any* sensor works.  Assert the full trio the board actually
# publishes: all three kernel/198/200 runs reported HasAccelerometer,
# HasAmbientLight and HasProximity = true, so a missing one is a regression.
for prop in HasAccelerometer HasAmbientLight HasProximity; do
	idx=$(printf '%s\n' HasAccelerometer HasAmbientLight HasProximity |
		grep -nx "$prop" | cut -d: -f1)
	value=$(sed -n "${idx}p" /tmp/sensor-props)
	[ "$value" = 'b true' ] ||
		bad "SensorProxy $prop is '$value' (expected b true)"
done
else
	bad 'net.hadess.SensorProxy is not reachable'
fi
rm -f /tmp/sensor-props

say "wifi (cfg80211 / NL80211)"
iface=$(ls /sys/class/net 2>/dev/null | grep -m1 wlan || true)
printf '  wlan iface: %s\n' "${iface:-none}"
[ -n "${iface:-}" ] && {
	printf '  regulatory: %s\n' "$(cat /sys/module/cfg80211/parameters/ieee80211_regdom 2>/dev/null || echo unset)"
	iw reg get 2>/dev/null | head -4 | sed 's/^/  /'
	printf '  driver: %s\n' \
		"$(basename "$(readlink -f /sys/class/net/$iface/device/driver 2>/dev/null)" 2>/dev/null)"
}
dmesg 2>/dev/null | grep -i -F 'failed to load regulatory' |
	sed 's/^/  /' | tail -2

say "bluetooth (BlueZ)"
printf '  adapter: %s\n' "$(ls /sys/class/bluetooth 2>/dev/null | head -3 | tr '\n' ' ')"
bluetoothctl show 2>/dev/null | grep -F -e Powered -e Name |
	sed 's/^/  /'

say "audio (ALSA UCM / PulseAudio)"
printf '  ucm dirs: %s\n' "$(ls /usr/share/alsa/ucm2/conf.d 2>/dev/null | wc -l)"
pactl info 2>/dev/null | grep -F -e 'Default Sink' -e 'Server Name' |
	sed 's/^/  /'

say "modem (ModemManager / QRTR)"
mmcli -L 2>/dev/null | sed 's/^/  /'

say "usb gadget (configfs UDC)"
printf '  udc: %s\n' "$(cat /sys/class/udc/*/state 2>/dev/null | head -1)"
printf '  usb0: %s\n' \
	"$(cat /sys/class/net/usb0/operstate 2>/dev/null || echo absent)"

say "touch / power / thermal"
printf '  touch: %s\n' \
	"$(grep -F -m1 -i 'Synaptics' /proc/bus/input/devices 2>/dev/null | cut -c1-80)"
printf '  thermal zones: %s\n' "$(ls /sys/class/thermal 2>/dev/null | grep -c thermal_zone)"

say "summary"
printf '  private-or-absent items: %s\n' "$BAD"
