#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k134-panel-reprobe-once
test ! -e "$dest"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k134+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k134-early-display-readonly/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test ! -e /dev/dri
test ! -L /sys/bus/mipi-dsi/devices/ae94000.dsi.0/driver
test -d /sys/bus/mipi-dsi/drivers/panel-samsung-sofef03f
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before-private.txt"
if rc-service greetd status >/dev/null 2>&1; then rc-service greetd stop > "$dest/greetd-stop.txt" 2>&1; fi
for pid in $(pgrep -u 10000 || true); do kill -TERM "$pid" 2>/dev/null || true; done
sleep 2
for pid in $(pgrep -u 10000 || true); do kill -KILL "$pid" 2>/dev/null || true; done
test -z "$(pgrep -u 10000 || true)"
test -z "$(pgrep -x phoc || true)"
set +e
timeout -s TERM -k 2 90 sh -c 'echo ae94000.dsi.0 > /sys/bus/mipi-dsi/drivers/panel-samsung-sofef03f/bind' > "$dest/bind-private.txt" 2>&1
result=$?
set -e
printf '%s\n' "$result" > "$dest/bind-exit.txt"
dmesg > "$dest/dmesg-after-private.txt"
cat /proc/sys/kernel/tainted > "$dest/final-taint.txt"
ls -l /dev/dri > "$dest/drm.txt" 2>&1 || true
readlink -f /sys/bus/mipi-dsi/devices/ae94000.dsi.0/driver > "$dest/panel-driver.txt" || true
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k134-panel-reprobe-private.tar.gz .
echo K134_SINGLE_NATIVE_PANEL_BIND_FINISHED_EXIT_$result
if test "$result" = 0 && test -c /dev/dri/card1 && test -c /dev/dri/renderD128; then
    rc-service greetd start > "$dest/greetd-start.txt" 2>&1
    echo K134_NATIVE_DRM_RECOVERED_GREETD_STARTED_STARTUP_DEFECT_REMAINS
fi
