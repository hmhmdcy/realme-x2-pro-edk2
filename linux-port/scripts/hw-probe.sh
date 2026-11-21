#!/bin/sh
# Read-only hardware probe for the Realme X2 Pro (RMX1931) port.
# Prints one section per interface so a missing driver shows up as an empty
# or absent block rather than a silent success.
set -u

pw() { printf '12345678\n' | sudo -S -p '' "$@"; }

section() { printf '\n===== %s =====\n' "$1"; }

section "kernel / os"
uname -a
cat /etc/os-release | grep -E '^(PRETTY_NAME|VERSION_ID)='
printf 'uptime: %s\n' "$(cut -d' ' -f1 /proc/uptime)"

section "failed units"
systemctl --failed --no-pager --no-legend

section "battery / charger"
for p in /sys/class/power_supply/*; do
    [ -e "$p" ] || continue
    printf '%-18s type=%-14s status=%-12s capacity=%-6s online=%s\n' \
        "$(basename "$p")" \
        "$(cat "$p/type" 2>/dev/null)" \
        "$(cat "$p/status" 2>/dev/null)" \
        "$(cat "$p/capacity" 2>/dev/null)" \
        "$(cat "$p/online" 2>/dev/null)"
done

section "thermal"
for t in /sys/class/thermal/thermal_zone*/temp; do
    [ -e "$t" ] || continue
    printf '%s %s mC\n' "$(basename "$(dirname "$t")")" "$(cat "$t")"
done | head -6

section "display / drm"
printf 'DSI-1 status=%s\n' "$(cat /sys/class/drm/card1-DSI-1/status 2>/dev/null)"
printf 'DSI-1 modes=%s\n' "$(head -2 /sys/class/drm/card1-DSI-1/modes 2>/dev/null | tr '\n' ' ')"
for b in /sys/class/backlight/*; do
    [ -e "$b" ] || continue
    printf 'backlight %s brightness=%s max=%s\n' \
        "$(basename "$b")" "$(cat "$b/brightness")" "$(cat "$b/max_brightness")"
done

section "touch / input"
for n in /sys/class/input/event*/device/name; do
    [ -e "$n" ] || continue
    printf '%-28s %s\n' "$(basename "$(dirname "$n")")" "$(cat "$n")"
done

section "wifi"
ip -br addr show wlan0 2>/dev/null
iw dev wlan0 info 2>/dev/null | sed -n '1,10p'
printf 'station signal: '
iw dev wlan0 link 2>/dev/null | grep -E 'signal|bitrate' | tr '\n' ' '
printf '\n'
nmcli -t -f DEVICE,STATE,CONNECTION dev status 2>/dev/null | grep wlan0

section "usb / ncm"
ip -br addr show usb0 2>/dev/null
pw systemctl is-active unudhcpd@usb0.service 2>/dev/null
cat /sys/class/udc/*/state 2>/dev/null

section "bluetooth"
pw systemctl is-active bluetooth
pw bluetoothctl show 2>/dev/null | grep -E 'Controller|Powered|Discoverable'
pw bluetoothctl devices 2>/dev/null | head -5

section "modem / gnss"
mmcli -L 2>/dev/null
pw mmcli -m any 2>/dev/null | grep -E 'state|powered|signal|operator' | head -6
pw systemctl is-active samurai-gnss-assist samurai-ssc samurai-radio 2>/dev/null

section "sensors"
pw systemctl is-active iio-sensor-proxy
for d in /sys/bus/iio/devices/iio:device*; do
    [ -e "$d/name" ] || continue
    printf '%-16s %s\n' "$(basename "$d")" "$(cat "$d/name")"
done

section "audio"
pw systemctl is-active pipewire pipewire-pulse wireplumber 2>/dev/null
for c in /sys/class/sound/card*; do
    [ -e "$c/id" ] || continue
    printf 'card %s id=%s\n' "$(basename "$c")" "$(cat "$c/id" 2>/dev/null)"
done
printf 'default sink: '
pw -u user sh -c 'cd ~; pactl get-default-sink 2>/dev/null || true'
printf '\n'

section "camera"
pw systemctl is-active samurai-camera-config 2>/dev/null
for v in /dev/video*; do
    [ -e "$v" ] || continue
    printf '%s\n' "$v"
done
pw sh -c 'media-ctl -p 2>/dev/null | grep -E "^-(entity|.*->)" | head -20' 2>/dev/null \
    || printf 'media-ctl not installed\n'
