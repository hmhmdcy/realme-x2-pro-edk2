#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
test -n "$(pgrep -u 10000 -x phosh || true)"
test -S /run/user/10000/wayland-0
dest=/var/lib/samurai/k113-display-wake15
test ! -e "$dest" && test ! -e /tmp/k113-phosh-wake15-private.png
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-before.txt"
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 wlr-randr' > "$dest/output-before.txt"
set +e
timeout -s TERM -k 2 12 su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 wlr-randr --output DSI-1 --on' > "$dest/output-wake.txt" 2>&1
printf '%s\n' "$?" > "$dest/output-wake-exit.txt"
sleep 1
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 wlr-randr' > "$dest/output-after.txt" 2>&1
printf '%s\n' "$?" > "$dest/output-read-exit.txt"
timeout -s TERM -k 2 10 su -s /bin/sh cy122 -c 'umask 077; XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 grim /tmp/k113-phosh-wake15-private.png' > "$dest/screenshot.txt" 2>&1
printf '%s\n' "$?" > "$dest/screenshot-exit.txt"
if test -f /tmp/k113-phosh-wake15-private.png; then
    cp /tmp/k113-phosh-wake15-private.png "$dest/screenshot-private.png"
    chmod 600 "$dest/screenshot-private.png"
fi
set -e
dmesg > "$dest/dmesg-after.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-after.txt"
cat /sys/class/vtconsole/vtcon1/bind > "$dest/fbcon-after.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi-after.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-after.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-display-wake15.tar .
sha256sum /tmp/k113-display-wake15.tar
echo DISPLAY_WAKE_AND_CAPTURE_ATTEMPT_ARCHIVED_WITH_ACTUAL_EXIT_CODES
