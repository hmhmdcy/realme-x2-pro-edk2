#!/bin/sh
# Driver + subsystem matrix: proves whether each interface is on a standard
# kernel/distro interface rather than a private shim.
set -u
pw() { printf '12345678\n' | sudo -S -p '' "$@"; }

drv() {
    # $1 = sysfs device path
    if [ -e "$1/driver" ]; then
        basename "$(readlink -f "$1/driver")"
    else
        echo "(no driver link)"
    fi
}

echo "== display =="
printf 'card: %s\n' "$(basename "$(readlink -f /sys/class/drm/card1/device/driver)")"
printf 'panel connector driver: %s\n' "$(drv /sys/class/drm/card1-DSI-1)"
pw sh -c 'cat /sys/kernel/debug/dri/1/name 2>/dev/null'

echo "== touch =="
printf 'driver: %s\n' "$(drv /sys/class/input/event3)"
pw sh -c 'cat /sys/class/input/event3/device/uevent 2>/dev/null | grep -E "PRODUCT|NAME"'

echo "== wifi =="
printf 'driver: %s\n' "$(drv /sys/class/net/wlan0/device)"
pw sh -c 'ethtool -i wlan0 2>/dev/null'

echo "== usb gadget =="
printf 'udc driver: %s\n' "$(drv /sys/class/udc/*)"
pw sh -c 'cat /sys/class/udc/*/uevent 2>/dev/null'

echo "== bluetooth =="
printf 'hci driver: %s\n' "$(drv /sys/class/bluetooth/hci0)"
pw sh -c 'btmon -t 2>/dev/null </dev/null | head -0'

echo "== modem =="
printf 'ipa driver: %s\n' "$(drv /sys/devices/platform/soc@0/1e40000.ipa)"

echo "== sensors =="
for d in /sys/bus/iio/devices/iio:device*; do
    [ -e "$d" ] || continue
    printf '%-12s name=%-28s driver=%s\n' \
        "$(basename "$d")" "$(cat "$d/name" 2>/dev/null)" "$(drv "$d")"
done
echo "-- sensor client driver (sensor core) --"
for d in /sys/bus/iio/devices/iio:device*; do
    [ -e "$d/name" ] || continue
    printf '%s %s\n' "$(basename "$d")" "$(cat "$d/name")"
done | grep -iE 'accel|light|prox|magn' || echo "(none matched by name)"

echo "== audio =="
printf 'sound card driver: %s\n' "$(drv /sys/class/sound/card0)"
pw sh -c 'cat /proc/asound/cards 2>/dev/null'

echo "== camera =="
pw sh -c 'ls /dev/v4l-subdev* 2>/dev/null | wc -l'
pw sh -c 'command -v media-ctl || echo media-ctl-missing'
if pw sh -c 'command -v media-ctl >/dev/null 2>&1'; then
    pw media-ctl -p 2>&1 | grep -E '-\s(entity|.*->)' | head -30
fi

echo "== charger / fuel gauge =="
for p in /sys/class/power_supply/*; do
    [ -e "$p/device" ] || continue
    printf '%-18s driver=%s\n' "$(basename "$p")" "$(drv "$p/device")"
done

echo "== flash led =="
pw sh -c 'ls /sys/class/leds 2>/dev/null | head -10'
