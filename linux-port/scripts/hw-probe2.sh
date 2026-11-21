#!/bin/sh
# Second-pass probe: things the first pass could only report as "unknown".
set -u
pw() { printf '12345678\n' | sudo -S -p '' "$@"; }

echo "===== sensors (as logged-in user) ====="
export XDG_RUNTIME_DIR=/run/user/10000
timeout 8 monitor-sensor 2>&1 | head -12

echo "===== iio devices ====="
for d in /sys/bus/iio/devices/iio:device*; do
    [ -e "$d/name" ] || continue
    printf '%-16s %s\n' "$(basename "$d")" "$(cat "$d/name")"
done

echo "===== bluetooth scan ====="
pw bluetoothctl --timeout 10 scan on 2>&1 | head -12

echo "===== camera media graph ====="
pw media-ctl -p 2>&1 | head -70

echo "===== video nodes ====="
ls -l /sys/class/video4linux | awk '{print $9, $10, $11}' | head -20
