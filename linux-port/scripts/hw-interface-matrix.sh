#!/bin/sh
# Per-interface matrix: is it working, and is it on the interface the
# distribution actually ships (mainline driver + standard userspace API),
# or does it depend on a private shim?
#
# "Standard" means: mainline kernel driver + the userspace API that
# postmarketOS/Alpine already ships (sysfs class, IIO, ALSA, LED class,
# rfkill, NetworkManager/ModemManager D-Bus, etc.).  A board package that
# only supplies glue (units, udev rules, firmware paths) keeps the interface
# standard; a board package that invents a new API does not.
set -u
pw() { printf '12345678\n' | sudo -S -p '' "$@"; }

drv() { # $1 = sysfs device dir
    [ -e "$1/driver" ] && basename "$(readlink -f "$1/driver")" || echo "-"
}

row() { printf '%-22s %-6s %-26s %s\n' "$1" "$2" "$3" "$4"; }
hdr() { printf '\n%-22s %-6s %-26s %s\n' INTERFACE STATE DRIVER STANDARD-API; }

hdr

# --- display -------------------------------------------------------------
dsi=$(cat /sys/class/drm/card1-DSI-1/status 2>/dev/null)
row display "$dsi" "$(drv /sys/class/drm/card1/device)" "DRM/KMS + backlight class"

# --- touch ---------------------------------------------------------------
tn=$(cat /sys/class/input/event3/device/name 2>/dev/null)
row touch "${tn:+ok}" "$(drv /sys/class/input/event3)" "input evdev (libinput)"

# --- wifi ----------------------------------------------------------------
wl=$(ip -br addr show wlan0 2>/dev/null | awk '{print $2}')
row wifi "${wl:+up}" "$(drv /sys/class/net/wlan0/device)" "cfg80211 + NetworkManager"

# --- bluetooth -----------------------------------------------------------
bt=$(pw systemctl is-active bluetooth 2>/dev/null)
row bluetooth "$bt" "hci0/wcn399x" "BlueZ D-Bus"

# --- usb gadget / ncm ----------------------------------------------------
u0=$(ip -br addr show usb0 2>/dev/null | awk '{print $2}')
row "usb-ncm" "${u0:+up}" "$(cat /sys/class/udc/*/uevent 2>/dev/null | sed -n 's/^USB_UDC_DRIVER=//p')" \
    "netdev + unudhcpd"

# --- audio ---------------------------------------------------------------
row audio "$(grep -c . /proc/asound/cards 2>/dev/null | tr -d '\n')card" \
    "$(sed -n 's/.*: ([^)]*) - .*/\1/p' /proc/asound/cards 2>/dev/null | head -1)" \
    "ALSA + PulseAudio"

# --- battery / charger ---------------------------------------------------
cap=$(cat /sys/class/power_supply/bq28z610-0/capacity 2>/dev/null)
row battery "${cap:+${cap}%}" "$(drv /sys/class/power_supply/bq28z610-0/device)" \
    "power_supply class + UPower"
row charger "$(cat /sys/class/power_supply/mp2650-input/online 2>/dev/null | sed 's/1/online/;s/0/offline/')" \
    "$(drv /sys/class/power_supply/mp2650-input/device)" "power_supply class"

# --- thermal -------------------------------------------------------------
# mC -> C with one decimal; truncating the string would print 293 for 29300.
tz=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)
if [ -n "${tz:-}" ]; then
    thermal_c=$(awk -v t="$tz" 'BEGIN { printf "%.1f", t/1000 }')
else
    thermal_c='?'
fi
row thermal "${thermal_c}C" "$(cat /sys/class/thermal/thermal_zone0/type 2>/dev/null)" \
    "thermal_zone sysfs"

# --- flash led -----------------------------------------------------------
row "flash-led" "$(ls /sys/class/leds/white:flash >/dev/null 2>&1 && echo ok)" \
    "$(drv /sys/class/leds/white:flash/device)" "LED class + flash_* attrs"

# --- modem ---------------------------------------------------------------
mm=$(pw mmcli -L 2>/dev/null | grep -c Modem)
row modem "${mm:+present}" "ipa,qrtr" "ModemManager D-Bus (qcom-soc)"

# --- gnss ----------------------------------------------------------------
row gnss "$(pw systemctl is-active samurai-gnss-assist 2>/dev/null)" \
    "samurai-gnss-assist" "ModemManager Location + NMEA"

# --- sensors -------------------------------------------------------------
iio=$(ls -d /sys/bus/iio/devices/iio:device* 2>/dev/null | wc -l)
accel=$(pw sh -c 'ssccli --debug --sensor accelerometer --timeout 2 2>/dev/null | grep -c "measurement"')
row sensors "iio=${iio}" \
    "SSC/SLPI only" "IIO (accel/light/prox) -- missing bridge"

# --- camera --------------------------------------------------------------
med=$(ls /dev/media* 2>/dev/null | wc -l)
sub=$(ls /dev/v4l-subdev* 2>/dev/null | wc -l)
camdrv=$(pw lsmod 2>/dev/null | grep -c '^qcom_camss')
row camera "media=${med} subdev=${sub}" "qcom_camss=${camdrv}" \
    "V4L2/media-controller -- pad links missing"

# --- haptics -------------------------------------------------------------
row haptics "$(ls /sys/class/input/ | grep -c . >/dev/null && \
    cat /sys/class/input/event1/device/name 2>/dev/null | grep -c AW8697)" \
    "aw8697-samurai" "input ff-memless (private driver)"

# --- headset / jack -------------------------------------------------------
jack=$(cat /sys/class/input/event4/device/name 2>/dev/null)
row jack "${jack:+ok}" "-" "ALSA jack kcontrol + input switch"

echo
echo "== notes =="
echo "  battery 'ok' is capacity read through power_supply, not gauge accuracy"
echo "  sensors: hardware proven via SSC readiness logs, but not exposed as IIO"
echo "  camera: 4 sensors bound, 0 pad links -> needs camss notifier fix in kernel"
