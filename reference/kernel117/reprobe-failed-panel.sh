#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k117-panel-reprobe
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-final-health/boot-id-private.txt)"
uname -v | grep -q '^#115 '
test "$(cat /proc/sys/kernel/tainted)" = 0
test ! -d /dev/dri
if pgrep -x phosh || pgrep -x phoc; then echo GUI_OWNER_PRESENT_ABORT;exit 1;fi
dev=/sys/bus/mipi-dsi/devices/ae94000.dsi.0
grep -qx 'OF_COMPATIBLE_0=samsung,sofef03f-m' "$dev/uevent"
test ! -e "$dev/driver"
test -w /sys/bus/mipi-dsi/drivers/panel-samsung-sofef03f/bind
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before-private.txt"
cat /proc/uptime > "$dest/uptime-before.txt"
set +e
timeout 20 sh -c 'printf "%s" "ae94000.dsi.0" > /sys/bus/mipi-dsi/drivers/panel-samsung-sofef03f/bind' > "$dest/bind.out" 2> "$dest/bind.err"
code=$?
set -e
echo "$code" > "$dest/bind-exit.txt"
if test "$code" = 0 && test -d /dev/dri; then
    set +e
    timeout 20 rc-service greetd restart > "$dest/greetd.out" 2> "$dest/greetd.err"
    code=$?
    set -e
    echo "$code" > "$dest/greetd-exit.txt"
    sleep 15
fi
ls -l /dev/dri > "$dest/drm.txt" 2>&1 || true
readlink "$dev/driver" > "$dest/panel-driver.txt" || true
pgrep -x phosh > "$dest/phosh.txt" || true
pgrep -x phoc > "$dest/phoc.txt" || true
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensors.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
cat /proc/uptime > "$dest/uptime-after.txt"
dmesg > "$dest/dmesg-after-private.txt"
rc-status default > "$dest/services.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k117-panel-reprobe-private.tar.gz .
sha256sum /tmp/k117-panel-reprobe-private.tar.gz
echo KERNEL117_BOUNDED_PANEL_REPROBE_EVIDENCE_SAVED
