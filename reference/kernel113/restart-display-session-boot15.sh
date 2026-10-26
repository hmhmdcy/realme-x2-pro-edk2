#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(cat /var/lib/samurai/k113-sensor-ram-attributes15/trial-exit.txt)" = 0
test -f /var/lib/samurai/k113-display-regression-boot15/SHA256SUMS
dest=/var/lib/samurai/k113-display-session-reset-boot15
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-before.txt"
dmesg > "$dest/dmesg-before.txt"
rc-service greetd stop > "$dest/greetd-stop.txt" 2>&1
sleep 2
ps -eo pid,user,args > "$dest/processes-stopped-private.txt"
for item in /sys/kernel/debug/dri/*; do
    test -f "$item/state" || continue
    cat "$item/state" > "$dest/drm-$(basename "$item")-stopped-private.txt"
done
cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-stopped-private.txt"
rc-service greetd start > "$dest/greetd-start.txt" 2>&1
sleep 8
rc-service greetd status > "$dest/greetd-status.txt"
ps -eo pid,user,args > "$dest/processes-after-private.txt"
for item in /sys/kernel/debug/dri/*; do
    test -f "$item/state" || continue
    cat "$item/state" > "$dest/drm-$(basename "$item")-after-private.txt"
done
cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-after-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-after.txt"
dmesg > "$dest/dmesg-after.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi-after.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-after.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-display-session-reset-boot15.tar .
sha256sum /tmp/k113-display-session-reset-boot15.tar
echo DISPLAY_SESSION_RESET_COMPLETE_NEW_PHYSICAL_STATE_REQUIRES_CONFIRMATION
